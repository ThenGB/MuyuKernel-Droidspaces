#!/usr/bin/env bash
# Build the kernel source identified in the official OS3.0.304.0.WOYMIXM boot.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
work_dir=${WORK_DIR:-"$project_dir/work-stock"}
kernel_dir="$work_dir/ack"
out_dir=${OUT_DIR:-"$work_dir/out"}
dist_dir=${DIST_DIR:-"$project_dir/output/stock-6.1.138"}
clang_dir=${CLANG_DIR:-"$work_dir/clang-r487747c"}
source_commit=0c3d559bcd85c64dae9c9c9687abbe5347fff3ad
clang_commit=425c8149f17c8d9914bf690b4d5abe45a13fb993
archive_sha=bc81167c8f5552ef5d9808515fce5d63b780ca0d8391fe2c26653afbe2c97494
mkdir -p "$work_dir" "$dist_dir"
if [[ ! -f "$kernel_dir/.source-commit" ]]; then
    if [[ -d "$kernel_dir" ]]; then
        echo "Use a fresh WORK_DIR: $kernel_dir already exists without a source marker" >&2
        exit 1
    fi
    curl -fL --retry 3 \
        "https://android.googlesource.com/kernel/common/+archive/$source_commit.tar.gz" \
        -o "$work_dir/ack-stock.tar.gz"
    echo "$archive_sha  $work_dir/ack-stock.tar.gz" | sha256sum -c -
    mkdir -p "$kernel_dir"
    tar -xzf "$work_dir/ack-stock.tar.gz" -C "$kernel_dir"
    printf '%s\n' "$source_commit" > "$kernel_dir/.source-commit"
    cp "$kernel_dir/arch/arm64/configs/gki_defconfig" "$work_dir/original-gki_defconfig"
    cp "$kernel_dir/include/linux/sched.h" "$work_dir/original-sched.h"
fi
[[ $(cat "$kernel_dir/.source-commit") == "$source_commit" ]]
if [[ ! -x "$clang_dir/bin/clang" ]]; then
    curl -fL --retry 3 \
        "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+archive/$clang_commit/clang-r487747c.tar.gz" \
        -o "$work_dir/clang-r487747c.tar.gz"
    echo "939f635364907fba0f01563ed8a0b72a678af4c772a5a050f7521d5479b08dbf  $work_dir/clang-r487747c.tar.gz" | sha256sum -c -
    mkdir -p "$clang_dir"
    tar -xzf "$work_dir/clang-r487747c.tar.gz" -C "$clang_dir"
fi
export PATH="$clang_dir/bin:$PATH"
clang --version
clang --version | grep -q 'based on r487747c'
patch_file="$project_dir/patches/001-sysvipc-kabi.patch"
if patch --dry-run --forward -d "$kernel_dir" -p1 < "$patch_file" >/dev/null; then
    patch --forward -d "$kernel_dir" -p1 < "$patch_file"
elif ! patch --dry-run --reverse -d "$kernel_dir" -p1 < "$patch_file" >/dev/null; then
    echo "SYSVIPC patch does not match the source" >&2
    exit 1
fi
python3 - "$kernel_dir" "$project_dir" <<'PY'
import re
import sys
from pathlib import Path
kernel, project = map(Path, sys.argv[1:])
config = project.joinpath('configs/stock-OS3.0.304.0.WOYMIXM.config').read_text()
options = '\n'.join(project.joinpath('configs', name).read_text() for name in
                    ('droidspaces-gki.config', 'ksunext-lkm.config'))
for line in options.splitlines():
    if not line.strip():
        continue
    name = line.split('=')[0]
    pattern = rf'^(?:{name}=.*|# {name} is not set)$'
    config = (re.sub(pattern, line, config, flags=re.M)
              if re.search(pattern, config, re.M) else config + line + '\n')
kernel.joinpath('arch/arm64/configs/gki_defconfig').write_text(config)
trusted_key = 'certs/muyu-stock-module-signing.pem'
config = re.sub(r'^CONFIG_SYSTEM_TRUSTED_KEYS=.*$',
                f'CONFIG_SYSTEM_TRUSTED_KEYS="{trusted_key}"', config, flags=re.M)
kernel.joinpath(trusted_key).write_bytes(
    project.joinpath('configs/stock-module-signing.pem').read_bytes())
kernel.joinpath('arch/arm64/configs/gki_defconfig').write_text(config)
symbols = set()
for path in kernel.joinpath('android').glob('abi_gki_aarch64*'):
    if path.suffix in ('.xml', '.stg'):
        continue
    for line in path.read_text(errors='replace').splitlines():
        line = line.split('#')[0].strip()
        if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', line):
            symbols.add(line)
kernel.joinpath('abi_symbollist.raw').write_text('\n'.join(sorted(symbols)) + '\n')
PY
export KBUILD_BUILD_USER=builder KBUILD_BUILD_HOST=muyu-droidspaces
export KBUILD_BUILD_TIMESTAMP='Thu Oct 15 00:00:00 UTC 2026'
export KBUILD_BUILD_VERSION=1
make_args=(-C "$kernel_dir" O="$out_dir" ARCH=arm64 LLVM=1 LLVM_IAS=1
           HOSTCC=gcc HOSTCXX=g++ LOCALVERSION=-android14-11-Droidspaces
           'KCFLAGS=-D__ANDROID_COMMON_KERNEL__')
make "${make_args[@]}" gki_defconfig
python3 "$project_dir/scripts/check-config.py" "$out_dir/.config"
make "${make_args[@]}" -j"${JOBS:-$(nproc)}" Image Image.gz Image.lz4 modules 2>&1 | tee "$dist_dir/build.log"
cp "$out_dir/arch/arm64/boot/"{Image,Image.gz,Image.lz4} "$dist_dir/"
cp "$out_dir/.config" "$dist_dir/kernel.config"
cp "$out_dir/Module.symvers" "$dist_dir/"
cp "$out_dir/System.map" "$dist_dir/"
cp "$kernel_dir/abi_symbollist.raw" "$dist_dir/"
make "${make_args[@]}" -s kernelrelease > "$dist_dir/kernelrelease.txt"
python3 "$project_dir/scripts/check-config.py" "$dist_dir/kernel.config" > "$dist_dir/config-check.txt"
(cd "$dist_dir" && sha256sum Image Image.gz Image.lz4 kernel.config Module.symvers System.map abi_symbollist.raw > SHA256SUMS)
echo "Build finished: $dist_dir"
