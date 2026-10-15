#!/usr/bin/env python3
"""Independently inspect the official v3.4.2 boot-patch-v2 capsule and fixups.

Usage: check-ksunext-image.py base-boot patched-boot kernelsu.ko System.map patch.log
Checks format, contents and addresses; cannot establish successful device boot.
Wire format: KernelSU-Next commit 4c706b5938665866ebe16944a481a7b91e3396af,
userspace/ksud/src/lkm_image.rs.
"""
from pathlib import Path
import gzip
import hashlib
import json
import re
import struct
import sys

base_boot, boot, module, system_map, log = (Path(p) for p in sys.argv[1:])
base_data, data, ko = base_boot.read_bytes(), boot.read_bytes(), module.read_bytes()


def kernel(payload):
    assert payload[:8] == b'ANDROID!', 'Invalid boot magic'
    assert struct.unpack_from('<I', payload, 40)[0] == 4, 'Expected boot v4'
    size = struct.unpack_from('<I', payload, 8)[0]
    result = payload[4096:4096 + size]
    assert result[56:60] == b'ARM\x64', 'Expected raw ARM64 Image'
    return result


original, patched = kernel(base_data), kernel(data)
assert len(base_data) == len(data) == 100663296
assert data[12:1584] == base_data[12:1584], 'Boot header metadata changed'
old_size = struct.unpack_from('<Q', original, 16)[0]
new_size = struct.unpack_from('<Q', patched, 16)[0]
assert len(original) <= old_size < new_size == len(patched)
cap = (old_size + 15) & ~15
assert patched[cap:cap + 8] == b'KSULKM1\0'
version, header_size = struct.unpack_from('<II', patched, cap + 8)
cap_size, module_offset, module_size, fixup_offset, count, flags = struct.unpack_from('<6Q', patched, cap + 16)
assert version == 2 and header_size == 112 and flags == 1
assert cap + cap_size == len(patched)
assert module_offset == 112 and module_size == len(ko)
assert patched[cap + module_offset:cap + module_offset + module_size] == ko
digest = hashlib.sha256(ko).digest()
assert patched[cap + 64:cap + 96] == digest
args_offset, args_size = struct.unpack_from('<QQ', patched, cap + 96)
assert fixup_offset >= module_offset + module_size
assert fixup_offset + count * 16 <= args_offset
assert args_offset + args_size <= cap_size
assert patched[cap + args_offset:cap + args_offset + args_size] == b'\0', 'Unexpected module params'
assert not any(patched[len(original):cap]), 'Nonzero bytes in extended BSS padding'
assert not any(patched[cap + args_offset + args_size:]), 'Nonzero capsule tail'

symbols = {}
for line in system_map.read_text().splitlines():
    address, kind, name = line.split(maxsplit=2)
    symbols.setdefault(name, set()).add(int(address, 16))
image_base = next(iter(symbols['_text']))
assert len(symbols['_text']) == 1
assert ko[:6] == b'\x7fELF\x02\x01'
assert struct.unpack_from('<HH', ko, 16) == (1, 183)
section_offset = struct.unpack_from('<Q', ko, 40)[0]
section_size, section_count = struct.unpack_from('<HH', ko, 58)
sections = [struct.unpack_from('<IIQQQQIIQQ', ko, section_offset + i * section_size)
            for i in range(section_count)]
undefined = {}
for section in sections:
    if section[1] != 2:
        continue
    strings_section = sections[section[6]]
    strings = ko[strings_section[4]:strings_section[4] + strings_section[5]]
    for i in range(1, section[5] // section[9]):
        offset = section[4] + i * section[9]
        name_offset, _, _, index, _, _ = struct.unpack_from('<IBBHQQ', ko, offset)
        if index == 0 and name_offset:
            name = strings[name_offset:strings.index(0, name_offset)].decode()
            undefined[offset] = name
seen = set()
for i in range(count):
    symbol_offset, padding, kernel_offset = struct.unpack_from('<IIQ', patched, cap + fixup_offset + i * 16)
    assert padding == 0 and symbol_offset in undefined and symbol_offset not in seen
    name = undefined[symbol_offset]
    assert image_base + kernel_offset in symbols.get(name, set()), f'Wrong fixup for {name}'
    assert kernel_offset < old_size
    seen.add(symbol_offset)
assert seen == set(undefined), 'Not all undefined symbols have validated fixups'

text = log.read_text()
match = re.search(r'Bootstrap: offset 0x([0-9a-f]+), (\d+) bytes', text)
assert match
code_offset, code_size = int(match[1], 16), int(match[2])
assert not any(original[code_offset:code_offset + code_size]), 'Bootstrap did not use empty padding'
assert f'Module fixups: {count}, unresolved: 0' in text
sites = set()
for offset, (before, after) in enumerate(zip(original, patched)):
    if before != after and not (16 <= offset < 24 or code_offset <= offset < code_offset + code_size):
        sites.add(offset & ~3)
assert len(sites) == 3, 'Unexpected instruction patch sites'


def branch_target(instruction, offset):
    assert instruction & 0xfc000000 == 0x94000000, 'Instruction is not BL'
    delta = instruction & 0x03ffffff
    if delta & (1 << 25):
        delta -= 1 << 26
    return offset + delta * 4


expected_targets = {next(iter(symbols[name])) for name in
                    ('async_synchronize_full', 'strndup_user', 'memblock_reserve')}
actual_targets = set()
for offset in sites:
    before, after = (struct.unpack_from('<I', blob, offset)[0] for blob in (original, patched))
    actual_targets.add(image_base + branch_target(before, offset))
    assert code_offset <= branch_target(after, offset) < code_offset + code_size
assert actual_targets == expected_targets
begin = patched.index(b'IKCFG_ST') + 8
end = patched.index(b'IKCFG_ED', begin)
cfg = gzip.decompress(patched[begin:end])
base_begin = original.index(b'IKCFG_ST') + 8
base_end = original.index(b'IKCFG_ED', base_begin)
assert cfg == gzip.decompress(original[base_begin:base_end])
report = {
    'passed': True, 'scope': 'Offline boot/capsule/address verification; no device execution',
    'boot_header_version': 4, 'boot_size_bytes': len(data),
    'base_kernel_sha256': hashlib.sha256(original).hexdigest(),
    'patched_kernel_sha256': hashlib.sha256(patched).hexdigest(),
    'boot_sha256': hashlib.sha256(data).hexdigest(),
    'capsule_version': version, 'capsule_offset': cap,
    'embedded_module_sha256': digest.hex(), 'module_bytes_match_official_asset': True,
    'undefined_symbols': len(undefined), 'validated_fixups': count, 'unresolved_symbols': 0,
    'bootstrap_size': code_size, 'modified_call_sites': [hex(v) for v in sorted(sites)],
    'base_code_unchanged_outside_bootstrap_header_and_three_call_sites': True,
    'embedded_kernel_config_unchanged': True, 'extra_root_or_debug_params': False,
    'device_boot_tested': False, 'root_tested_on_device': False,
    'droidspaces_tested_on_device': False,
}
print(json.dumps(report, indent=2))
