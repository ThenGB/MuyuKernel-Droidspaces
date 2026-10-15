# Kernel muyu: Droidspaces dan KernelSU-Next LKM

Target perangkat: **Xiaomi Pad 7 Pro (`muyu`)**, stock Global
**3.0.304.0.WOYMIXM.C07** yang disebutkan pengguna.

Boot image Droidspaces **tanpa patch KernelSU** ada di
`output/droidspaces-no-kernelsu/boot-Droidspaces-NO-KSU-OS3.0.304.0.WOYMIXM.img`.
Image ini untuk partisi `boot`; `init_boot` tidak diubah. Root yang sebelumnya
dipasang pada `init_boot` tetap perlu diuji dengan kernel baru, terutama
kecocokan LKM-nya. Panduan dan reproduksi: [boot tanpa KernelSU](docs/FLASH-NO-KSU.md).
Hash image dan hasil pemeriksaan offline: [laporan build](docs/verified-no-ksu.json).
Image belum diuji boot pada tablet. Biner build berada di distribusi terpisah;
direktori `output/` tidak disimpan dalam Git.

Varian terbaru dengan root ada di `output/stock-6.1.138-ksunext-lkm-spoofed/`:
`boot-Droidspaces-KSUNext-LKM-v3.4.2-OS3.0.304.0.WOYMIXM.img`.
KernelSU-Next **v3.4.2** dipasang sebagai LKM GKI2 menggunakan patcher resmi
`ksud boot-patch-v2` dan modul resmi `aarch64_android14-6.1_kernelsu.ko`.
APK yang disertakan adalah **v3.4.2-spoofed (33355)** resmi, rilis terbaru
yang diperiksa pada 15 Oktober 2026. Sertifikat Manager cocok dengan LKM.
Footer AVB diperbarui untuk payload kustom dan diverifikasi sebagai unsigned
(`NONE`, flags 0); bootloader harus unlocked.
Panduan pemasangan, pengujian perangkat, dan pemulihan: `docs/KERNELSU-NEXT-LKM.md`.

Ada dua basis build. Keduanya dipisahkan karena source MiCode yang ditautkan
lebih tua daripada kernel di ROM tersebut.

| Build | Basis source | Tujuan |
| --- | --- | --- |
| `stock-6.1.138` | ACK `0c3d559bcd85c64dae9c9c9687abbe5347fff3ad` | Basis yang sama dengan kernel boot resmi OS3.0.304.0.WOYMIXM |
| `micode-6.1.68` | MiCode `681e88870888dec258dd48b0ab8c908b303eb159` | Hasil dari cabang `muyu-v-oss` yang diminta; bukan kandidat untuk ROM terbaru ini |

Boot resmi ROM Global diperiksa langsung dari OTA Xiaomi. Kernel di dalamnya
adalah `6.1.138-android14-11-g0c3d559bcd85-ab14529422`, dengan Clang r487747c
17.0.2. Hash partisi boot yang direkonstruksi cocok dengan manifest OTA.

Build MiCode berhasil dikompilasi, tetapi pemeriksaan terhadap 789 modul stock
menemukan 10 simbol kernel yang tidak tersedia, dengan 15 referensi impor ke
simbol-simbol itu. **Jangan memakai build 6.1.68 untuk ROM ini.** Lihat laporan
`module-crc-check.json` di folder artefaknya.

Build stock 6.1.138 selesai. Hasil akhirnya lolos pemeriksaan 39.180 impor
simbol kernel pada 789 berkas modul stock, tanpa perbedaan CRC atau simbol
hilang. Ukuran dan offset field delapan struktur yang diuji tetap sama.
120 tanda tangan modul GKI stock berhasil diverifikasi, dan sertifikat
publiknya ditemukan dalam `Image` hasil kompilasi.

## Konfigurasi Droidspaces

Patch SYSVIPC memakai slot padding kABI 6, 7, dan 8 sesuai panduan Droidspaces.
Opsi GKI yang valid diaktifkan untuk IPC/PID/user namespace, devtmpfs, IPv6 NAT,
macvlan, firewall/ipset, dan tmpfs ACL/xattr. Pemeriksaan konfigurasi mencakup
54 opsi aktif (termasuk kebutuhan LKM) serta dua opsi yang harus tetap nonaktif.

`CONFIG_NETFILTER_XT_TARGET_REJECT` dalam panduan tidak ada di tree 6.1.
Target yang tersedia, `CONFIG_IP_NF_TARGET_REJECT` dan
`CONFIG_IP6_NF_TARGET_REJECT`, sudah aktif dan ikut diverifikasi.

Sesuai panduan GKI, **batas CPU (`--cpus`) dan jumlah proses (`--pids-limit`)
tetap tidak tersedia** karena `CONFIG_CFS_BANDWIDTH` dan `CONFIG_CGROUP_PIDS`
mengubah ABI. Batas memori didukung melalui `CONFIG_MEMCG`. Pemeriksaan versi
modul dan CFI tidak dinonaktifkan. Varian dasar `stock-6.1.138` tidak memiliki
root; varian `stock-6.1.138-ksunext-lkm-spoofed` menambahkan KernelSU-Next LKM.

## Build ulang untuk stock ROM tersebut

Host: Linux x86_64, sekitar 20 GB ruang kosong dan RAM yang memadai. Dependensi
Debian/Ubuntu:

```sh
sudo apt update
sudo apt install build-essential bc bison flex m4 patch pkg-config git curl \
  tar xz-utils zip unzip cpio rsync kmod perl python3 libssl-dev libelf-dev \
  pahole libncurses-dev zlib1g-dev libyaml-dev lz4 zstd device-tree-compiler
bash build-stock.sh
```

Skrip mengunduh snapshot ACK yang tepat, memverifikasi SHA256 source, memakai
Clang yang sama, mengambil konfigurasi lengkap yang diekstrak dari kernel stock
sebagai `gki_defconfig`, lalu mengaktifkan opsi Droidspaces. Symbol trimming
stock dipertahankan dengan whitelist gabungan daftar KMI dari source ACK.
Build ini tidak membutuhkan patch untuk driver Xiaomi yang hilang pada MiCode.

Sertifikat publik penanda tangan modul stock diekstrak dari boot resmi dan
ditambahkan melalui `CONFIG_SYSTEM_TRUSTED_KEYS`. Sidik jari SHA256-nya
`0240470683ba6e8d52570f27a99eb4b8a0735a3fbd028d48e5d5e87e09cc3ba4`.
Ini mempertahankan kepercayaan kepada modul GKI stock saat kernel dibangun
dengan kunci build baru; `CONFIG_MODULE_SIG_PROTECT` tetap aktif. File PEM hanya
berisi sertifikat publik, tanpa private key.

Variabel opsional: `JOBS`, `WORK_DIR`, `OUT_DIR`, `CLANG_DIR`, `DIST_DIR`.
Hasil kernel dasar berada di `output/stock-6.1.138/`. Skrip patch mengunduh
rilis KernelSU-Next yang dipin dan memeriksa hash modul, ksud host, dan APK
Manager. Hasil patch berada di `output/stock-6.1.138-ksunext-lkm-spoofed/`.
Setelah build kernel baru, repack boot dasar memakai `scripts/repack-boot.sh`
sebelum menjalankan `patch-ksunext-lkm.sh`. Urutan lengkap yang memakai
direktori output baru ada pada bagian Reproduksi di panduan LKM.

Untuk mengulangi build dari cabang MiCode yang ditautkan, gunakan
`bash build.sh`. Detail dan batasannya ada di `docs/BUILD-MICODE.md`.

## Verifikasi

`scripts/check-config.py` memeriksa konfigurasi hasil resolusi Kconfig.
`scripts/compare-layout.py` membandingkan ukuran dan offset field pada delapan
struktur kernel dari objek probe baseline dan hasil patch.
`scripts/check-module-crcs.py` membandingkan CRC simbol kernel yang diimpor
modul stock terhadap `Module.symvers` build. Kedua skrip tersebut membutuhkan
`python3-pyelftools` / `pyelftools`.

```sh
python3 scripts/check-config.py output/stock-6.1.138/kernel.config
python3 scripts/check-module-crcs.py \
  output/stock-6.1.138/Module.symvers /path/to/extracted-stock-modules
```

Modul harus mencakup vendor ramdisk di `vendor_boot`, `vendor_dlkm`, dan
`system_dlkm`. Checker memisahkan impor dari kernel dan impor yang dipenuhi oleh
modul stock lain. Modul stock tetap digunakan; jangan menimpa partisi modul
dengan hasil kompilasi GKI tanpa alasan dan pemeriksaan tersendiri. Dalam ROM
ini diperiksa 789 berkas `.ko` (509 biner unik); sebagian modul muncul pada
lebih dari satu partisi. `scripts/check-stock-signatures.py` memverifikasi
tanda tangan 120 modul GKI stock dengan sertifikat publik tadi.

**Lolos pemeriksaan source, layout, atau CRC tidak sama dengan lolos uji boot.**
Tidak ada tablet/ADB dalam lingkungan ini, sehingga fungsi hardware dan
`droidspaces check` tetap memerlukan pengujian di perangkat.

## Penggunaan image

Boot dasar untuk reproduksi, bukan kandidat flash final, ada di
`output/stock-6.1.138/boot-Droidspaces-OS3.0.304.0.WOYMIXM.img`.
Struktur header v4, ukuran 96 MiB, dan kecocokan payload kernel sudah
diverifikasi; belum diuji boot pada tablet. Paket `.tar.gz` adalah arsip
artefak dan source pendamping, bukan installer recovery.

`Image`, `Image.gz`, dan `Image.lz4` adalah payload kernel, bukan ZIP flashable.
Untuk repack, gunakan `boot.img` asli dari ROM yang persis terpasang dengan
`magiskboot unpack boot.img`, ganti file `kernel` dengan `Image`, kemudian
`magiskboot repack boot.img` di direktori kosong khusus pekerjaan ini.
Skrip `scripts/repack-boot.sh` melakukan langkah tersebut dengan pemeriksaan
hash boot resmi dan verifikasi payload hasil repack. Contoh:

```sh
MAGISKBOOT=/path/to/magiskboot bash scripts/repack-boot.sh \
  /path/to/stock-boot.img output/stock-6.1.138/Image /path/to/new-boot.img
```

Repack ini belum memperbarui hash footer AVB. Untuk menghasilkan image tanpa
KernelSU dengan metadata yang konsisten, lanjutkan langkah normalisasi dan
verifikasi pada [panduan tanpa KernelSU](docs/FLASH-NO-KSU.md).

Bootloader perlu terbuka untuk boot image kustom; simpan boot asli untuk
pemulihan. Boot image kustom tidak memiliki tanda tangan Xiaomi yang valid.

Setelah uji boot, periksa Wi-Fi, touch, layar, audio, pengisian daya, dan log
modul. Di Droidspaces jalankan **Settings → Requirements → Check Requirements**,
kemudian uji container, NAT, overlay, dan batas memori. Akses root tetap
diperlukan oleh Droidspaces.

## Source dan panduan

- https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/muyu-v-oss
- https://android.googlesource.com/kernel/common/+/0c3d559bcd85c64dae9c9c9687abbe5347fff3ad
- https://github.com/ravindu644/Droidspaces-OSS/blob/0aa20da53656790aee4747537bfacb301b165aec/Documentation/Kernel-Configuration.md
- https://github.com/ravindu644/Android-Kernel-Tutorials/tree/f0e815e5ee1197e7d25142c74060dfa4e10d38da
- https://github.com/KernelSU-Next/KernelSU-Next/releases/tag/v3.4.2
- https://github.com/KernelSU-Next/KernelSU-Next/blob/4c706b5938665866ebe16944a481a7b91e3396af/userspace/ksud/src/lkm_image.rs

Patch mempertahankan atribusi pengarang asli. Source kernel mengikuti lisensi
upstream; lisensi repositori pembungkus tidak mengganti lisensi kernel.
