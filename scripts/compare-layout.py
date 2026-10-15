#!/usr/bin/env python3
"""Compare selected DWARF structure layouts; requires pyelftools.

Usage: compare-layout.py baseline.o patched.o
This checks sizes and baseline member offsets, not complete KMI compatibility.
"""
import json
import sys
from elftools.elf.elffile import ELFFile

STRUCTURES = ('task_struct', 'signal_struct', 'user_struct', 'mm_struct',
              'cred', 'nsproxy', 'inode', 'file')


def name(die):
    attr = die.attributes.get('DW_AT_name')
    return attr.value.decode() if attr else None


def members(die, base_bits=0):
    result = {}
    for child in die.iter_children():
        if child.tag != 'DW_TAG_member':
            continue
        attrs = child.attributes
        location = attrs.get('DW_AT_data_member_location')
        # Anonymous union members have no location and start at the union base.
        offset = base_bits + (location.value * 8 if location else 0)
        if 'DW_AT_data_bit_offset' in attrs:
            offset = base_bits + attrs['DW_AT_data_bit_offset'].value
        member_name = name(child)
        if member_name:
            result[member_name] = {'offset_bits': offset}
            for attr in ('DW_AT_bit_size', 'DW_AT_bit_offset'):
                if attr in attrs:
                    result[member_name][attr] = attrs[attr].value
        else:
            nested = child.get_DIE_from_attribute('DW_AT_type')
            result.update(members(nested, offset))
    return result


def read(path):
    result = {}
    with open(path, 'rb') as stream:
        dwarf = ELFFile(stream).get_dwarf_info()
        for cu in dwarf.iter_CUs():
            for die in cu.iter_DIEs():
                if (die.tag == 'DW_TAG_structure_type'
                        and name(die) in STRUCTURES
                        and 'DW_AT_byte_size' in die.attributes):
                    result[name(die)] = {
                        'size': die.attributes['DW_AT_byte_size'].value,
                        'members': members(die),
                    }
    return result


baseline, patched = map(read, sys.argv[1:3])
report = {'scope': 'Selected structure sizes and baseline member bit offsets; '
                   'does not validate complete KMI, symbol CRCs or stock modules.',
          'structures': {}, 'errors': []}
for struct_name in STRUCTURES:
    if struct_name not in baseline or struct_name not in patched:
        report['errors'].append(f'Missing DWARF type: {struct_name}')
        continue
    before, after = baseline[struct_name], patched[struct_name]
    if before['size'] != after['size']:
        report['errors'].append(f'{struct_name}: structure size changed')
    for member_name, location in before['members'].items():
        if after['members'].get(member_name) != location:
            report['errors'].append(f'{struct_name}.{member_name}: offset/bitfield changed')
    report['structures'][struct_name] = {
        'baseline_size': before['size'], 'patched_size': after['size'],
        'baseline_members_checked': len(before['members']),
        'added_members': sorted(after['members'].keys() - before['members'].keys()),
    }
report['passed'] = not report['errors']
print(json.dumps(report, indent=2))
sys.exit(0 if report['passed'] else 1)
