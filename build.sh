#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
work_dir=${WORK_DIR:-"$project_dir/work"}
kernel_dir="$work_dir/muyu"
out_dir=${OUT_DIR:-"$work_dir/out"}
dist_dir=${DIST_DIR:-"$project_dir/output/micode-6.1.68"}
clang_dir=${CLANG_DIR:-"$work_dir/clang-r487747c"}
source_commit=681e88870888dec258dd48b0ab8c908b303eb159
clang_commit=425c8149f17c8d9914bf690b4d5abe45a13fb993
mkdir -p "$work_dir" "$dist_dir"
if [[ ! -d "$kernel_dir/.git" ]]; then
    git clone --depth 1 --single-branch --branch muyu-v-oss \
        https://github.com/MiCode/Xiaomi_Kernel_OpenSource.git "$kernel_dir"
fi
if [[ $(git -C "$kernel_dir" rev-parse HEAD) != "$source_commit" ]]; then
    echo "Expected Xiaomi source $source_commit; use a fresh WORK_DIR." >&2
    exit 1
fi
if [[ ! -x "$clang_dir/bin/clang" ]]; then
    mkdir -p "$clang_dir"
    curl -fL --retry 3 \
        "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+archive/$clang_commit/clang-r487747c.tar.gz" \
        -o "$work_dir/clang-r487747c.tar.gz"
    echo "939f635364907fba0f01563ed8a0b72a678af4c772a5a050f7521d5479b08dbf  $work_dir/clang-r487747c.tar.gz" | sha256sum -c -
    tar -xzf "$work_dir/clang-r487747c.tar.gz" -C "$clang_dir"
fi
export PATH="$clang_dir/bin:$PATH"
clang --version
for patch_file in "$project_dir"/patches/*.patch; do
    if git -C "$kernel_dir" apply --check "$patch_file" 2>/dev/null; then
        git -C "$kernel_dir" apply "$patch_file"
    elif git -C "$kernel_dir" apply --reverse --check "$patch_file" 2>/dev/null; then
        echo "Already applied: $patch_file"
    else
        echo "Patch does not match source: $patch_file" >&2
        exit 1
    fi
done
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
make "${make_args[@]}" -s kernelrelease > "$dist_dir/kernelrelease.txt"
python3 "$project_dir/scripts/check-config.py" "$dist_dir/kernel.config" > "$dist_dir/config-check.txt"
git -C "$kernel_dir" diff --binary > "$dist_dir/muyu-droidspaces.patch"
(cd "$dist_dir" && sha256sum Image Image.gz Image.lz4 kernel.config Module.symvers > SHA256SUMS)
echo "Build finished: $dist_dir"
