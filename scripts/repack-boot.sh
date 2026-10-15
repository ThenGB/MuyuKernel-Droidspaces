#!/usr/bin/env bash
# Prepare a boot image for this specific ROM. Does not flash the device.
set -euo pipefail
if [[ $# != 3 ]]; then
    echo "Usage: MAGISKBOOT=/path/to/magiskboot $0 stock-boot.img Image output-boot.img" >&2
    exit 1
fi
stock_boot=$(realpath -- "$1")
kernel_image=$(realpath -- "$2")
output_boot=$(realpath -m -- "$3")
[[ ! -e "$output_boot" ]] || { echo "Output already exists: $output_boot" >&2; exit 1; }
echo "1f2f319f3ab051b5b5ebdefb92abba250f9dba7a65798f917b457bab7076d131  $stock_boot" | sha256sum -c -
magiskboot_tool=$(command -v "${MAGISKBOOT:-magiskboot}")
temp_dir=$(mktemp -d "${TMPDIR:-/tmp}/muyu-repack.XXXXXX")
trap 'rm -rf -- "$temp_dir"' EXIT
cd "$temp_dir"
"$magiskboot_tool" unpack -h "$stock_boot"
cp -- "$kernel_image" kernel
"$magiskboot_tool" repack "$stock_boot" "$output_boot"
python3 - "$output_boot" "$kernel_image" <<'PY'
from pathlib import Path
import struct
import sys
boot = Path(sys.argv[1]).read_bytes()
kernel = Path(sys.argv[2]).read_bytes()
assert boot[:8] == b'ANDROID!', 'Unexpected boot magic'
assert struct.unpack_from('<I', boot, 40)[0] == 4, 'Unexpected boot header version'
assert struct.unpack_from('<I', boot, 12)[0] == 0, 'Unexpected ramdisk in boot'
size = struct.unpack_from('<I', boot, 8)[0]
assert boot[4096:4096 + size] == kernel, 'Repacked kernel payload differs'
assert len(boot) == 100663296, 'Unexpected boot partition image size'
print('PASS: boot v4, original partition size, exact compiled kernel payload')
PY
sha256sum -- "$output_boot"
