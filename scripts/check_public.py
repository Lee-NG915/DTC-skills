#!/usr/bin/env python3
"""Conservative text/export checks. Does not prove legal rights or full anonymization."""
import argparse
import ipaddress
import re
import sys
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_HOSTS = {
    'agentskills.io', 'github.com', 'nx.dev', 'shopify.dev',
    'support.google.com', 'www.w3.org', 'json-schema.org',
}
PATTERNS = {
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{15,}|shp(?:at|ca|pa|ss)_[a-fA-F0-9]{24,}|AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{15,})\b'),
    'bearer-value': re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}'),
    'jwt-value': re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
    'home-path': re.compile(r'(?:/Users/|/home/)[A-Za-z0-9_.-]+|[A-Za-z]:\\Users\\[^\\\s]+'),
    'platform-id': re.compile(r'\b(?:GTM-[A-Z0-9]{5,}|G-[A-Z0-9]{7,})\b'),
    'shop-domain': re.compile(r'\b[a-z0-9-]+\.myshopify\.com\b', re.I),
    'email': re.compile(r'\b[A-Za-z0-9._%+-]+@(?!example\.(?:invalid|com|org)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
    'secret-assignment': re.compile(r"""(?ix)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|cookie)\b["']?\s*[:=]\s*["']([^"'\n]{12,})["']"""),
}
URL = re.compile(r'https?://[^\s<>\)\]"\x27]+', re.I)
IP = re.compile(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])')

def scan_text(content, deny_terms=()):
    findings = []
    for line_no, line in enumerate(content.splitlines(), 1):
        for rule, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append((line_no, rule))
        if any(term.casefold() in line.casefold() for term in deny_terms):
            findings.append((line_no, 'private-deny-term'))
        for url in URL.findall(line):
            try:
                parsed = urlsplit(url)
                host = (parsed.hostname or '').lower()
                if parsed.username or parsed.password or parsed.query and re.search(r'(?i)(?:token|signature|credential|api[_-]?key|auth|code)=', parsed.query):
                    findings.append((line_no, 'access-bearing-url'))
                if host not in PUBLIC_HOSTS and host not in {'localhost', '127.0.0.1', '::1'} and not (host == 'example.invalid' or host.endswith('.example.invalid')):
                    findings.append((line_no, 'unreviewed-url-host'))
            except ValueError:
                findings.append((line_no, 'invalid-url'))
        for address in IP.findall(line):
            try:
                ip = ipaddress.ip_address(address)
                if not ip.is_loopback and ip.is_private:
                    findings.append((line_no, 'private-network-address'))
            except ValueError:
                pass
    return sorted(set(findings))

def scan_tree(root, deny_terms=()):
    findings = []
    try:
        result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'], capture_output=True)
        tracked = set(result.stdout.decode('utf-8').split('\x00')) if result.returncode == 0 else set()
    except FileNotFoundError:
        tracked = set()
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in {'.git', '__pycache__'} for part in relative.parts) and str(relative) not in tracked:
            continue
        if path.is_symlink():
            findings.append((str(relative), 0, 'symlink-review-required'))
            continue
        if not path.is_file():
            continue
        name = path.name.lower()
        if (name.startswith('.env') and name != '.env.example') or path.suffix.lower() in {'.pem', '.key', '.p12', '.pfx', '.har'}:
            findings.append((str(relative), 0, 'sensitive-file-type'))
        try:
            content = path.read_text(encoding='utf-8')
            if '\x00' in content:
                raise UnicodeError()
        except (UnicodeError, OSError):
            findings.append((str(relative), 0, 'non-text-review-required'))
            continue
        for line, rule in scan_text(str(relative) + '\n' + content, deny_terms):
            findings.append((str(relative), max(line - 1, 0), rule))
    return findings

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--deny-file', type=Path, help='Private newline-separated identifiers; never commit this file')
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error('root must be an existing directory')
    terms = []
    if args.deny_file:
        terms = [line.strip() for line in args.deny_file.read_text().splitlines() if line.strip() and not line.startswith('#')]
    findings = scan_tree(root, terms)
    for path, line, rule in findings:
        # Never echo matched values: reports must not become another secret copy.
        print(f'{path}:{line}: {rule}')
    print(f'{"FAIL" if findings else "PASS"}: public-content checks; {len(findings)} findings')
    return 1 if findings else 0

if __name__ == '__main__':
    sys.exit(main())
