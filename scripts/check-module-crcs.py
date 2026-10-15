#!/usr/bin/env python3
"""Compare stock modules' imported symbol CRCs with a rebuilt kernel.

Usage: check-module-crcs.py Module.symvers stock-module-root
Requires pyelftools. Report separates kernel imports from imports provided by
other stock modules, since those modules remain in the stock ROM.
"""
from pathlib import Path
import json
import struct
import sys
from elftools.elf.elffile import ELFFile

symvers = {}
owners = {}
for line in Path(sys.argv[1]).read_text().splitlines():
    fields = line.split()
    if len(fields) >= 3:
        symvers[fields[1]] = int(fields[0], 16)
        owners[fields[1]] = fields[2]

modules = []
stock_exports = set()
for path in sorted(Path(sys.argv[2]).rglob('*.ko')):
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        if elf.elfclass != 64 or not elf.little_endian:
            sys.exit(f'Unsupported module architecture: {path}')
        versions = elf.get_section_by_name('__versions')
        symbols = elf.get_section_by_name('.symtab')
        if symbols:
            for symbol in symbols.iter_symbols():
                if symbol.name.startswith('__ksymtab_'):
                    stock_exports.add(symbol.name.removeprefix('__ksymtab_'))
        if versions is None:
            sys.exit(f'No __versions section: {path}')
        data = versions.data()
        if not data:
            sys.exit(f'No versioned imports: {path}; CRC verification is not applicable. '
                     'Use the dedicated KernelSU-Next symbol/fixup checker for its LKM.')
        if len(data) % 64:
            sys.exit(f'Unexpected __versions record size: {path}')
        imports = []
        for offset in range(0, len(data), 64):
            crc = struct.unpack_from('<Q', data, offset)[0]
            name = data[offset + 8:offset + 64].split(b'\0', 1)[0].decode()
            imports.append((name, crc))
        modules.append((str(path.relative_to(sys.argv[2])), imports))

report = {'scope': 'Imported symbol CRC compatibility, not a device boot test.',
          'module_count': len(modules), 'kernel_import_checks': 0,
          'stock_module_imports': 0, 'mismatches': [], 'missing_symbols': []}
if not modules:
    sys.exit('No stock modules found')
for path, imports in modules:
    for name, expected in imports:
        # A symbol supplied by an existing stock module is not replaced by
        # the newly built GKI modules. Check the kernel-owned imports here.
        if name in stock_exports and owners.get(name) != 'vmlinux':
            report['stock_module_imports'] += 1
        elif name in symvers:
            report['kernel_import_checks'] += 1
            if symvers[name] != expected:
                report['mismatches'].append({
                    'module': path, 'symbol': name,
                    'stock_crc': f'0x{expected:08x}',
                    'build_crc': f'0x{symvers[name]:08x}',
                })
        else:
            report['missing_symbols'].append({'module': path, 'symbol': name})
report['passed'] = not report['mismatches'] and not report['missing_symbols']
print(json.dumps(report, indent=2))
sys.exit(0 if report['passed'] else 1)
