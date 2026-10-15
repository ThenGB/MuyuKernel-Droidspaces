#!/usr/bin/env python3
"""Verify detached PKCS#7 module signatures with the stock public certificate.

Usage: check-stock-signatures.py extracted-module-root stock-certificate.pem
OpenSSL verifies the content signature; -noverify skips PKI chain validation
because the trust anchor is the certificate extracted from the official boot.
"""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
certificate = Path(sys.argv[2]).resolve()
magic = b'~Module signature appended~\n'
report = {'signed_modules_checked': 0, 'unsigned_modules': 0, 'failures': []}
with tempfile.TemporaryDirectory(prefix='muyu-module-signatures-') as directory:
    temp = Path(directory)
    for path in sorted(root.rglob('*.ko')):
        data = path.read_bytes()
        if not data.endswith(magic):
            report['unsigned_modules'] += 1
            continue
        header_end = len(data) - len(magic)
        header_start = header_end - 12
        header = data[header_start:header_end]
        length = struct.unpack_from('>I', header, 8)[0]
        if header[2] != 2 or length > header_start:
            report['failures'].append(str(path.relative_to(root)))
            continue
        content_end = header_start - length
        temp.joinpath('signature.p7').write_bytes(data[content_end:header_start])
        temp.joinpath('module').write_bytes(data[:content_end])
        result = subprocess.run([
            'openssl', 'cms', '-verify', '-binary', '-inform', 'DER',
            '-in', str(temp / 'signature.p7'), '-content', str(temp / 'module'),
            '-certfile', str(certificate), '-noverify', '-out', '/dev/null',
        ], capture_output=True)
        report['signed_modules_checked'] += 1
        if result.returncode:
            report['failures'].append(str(path.relative_to(root)))
report['passed'] = report['signed_modules_checked'] > 0 and not report['failures']
print(json.dumps(report, indent=2))
sys.exit(0 if report['passed'] else 1)
