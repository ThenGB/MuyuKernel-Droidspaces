#!/usr/bin/env python3
"""Check the resolved kernel config, including ABI-sensitive GKI choices."""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = Path(sys.argv[1]).read_text()
values = dict(re.findall(r'^(CONFIG_\w+)=(.*)$', config, re.M))
required = '\n'.join(root.joinpath('configs', name).read_text() for name in
                     ('droidspaces-gki.config', 'ksunext-lkm.config'))
checks = dict(re.findall(r'^(CONFIG_\w+)=(.*)$', required, re.M))
for name in (
    'NAMESPACES', 'UTS_NS', 'NET_NS', 'SECCOMP', 'SECCOMP_FILTER',
    'CGROUPS', 'MEMCG', 'BLK_DEV_LOOP', 'EXT4_FS', 'OVERLAY_FS',
    'FUSE_FS', 'TUN', 'VETH', 'BRIDGE', 'NF_CONNTRACK', 'NF_NAT',
    'IP_NF_IPTABLES', 'IP_NF_FILTER', 'IP_NF_NAT',
    'IP_NF_TARGET_MASQUERADE', 'IP_NF_TARGET_REJECT', 'IP6_NF_TARGET_REJECT',
    'MODVERSIONS', 'MODULE_SIG', 'MODULE_SIG_PROTECT', 'ANDROID_KABI_RESERVE',
    'ANDROID_VENDOR_HOOKS', 'CFI_CLANG',
):
    checks['CONFIG_' + name] = 'y'
errors = [f'{key}: expected {want}, got {values.get(key, "n")}'
          for key, want in checks.items() if values.get(key) != want]
for key in ('CONFIG_CFS_BANDWIDTH', 'CONFIG_CGROUP_PIDS'):
    if values.get(key, 'n') != 'n':
        errors.append(f'{key} must remain disabled for stock vendor modules')
if errors:
    sys.exit('\n'.join(errors))
if values.get('CONFIG_KSU', 'n') != 'n':
    sys.exit('The base GKI kernel must not also contain a built-in KernelSU driver')
if values.get('CONFIG_MODULE_SIG_FORCE', 'n') != 'n':
    sys.exit('LKM requires the stock CONFIG_MODULE_SIG_FORCE=n setting')
print(f'PASS: {len(checks)} enabled options and 2 ABI-sensitive disabled options')
