"""Observable client behavior against a synthetic local HTTP API; no real credentials."""
import contextlib
import copy
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/nb-project-upload/scripts/upload_projects.py"
SPEC = importlib.util.spec_from_file_location("nb_upload", SCRIPT)
upload = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(upload)
TOKEN = "synthetic-test-value"
ENTRY = {
    "name": "example-org/sample-tool", "url": "https://github.com/example-org/sample-tool",
    "domain": "devtools", "sub": "cli", "one_liner": "Synthetic tool",
    "public": {"scenario": "Synthetic scenario"},
}


def result(entries, dry_run, statuses=None):
    statuses = statuses or [("would_create" if dry_run else "created")] * len(entries)
    created = sum(status != "exists" for status in statuses)
    return {"ok": True, "dryRun": dry_run,
            "summary": {"projectsCreated": min(created, len({e["name"] for e in entries})),
                        "entriesCreated": created, "entriesSkipped": len(entries) - created},
            "items": [{"name": e["name"], "domain": e["domain"], "sub": e["sub"], "status": status}
                      for e, status in zip(entries, statuses)]}


class FakeApi:
    def __init__(self, respond=None):
        self.requests = []
        self.stored = set()
        self.respond = respond
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                owner.requests.append({"path": self.path, "body": body,
                                       "authorization": self.headers.get("Authorization")})
                if (self.headers.get("User-Agent") != "nb-project-upload/1.0"
                        or self.headers.get("Accept") != "application/json"):
                    status, response, headers = 403, {"error": "Client identification required"}, {}
                elif owner.respond:
                    status, response, headers = owner.respond(body, len(owner.requests))
                else:
                    entries = body["entries"]
                    keys = [upload.entry_key(e) for e in entries]
                    statuses = ["exists" if key in owner.stored else (
                        "would_create" if body["dryRun"] else "created") for key in keys]
                    if not body["dryRun"]:
                        owner.stored.update(keys)
                    status, response, headers = 200, result(entries, body["dryRun"], statuses), {}
                raw = response if isinstance(response, bytes) else json.dumps(response).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = "http://127.0.0.1:" + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.input = Path(self.temp.name) / "entries.json"
        self.input.write_text(json.dumps([ENTRY]), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, url, *args, token=TOKEN):
        stdout, stderr = io.StringIO(), io.StringIO()
        environment = {"NB_PROJECT_URL": url, "NB_PROJECT_INGEST_TOKEN": token}
        with patch.dict(os.environ, environment), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = upload.main(["--input", str(self.input), *args])
        self.assertNotIn(TOKEN, stdout.getvalue() + stderr.getvalue())
        return code, stdout.getvalue(), stderr.getvalue()

    def test_default_is_preflight_without_write(self):
        with FakeApi() as api:
            code, stdout, stderr = self.cli(api.url)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(api.requests), 1)
        self.assertTrue(api.requests[0]["body"]["dryRun"])
        self.assertFalse(api.stored)
        self.assertEqual(json.loads(stdout)["items"][0]["status"], "would_create")

    def test_apply_preflights_writes_and_reads_back(self):
        with FakeApi() as api:
            code, stdout, stderr = self.cli(api.url, "--apply")
        self.assertEqual(code, 0, stderr)
        self.assertEqual([r["body"]["dryRun"] for r in api.requests], [True, False, True])
        self.assertEqual({r["path"] for r in api.requests}, {"/api/ingest/projects"})
        self.assertEqual({r["authorization"] for r in api.requests}, {"Bearer " + TOKEN})
        receipt = json.loads(stdout)
        self.assertTrue(receipt["verified"])
        self.assertEqual(receipt["items"][0]["status"], "created")

    def test_repeat_preserves_exists_and_reports_zero_created(self):
        with FakeApi() as api:
            self.cli(api.url, "--apply")
            code, stdout, stderr = self.cli(api.url, "--apply")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["summary"],
                         {"projectsCreated": 0, "entriesCreated": 0, "entriesSkipped": 1})
        self.assertEqual(json.loads(stdout)["items"][0]["status"], "exists")

    def test_standalone_cli_runs_outside_repo(self):
        with FakeApi() as api:
            environment = {**os.environ, "NB_PROJECT_URL": api.url, "NB_PROJECT_INGEST_TOKEN": TOKEN}
            response = subprocess.run([sys.executable, str(SCRIPT), "--input", str(self.input), "--apply"],
                                      cwd=self.temp.name, env=environment, text=True, capture_output=True, timeout=10)
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertTrue(json.loads(response.stdout)["verified"])

    def test_auth_rejection_stops_before_apply_and_hides_body(self):
        with FakeApi(lambda *_: (401, {"error": TOKEN}, {})) as api:
            code, stdout, stderr = self.cli(api.url, "--apply")
        self.assertEqual(code, 2)
        self.assertEqual(len(api.requests), 1)
        self.assertEqual(json.loads(stderr)["writeState"], "not_started")

    def test_redirect_is_not_followed(self):
        with FakeApi() as destination:
            with FakeApi(lambda *_: (307, {}, {"Location": destination.url + "/api/ingest/projects"})) as api:
                code, stdout, stderr = self.cli(api.url, "--apply")
            self.assertEqual(destination.requests, [])
        self.assertEqual(code, 2)
        self.assertIn("Redirect refused", stderr)

    def test_apply_timeout_is_unknown_and_not_retried(self):
        def respond(body, count):
            if count == 2:
                time.sleep(0.12)
            return 200, result(body["entries"], body["dryRun"]), {}
        with FakeApi(respond) as api:
            code, stdout, stderr = self.cli(api.url, "--apply", "--timeout", "0.04")
        self.assertEqual(code, 2)
        self.assertEqual(len(api.requests), 2)
        self.assertEqual(json.loads(stderr)["writeState"], "unknown")
        self.assertEqual(json.loads(stderr)["phase"], "apply")

    def test_apply_500_is_unknown_and_hides_body(self):
        def respond(body, count):
            if count == 2:
                return 500, {"error": TOKEN}, {}
            return 200, result(body["entries"], True), {}
        with FakeApi(respond) as api:
            code, stdout, stderr = self.cli(api.url, "--apply")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stderr)["writeState"], "unknown")
        self.assertEqual(len(api.requests), 2)

    def test_apply_503_from_proxy_is_also_unknown(self):
        def respond(body, count):
            if count == 2:
                return 503, {"error": TOKEN}, {}
            return 200, result(body["entries"], True), {}
        with FakeApi(respond) as api:
            code, stdout, stderr = self.cli(api.url, "--apply")
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stderr)["writeState"], "unknown")
        self.assertEqual(len(api.requests), 2)

    def test_missing_readback_is_acknowledged_but_not_verified(self):
        with FakeApi(lambda body, count: (200, result(body["entries"], body["dryRun"]), {})) as api:
            code, stdout, stderr = self.cli(api.url, "--apply")
        failure = json.loads(stderr)
        self.assertEqual(code, 2)
        self.assertEqual(failure["writeState"], "acknowledged")
        self.assertEqual(failure["receipt"]["items"][0]["status"], "created")
        self.assertEqual(len(api.requests), 3)

    def test_wrong_or_duplicate_response_identity_does_not_pass(self):
        def respond(body, count):
            response = result(body["entries"], body["dryRun"])
            response["items"][0]["name"] = "example-org/unrequested"
            return 200, response, {}
        with FakeApi(respond) as api:
            code, stdout, stderr = self.cli(api.url, "--apply")
        self.assertEqual(code, 2)
        self.assertEqual(len(api.requests), 1)

    def test_inconsistent_counts_are_not_success(self):
        def respond(body, count):
            response = result(body["entries"], body["dryRun"])
            response["summary"]["entriesCreated"] = 0
            return 200, response, {}
        with FakeApi(respond) as api:
            code, stdout, stderr = self.cli(api.url)
        self.assertEqual(code, 2)

    def test_server_extra_fields_are_not_copied_to_receipt(self):
        def respond(body, count):
            response = result(body["entries"], body["dryRun"])
            response["debug"] = TOKEN
            response["items"][0]["raw"] = TOKEN
            return 200, response, {}
        with FakeApi(respond) as api:
            code, stdout, stderr = self.cli(api.url)
        self.assertEqual(code, 0, stderr)

    def test_missing_credential_never_sends_request(self):
        with FakeApi() as api:
            code, stdout, stderr = self.cli(api.url, "--apply", token="")
        self.assertEqual(code, 2)
        self.assertEqual(api.requests, [])

    def test_legacy_receipt_without_quality_is_unchanged(self):
        response = result([ENTRY], True)
        self.assertEqual(upload.validate_response(response, [ENTRY], True), response)
        self.assertNotIn("quality", response["items"][0])

    def test_quality_hints_survive_apply_and_never_block_existing_upload_flow(self):
        def respond(body, count):
            response = result(body["entries"], body["dryRun"], ["exists"] if count == 3 else None)
            response["items"][0]["quality"] = {
                "errors": [{"field": "public.scenario", "code": "INTERNAL_COPY", "message": TOKEN}],
                "warnings": [{"field": "one_liner", "code": "LANGUAGE", "message": TOKEN, "raw": TOKEN}],
                "raw": TOKEN,
            }
            return 200, response, {}
        with FakeApi(respond) as api:
            code, stdout, stderr = self.cli(api.url, "--apply")
        self.assertEqual(code, 0, stderr)
        self.assertEqual([r["body"]["dryRun"] for r in api.requests], [True, False, True])
        receipt = json.loads(stdout)
        self.assertTrue(receipt["verified"])
        self.assertEqual(receipt["items"][0]["quality"], {
            "errors": [{"field": "public.scenario", "code": "INTERNAL_COPY", "message": upload.QUALITY_MESSAGES["INTERNAL_COPY"]}],
            "warnings": [{"field": "one_liner", "code": "LANGUAGE", "message": upload.QUALITY_MESSAGES["LANGUAGE"]}],
        })

    def test_quality_preview_retains_safe_evidence_fields_and_hides_unknown_text(self):
        response = result([ENTRY], True)
        response["items"][0]["quality"] = {"errors": [
            {"field": "evidence.19.url", "code": "INVALID_EVIDENCE_URL", "message": TOKEN},
            {"field": TOKEN, "code": "REQUIRED", "message": TOKEN},
            {"field": "one_liner", "code": TOKEN, "message": TOKEN},
            {"field": [TOKEN], "code": [TOKEN]}, None,
        ], "warnings": []}
        normalized = upload.validate_response(response, [ENTRY], True)
        self.assertNotIn(TOKEN, json.dumps(normalized))
        issues = normalized["items"][0]["quality"]["errors"]
        self.assertEqual([(i["field"], i["code"]) for i in issues], [
            ("evidence.19.url", "INVALID_EVIDENCE_URL"), ("draft", "UNRECOGNIZED_QUALITY")])

    def test_malformed_optional_quality_does_not_invalidate_a_successful_receipt(self):
        for quality in (None, TOKEN, {"errors": TOKEN, "warnings": []}, {}):
            with self.subTest(quality=type(quality).__name__):
                response = result([ENTRY], False)
                response["items"][0]["quality"] = quality
                hints = upload.validate_response(response, [ENTRY], False)["items"][0]["quality"]
                self.assertEqual(hints["warnings"][0]["code"], "UNRECOGNIZED_QUALITY")
                self.assertNotIn(TOKEN, json.dumps(hints))

    def test_quality_hints_are_bounded_and_deduplicated(self):
        hints = upload.normalize_quality({"errors": [], "warnings": [
            {"field": "one_liner", "code": "LANGUAGE", "message": TOKEN}] * 101})
        self.assertEqual([i["code"] for i in hints["warnings"]], ["LANGUAGE", "UNRECOGNIZED_QUALITY"])
        self.assertNotIn(TOKEN, json.dumps(hints))

    def test_failed_readback_retains_safe_quality_in_acknowledged_receipt(self):
        def respond(body, count):
            if count == 3:
                return 500, {"error": TOKEN}, {}
            response = result(body["entries"], body["dryRun"])
            response["items"][0]["quality"] = {"errors": [], "warnings": [
                {"field": "highlights", "code": "HIGHLIGHT_COUNT", "message": TOKEN}]}
            return 200, response, {}
        with FakeApi(respond) as api:
            code, stdout, stderr = self.cli(api.url, "--apply")
        self.assertEqual(code, 2)
        failure = json.loads(stderr)
        self.assertEqual(failure["writeState"], "acknowledged")
        self.assertEqual(failure["receipt"]["items"][0]["quality"]["warnings"][0]["code"], "HIGHLIGHT_COUNT")
        self.assertEqual(len(api.requests), 3)

    def test_unsafe_origins_are_rejected(self):
        bad = ["http://catalog.example.invalid", "https://" + "user:secret" + "@" + "catalog.example.invalid",
               "https://catalog.example.invalid/api", "https://catalog.example.invalid" + "?token=x",
               "https://catalog.example.invalid/#secret", "https://catalog.example.invalid" + ":bad",
               " https://catalog.example.invalid"]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(upload.UploadError):
                upload.origin(value)
        self.assertEqual(upload.origin("https://catalog.example.invalid/"), "https://catalog.example.invalid")
        self.assertEqual(upload.origin("http://" + "[::1]:8787"), "http://" + "[::1]:8787")

    def test_payload_cannot_enable_writes_and_rejects_duplicate_keys(self):
        invalid = ['{"entries":[],"dryRun":false}', '{"entries":[],"entries":[]}']
        for payload in invalid:
            with self.subTest(payload=payload):
                self.input.write_text(payload)
                with self.assertRaises(upload.UploadError):
                    upload.load_entries(self.input)

    def test_limit_and_case_insensitive_batch_duplicates(self):
        duplicate = copy.deepcopy(ENTRY)
        duplicate["name"] = "EXAMPLE-ORG/SAMPLE-TOOL"
        for entries in ([], [ENTRY, duplicate], [ENTRY] * 21):
            with self.subTest(size=len(entries)):
                self.input.write_text(json.dumps(entries))
                with self.assertRaises(upload.UploadError):
                    upload.load_entries(self.input)

    def test_size_limit_finite_numbers_and_unicode(self):
        for raw in (b" " * (upload.MAX_BYTES + 1), b'[{"name":NaN}]',
                    json.dumps([{**ENTRY, "highlights": "\ud800"}]).encode()):
            self.input.write_bytes(raw)
            with self.assertRaises(upload.UploadError):
                upload.load_entries(self.input)

    def test_multi_domain_is_not_a_duplicate(self):
        other = {**ENTRY, "domain": "backend", "sub": "devops"}
        self.input.write_text(json.dumps({"entries": [ENTRY, other]}))
        self.assertEqual(len(upload.load_entries(self.input)), 2)

    def test_surrounding_identity_whitespace_is_rejected_before_request(self):
        for key in ("domain", "sub"):
            with self.subTest(key=key):
                entry = {**ENTRY, key: " " + ENTRY[key] + " "}
                self.input.write_text(json.dumps([entry]))
                with FakeApi() as api:
                    code, stdout, stderr = self.cli(api.url, "--apply")
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(stderr)["phase"], "input")
                self.assertEqual(api.requests, [])

    def test_unknown_arguments_do_not_echo_accidental_credential(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            upload.main(["--input", str(self.input), "--token", TOKEN])
        self.assertNotIn(TOKEN, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
