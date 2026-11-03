#!/usr/bin/env python3
"""Upload curated entries to nb-project using only Python's standard library."""
import argparse
import http.client
import ipaddress
import json
import math
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 128 * 1024
MAX_ENTRIES = 20
USER_AGENT = "nb-project-upload/1.0"
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}\Z")
SUMMARY_KEYS = ("projectsCreated", "entriesCreated", "entriesSkipped")
QUALITY_FIELDS = frozenset(("draft", "title", "one_liner", "public.scenario", "public.diff",
                            "highlights", "domain", "sub", "tags", "evidence"))
# Never echo a server-supplied message: diagnostics can contain upstream text or secrets.
QUALITY_MESSAGES = {
    "INVALID_DRAFT": "草稿格式需要完善。",
    "INVALID_TEXT": "字段应填写文本。",
    "REQUIRED": "请补全必需字段。",
    "TOO_LONG": "字段超过长度限制。",
    "INVALID_CHARACTERS": "字段包含不支持的字符。",
    "INTERNAL_COPY": "公开文案包含内部策展措辞，请修订。",
    "UNVERIFIED_SUPERLATIVE": "请核实绝对评价并改为具体能力。",
    "LANGUAGE": "建议提供完整中文简介，保留产品名和技术名。",
    "EDITORIAL_LENGTH": "建议约 30–60 字，完整说明类型与用途。",
    "POSSIBLE_TRUNCATION": "请核对简介是否被截断。",
    "DUPLICATE_SUMMARY": "适用场景应补充使用条件，避免重复简介。",
    "HIGHLIGHT_COUNT": "建议提供 2–4 条有来源依据的具体能力。",
    "UNKNOWN_DOMAIN": "请选择已有一级领域。",
    "INVALID_SUB": "子方向应使用小写字母、数字和连字符。",
    "INVALID_TAGS": "请检查标签类型、数量和长度。",
    "DUPLICATE_TAGS": "请去掉重复标签。",
    "TAG_FORMAT": "标签应使用小写并去掉开头的井号。",
    "MISSING_FACETS": "建议保留领域和子方向标签。",
    "SKILL_TASK_TAG": "Skill 需要具体任务标签。",
    "EVIDENCE_REQUIRED": "请补充来源和证据摘录。",
    "INVALID_EVIDENCE_URL": "证据应使用无凭证的 HTTPS 链接。",
    "UNRECOGNIZED_QUALITY": "服务端包含未识别的质量提示，请到管理台核对。",
}


class UploadError(Exception):
    def __init__(self, message, *, phase="configuration", write_state="not_started", receipt=None):
        super().__init__(message)
        self.phase = phase
        self.write_state = write_state
        self.receipt = receipt


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default error can echo an accidentally supplied secret argument.
        print(json.dumps({"ok": False, "error": "Invalid arguments; run --help for supported options.",
                          "phase": "configuration", "writeState": "not_started"}), file=sys.stderr)
        self.exit(2)


def origin(value):
    """Accept an origin, never an access-bearing URL or arbitrary API path."""
    if not value or any(c.isspace() or ord(c) < 32 for c in value):
        raise UploadError("Set NB_PROJECT_URL or --base-url to the target site origin.")
    try:
        parsed = urlsplit(value)
        host, port = parsed.hostname, parsed.port
    except ValueError:
        raise UploadError("Invalid target origin.") from None
    if (not host or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise UploadError("Target must be a site origin without credentials, path, query or fragment.")
    loopback = host.lower() == "localhost"
    try:
        loopback = loopback or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
        raise UploadError("HTTPS is required; HTTP is allowed only for loopback testing.")
    # Preserve the supplied authority, including brackets around IPv6 literals.
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Non-finite JSON number")


def entry_key(entry):
    name, domain, sub = entry.get("name"), entry.get("domain"), entry.get("sub")
    if (not isinstance(name, str) or not NAME.fullmatch(name)
            or not isinstance(domain, str) or not domain
            or not isinstance(sub, str) or not sub):
        raise UploadError("Every entry needs a GitHub owner/repo name, domain and sub.", phase="input")
    if domain != domain.strip() or sub != sub.strip():
        raise UploadError("domain and sub must not contain surrounding whitespace.", phase="input")
    return name.casefold(), domain, sub


def load_entries(path):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError:
        raise UploadError("Cannot read the input JSON file.", phase="input") from None
    if len(raw) > MAX_BYTES:
        raise UploadError("Input exceeds 128 KiB; split it into explicit batches.", phase="input")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (ValueError, UnicodeError):
        raise UploadError("Input must be valid UTF-8 JSON with unique object keys.", phase="input") from None
    if isinstance(document, dict):
        if set(document) != {"entries"}:
            raise UploadError("Input object must contain only entries; use --apply to select writes.", phase="input")
        document = document["entries"]
    if not isinstance(document, list) or not 1 <= len(document) <= MAX_ENTRIES:
        raise UploadError("Each batch must contain 1–20 entries.", phase="input")
    keys = set()
    for entry in document:
        if not isinstance(entry, dict):
            raise UploadError("Each entry must be an object.", phase="input")
        key = entry_key(entry)
        if key in keys:
            raise UploadError("Duplicate project/domain/sub within this batch.", phase="input")
        keys.add(key)
    try:
        size = len(encode(document, True))
    except (ValueError, UnicodeError):
        raise UploadError("Input must contain valid Unicode and finite numbers.", phase="input") from None
    if size > MAX_BYTES:
        raise UploadError("Encoded request exceeds 128 KiB; split the batch.", phase="input")
    return document


def encode(entries, dry_run):
    return json.dumps({"dryRun": dry_run, "entries": entries}, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def normalize_quality(value):
    """Optional, informational hints. Keep only known fields/codes and fixed messages."""
    unknown = {"field": "draft", "code": "UNRECOGNIZED_QUALITY",
               "message": QUALITY_MESSAGES["UNRECOGNIZED_QUALITY"]}
    if not isinstance(value, dict) or any(not isinstance(value.get(key), list) for key in ("errors", "warnings")):
        return {"errors": [], "warnings": [unknown]}
    normalized = {"errors": [], "warnings": []}
    for bucket in normalized:
        seen, unrecognized = set(), len(value[bucket]) > 100
        for issue in value[bucket][:100]:
            if not isinstance(issue, dict):
                unrecognized = True
                continue
            field, code = issue.get("field"), issue.get("code")
            valid_field = isinstance(field, str) and (field in QUALITY_FIELDS or
                re.fullmatch(r"evidence\.(?:[0-9]|1[0-9])\.(?:url|excerpt)", field) is not None)
            if not valid_field or not isinstance(code, str) or code not in QUALITY_MESSAGES:
                unrecognized = True
                continue
            key = (field, code)
            if key not in seen:
                normalized[bucket].append({"field": field, "code": code, "message": QUALITY_MESSAGES[code]})
                seen.add(key)
        if unrecognized and ("draft", "UNRECOGNIZED_QUALITY") not in seen:
            normalized[bucket].append(dict(unknown))
    return normalized


def validate_response(body, entries, dry_run):
    if not isinstance(body, dict) or body.get("ok") is not True or body.get("dryRun") is not dry_run:
        raise ValueError("Invalid response envelope")
    summary, items = body.get("summary"), body.get("items")
    if not isinstance(summary, dict) or not isinstance(items, list) or len(items) != len(entries):
        raise ValueError("Missing result rows")
    if any(type(summary.get(key)) is not int or not 0 <= summary[key] <= len(entries)
           for key in SUMMARY_KEYS):
        raise ValueError("Invalid counts")
    expected = {entry_key(entry): entry for entry in entries}
    accepted, seen = [], set()
    creating_status = "would_create" if dry_run else "created"
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid result row")
        try:
            key = entry_key(item)
        except UploadError:
            raise ValueError("Invalid result identity") from None
        if key not in expected or key in seen or item.get("status") not in (creating_status, "exists"):
            raise ValueError("Unexpected result identity or status")
        seen.add(key)
        # Retain only contract fields; do not copy arbitrary server text into receipts.
        normalized = {"name": item["name"], "domain": item["domain"],
                      "sub": item["sub"], "status": item["status"]}
        if "quality" in item:
            normalized["quality"] = normalize_quality(item["quality"])
        accepted.append(normalized)
    created = sum(item["status"] == creating_status for item in accepted)
    if (summary["entriesCreated"] != created or summary["entriesSkipped"] != len(items) - created
            or summary["projectsCreated"] > min(created, len({key[0] for key in expected}))):
        raise ValueError("Inconsistent counts")
    return {"ok": True, "dryRun": dry_run,
            "summary": {key: summary[key] for key in SUMMARY_KEYS}, "items": accepted}


def request_batch(base_url, token, entries, dry_run, timeout, phase):
    request = Request(base_url + "/api/ingest/projects", data=encode(entries, dry_run),
                      method="POST", headers={"Authorization": "Bearer " + token,
                                               "Content-Type": "application/json",
                                               "Accept": "application/json",
                                               "User-Agent": USER_AGENT})
    unknown = "unknown" if phase == "apply" else "not_started"
    try:
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("Oversized response")
            body = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)
            return validate_response(body, entries, dry_run)
    except HTTPError as error:
        status = error.code
        error.close()
        messages = {
            400: "Invalid batch; check the payload contract and run preflight again.",
            401: "Ingest credential missing or rejected.",
            403: "The server refused this ingest credential.",
            404: "Ingest endpoint not found; verify the target and API deployment.",
            413: "The server rejected the request size.",
            415: "The server requires a JSON request.",
            422: "Batch validation failed; check the payload contract.",
            503: "Ingest is unavailable; verify server configuration.",
        }
        message = "Redirect refused; verify the target origin." if 300 <= status < 400 else messages.get(
            status, "The server did not return a successful ingest response.")
        # Validation/auth rejections occur before writes under the API contract.
        state = "not_started" if status in (400, 401, 403, 404, 413, 415, 422) or 300 <= status < 400 else unknown
        raise UploadError(f"HTTP {status}: {message}", phase=phase, write_state=state) from None
    except (URLError, TimeoutError, OSError, http.client.HTTPException):
        raise UploadError("Request failed or timed out. Do not blindly retry a write; run preflight to reconcile first.",
                          phase=phase, write_state=unknown) from None
    except (ValueError, UnicodeError):
        raise UploadError("Invalid or inconsistent server response. Reconcile with preflight before retrying a write.",
                          phase=phase, write_state=unknown) from None


def upload(base_url, token, entries, *, apply=False, timeout=20):
    preflight = request_batch(base_url, token, entries, True, timeout, "preflight")
    if not apply:
        return {"target": base_url, **preflight, "verified": False}
    receipt = request_batch(base_url, token, entries, False, timeout, "apply")
    try:
        readback = request_batch(base_url, token, entries, True, timeout, "verify")
        if any(item["status"] != "exists" for item in readback["items"]):
            raise UploadError("Some entries are absent on readback.", phase="verify")
    except UploadError as error:
        raise UploadError("The write was acknowledged, but readback is unconfirmed. Run preflight to reconcile.",
                          phase="verify", write_state="acknowledged", receipt=receipt) from error
    return {"target": base_url, **receipt, "verified": True}


def main(argv=None):
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="UTF-8 JSON array or an object containing entries")
    parser.add_argument("--base-url", help="Target site origin; defaults to NB_PROJECT_URL")
    parser.add_argument("--apply", action="store_true", help="Preflight, insert, then verify (default: preflight only)")
    parser.add_argument("--timeout", type=float, default=20, help="Per-request timeout in seconds (0 < value <= 120)")
    args = parser.parse_args(argv)
    try:
        base_url = origin(args.base_url or os.environ.get("NB_PROJECT_URL", ""))
        token = os.environ.get("NB_PROJECT_INGEST_TOKEN", "")
        if not token or token != token.strip() or any(c.isspace() or ord(c) < 32 or ord(c) > 126 for c in token):
            raise UploadError("Set NB_PROJECT_INGEST_TOKEN in the environment to the dedicated ingest credential.")
        if not math.isfinite(args.timeout) or not 0 < args.timeout <= 120:
            raise UploadError("Timeout must be greater than 0 and no more than 120 seconds.")
        entries = load_entries(args.input)
        result = upload(base_url, token, entries, apply=args.apply, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except UploadError as error:
        failure = {"ok": False, "error": str(error), "phase": error.phase,
                   "writeState": error.write_state}
        if error.receipt:
            failure["receipt"] = error.receipt
        print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
