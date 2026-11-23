"""Read-only scan of tracked/staged Git files; never prints secret contents.

Does not replace a manual privacy review or a full history/credential scanner.
"""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BLOCK_SUFFIX = ('.sqlite3', '.db', '.bak', '.log', '.pem', '.key', '.p12', '.pfx', '.csv', '.xlsx', '.zip', '.pyc')
BLOCK_NAME = {'db.sqlite3', '.medidesk_local.json', '.env', 'credentials.json', 'secrets.json'}
BLOCK_PARTS = {'.venv', 'venv', '__pycache__', '.medidesk_backups', '.medidesk_build_logs', 'stage2_payload', 'stage3_payload', 'stage4_payload', 'staticfiles', '.git', '.vscode'}
PUBLIC_ENV_EXAMPLE = '.env.example'
PATTERNS = [
    ('GitHub credential', re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{20,})\b')),
    ('AWS access key', re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
    ('Private key block', re.compile(rb'-----BEGIN [^-\r\n]*PRIVATE KEY-----')),
    ('Google API key', re.compile(rb'\bAIza[0-9A-Za-z_-]{35}\b')),
]

def main():
    result = subprocess.run(['git', 'ls-files', '--cached', '-z'], cwd=ROOT,
                            capture_output=True, check=False)
    if result.returncode:
        print('FAIL: Not a staged Git repository. Run the release installer first.')
        return 1
    paths = [name.decode('utf-8', 'replace') for name in result.stdout.split(b'\x00') if name]
    if not paths:
        print('FAIL: There are no files staged or tracked in Git.')
        return 1
    problems = []
    for path in paths:
        norm = path.replace('\\', '/')
        parts = norm.split('/')
        base = parts[-1]
        low = base.lower()
        if (any(s.lower() in {p.lower() for p in parts} for s in BLOCK_PARTS)
            or (low in BLOCK_NAME and norm != PUBLIC_ENV_EXAMPLE)
            or (low.startswith('.env') and norm != PUBLIC_ENV_EXAMPLE)
            or low.endswith(BLOCK_SUFFIX)):
            problems.append(f'Unsafe tracked filename: {norm}')
            continue
        blob = subprocess.run(['git', 'show', ':' + norm], cwd=ROOT,
                              capture_output=True, check=False)
        if blob.returncode:
            # A tracked file may be unchanged in the working tree, or cached in
            # the index; git show :path must still work in both cases.
            problems.append(f'Cannot inspect staged content: {norm}')
            continue
        raw = blob.stdout
        if b'\x00' in raw or len(raw) > 1_500_000:
            problems.append(f'Unexpected binary or oversized staged file: {norm}')
            continue
        for label, pattern in PATTERNS:
            if pattern.search(raw):
                problems.append(f'{label} detected in {norm}')
    if problems:
        print('GITHUB SAFETY SCAN FAILED:')
        for issue in problems:
            print(' - ' + issue)
        print('DO NOT PUSH. Remove risky content from the index and review Git history.')
        return 1
    print(f'GITHUB SAFETY SCAN PASSED: inspected {len(paths)} staged/tracked files.')
    print('Manual review is still required: scans cannot guarantee privacy or absence of secrets.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
