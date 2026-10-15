#!/usr/bin/env bash
# Apply the official KernelSU-Next GKI2 LKM patch; never flashes a device.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
asset_dir=${KSU_ASSET_DIR:-"$project_dir/work-stock/ksunext-v3.4.2"}
manager_variant=${KSU_MANAGER_VARIANT:-spoofed}
case "$manager_variant" in
    spoofed)
        manager_asset=KernelSU_Next_v3.4.2-spoofed_33355-release.apk
        manager_digest=e27ad21204e8f58a4268c41725de97341c62a2f4acca7fa4dda256e9d7863d01
        variant_suffix=-spoofed ;;
    normal)
        manager_asset=KernelSU_Next_v3.4.2_33355-release.apk
        manager_digest=774a5511f7034a4930e881114e202319cbdc34c5aaaa5c7c6b6d2902364e4c58
        variant_suffix= ;;
    *) echo 'KSU_MANAGER_VARIANT must be spoofed or normal' >&2; exit 1 ;;
esac
dist_dir=${KSU_DIST_DIR:-"$project_dir/output/stock-6.1.138-ksunext-lkm$variant_suffix"}
base_boot=${BASE_BOOT:-"$project_dir/output/stock-6.1.138/boot-Droidspaces-OS3.0.304.0.WOYMIXM.img"}
kernel_config=${KERNEL_CONFIG:-"$project_dir/output/stock-6.1.138/kernel.config"}
system_map=${SYSTEM_MAP:-"$(dirname -- "$kernel_config")/System.map"}
output_name=boot-Droidspaces-KSUNext-LKM-v3.4.2-OS3.0.304.0.WOYMIXM.img
release_url=https://github.com/KernelSU-Next/KernelSU-Next/releases/download/v3.4.2
mkdir -p "$asset_dir" "$dist_dir"
[[ -f "$base_boot" ]]
[[ -f "$system_map" ]]
[[ ! -e "$dist_dir/$output_name" ]] || { echo 'Output exists; choose a new KSU_DIST_DIR.' >&2; exit 1; }
python3 "$project_dir/scripts/check-config.py" "$kernel_config"
fetch_asset() {
    local name=$1 digest=$2
    if [[ ! -f "$asset_dir/$name" ]]; then
        curl -fL --retry 3 "$release_url/$name" -o "$asset_dir/$name"
    fi
    echo "$digest  $asset_dir/$name" | sha256sum -c -
}
fetch_asset aarch64_android14-6.1_kernelsu.ko 961d2ef0e135a71d2620f10ebdc6932ff5b43069c5cf7da595fba5ab666c4b72
fetch_asset ksud-x86_64-unknown-linux-musl 4d22f89416e7eef8f684f1ed03d2bea19da33c7d41266546e94fd7d1f6cbeca9
fetch_asset "$manager_asset" "$manager_digest"
if [[ ! -f "$asset_dir/avbtool.py" ]]; then
    curl -fL --retry 3 'https://android.googlesource.com/platform/external/avb/+/761178607206f4cb2af79ed9eec52d8cbd814adb/avbtool.py?format=TEXT' -o "$asset_dir/avbtool.py.base64"
    base64 -d "$asset_dir/avbtool.py.base64" > "$asset_dir/avbtool.py"
fi
echo "e5a664a38db623da00f080219bc0ee60a640a9dc4a872803616fae4938ac749b  $asset_dir/avbtool.py" | sha256sum -c -
chmod +x "$asset_dir/ksud-x86_64-unknown-linux-musl"
"$asset_dir/ksud-x86_64-unknown-linux-musl" boot-patch-v2 \
    --boot "$base_boot" --module "$asset_dir/aarch64_android14-6.1_kernelsu.ko" \
    --output "$dist_dir/$output_name" 2>&1 | tee "$dist_dir/patch.log"
grep -Eq 'Module fixups: [1-9][0-9]*, unresolved: 0$' "$dist_dir/patch.log"
python3 "$project_dir/scripts/normalize-avb.py" "$dist_dir/$output_name" "$asset_dir/avbtool.py" \
    > "$dist_dir/avb-check.json"
python3 "$project_dir/scripts/check-ksunext-image.py" \
    "$base_boot" "$dist_dir/$output_name" \
    "$asset_dir/aarch64_android14-6.1_kernelsu.ko" "$system_map" "$dist_dir/patch.log" \
    > "$dist_dir/ksunext-image-check.json"
cp "$asset_dir/aarch64_android14-6.1_kernelsu.ko" "$dist_dir/kernelsu.ko"
cp "$asset_dir/$manager_asset" "$dist_dir/"
"$asset_dir/ksud-x86_64-unknown-linux-musl" get-sign \
    "$dist_dir/$manager_asset" > "$dist_dir/manager-signature.txt"
grep -q 'size: 0x3e6, hash: 79e590113c4c4c0c222978e413a5faa801666957b1212a328e46c00c69821bf7' "$dist_dir/manager-signature.txt"
(cd "$dist_dir" && sha256sum "$output_name" kernelsu.ko "$manager_asset" > SHA256SUMS)
echo "Patched LKM boot image: $dist_dir/$output_name"
