#!/usr/bin/env python3
"""Refresh the custom boot hash footer for this ROM as unsigned AVB metadata.

Usage: normalize-avb.py generated-boot.img pinned-avbtool.py
This does not make the image Xiaomi-signed. An unlocked bootloader is required.
"""
from pathlib import Path
import json
import shutil
import struct
import subprocess
import sys
import tempfile

image, avbtool = (Path(p).resolve() for p in sys.argv[1:])
before = image.read_bytes()
assert len(before) == 100663296 and before[:8] == b'ANDROID!'
assert struct.unpack_from('<I', before, 40)[0] == 4
size = struct.unpack_from('<I', before, 8)[0]
assert b'6.1.138-android14-11-Droidspaces' in before[4096:4096 + size]
with tempfile.TemporaryDirectory(prefix='avb-normalize-', dir=image.parent) as directory:
    temporary = Path(directory) / 'boot.img'
    shutil.copy2(image, temporary)
    subprocess.run([
        sys.executable, str(avbtool), 'add_hash_footer', '--image', str(temporary),
        '--partition_size', '100663296', '--partition_name', 'boot',
        '--hash_algorithm', 'sha256', '--algorithm', 'NONE',
        '--salt', '97b2c53022e8c0bd0b279c4c592a196126a6eb0a93647c2957b39dcd5f2dc1c9',
        '--rollback_index', '1788220800',
        '--prop', 'com.android.build.boot.os_version:14',
        '--prop', 'com.android.build.boot.fingerprint:Xiaomi/muyu_global/muyu:14/UKQ1.240624.001/OS3.0.304.0.WOYMIXM:user/release-keys',
        '--prop', 'com.android.build.boot.security_patch:2026-09-01',
    ], check=True)
    checked = subprocess.run([sys.executable, str(avbtool), 'verify_image', '--image', str(temporary)],
                             check=True, capture_output=True, text=True)
    info = subprocess.run([sys.executable, str(avbtool), 'info_image', '--image', str(temporary)],
                          check=True, capture_output=True, text=True)
    assert 'Algorithm:                NONE' in info.stdout
    assert 'Flags:                    0' in info.stdout
    after = temporary.read_bytes()
    assert len(after) == len(before)
    assert after[:4096 + size] == before[:4096 + size], 'Kernel or boot header changed'
    temporary.replace(image)
print(json.dumps({
    'passed': True, 'payload_hash_verified': True,
    'boot_header_and_kernel_unchanged': True, 'avb_algorithm': 'NONE',
    'xiaomi_signature_valid': False, 'requires_unlocked_bootloader': True,
    'verification_disabled_flags_set': False,
    'verify_log': checked.stdout, 'info_log': info.stdout,
}, indent=2))
