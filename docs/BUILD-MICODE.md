# Muyu kernel dengan konfigurasi Droidspaces

Target source: Xiaomi Pad 7 Pro (`muyu`), cabang resmi `muyu-v-oss`.
Build ini mengikuti bagian **GKI** dari dokumentasi Droidspaces.

## Versi yang dipakai

| Komponen | Versi / commit |
| --- | --- |
| Source Xiaomi | `681e88870888dec258dd48b0ab8c908b303eb159` |
| Kernel | `6.1.68`, Android 14, KMI generation 11 |
| Toolchain | Android Clang `r487747c`, versi 17.0.2 |
| Repo toolchain | `425c8149f17c8d9914bf690b4d5abe45a13fb993` |
| Dokumentasi Droidspaces | `0aa20da53656790aee4747537bfacb301b165aec` |
| Android Kernel Tutorials | `f0e815e5ee1197e7d25142c74060dfa4e10d38da` |

“Terbaru” di sini berarti HEAD cabang Xiaomi yang ditautkan saat diperiksa pada
15 Oktober 2026. Commit Xiaomi tersebut diterbitkan pada Januari 2025. Ini bukan
upgrade ke Linux terbaru atau bukti cocok dengan stock ROM Global terbaru.

## Perubahan

- `001-sysvipc-kabi.patch`: patch resmi panduan Droidspaces, memindahkan field
  SYSVIPC ke slot padding 6, 7, dan 8 pada `task_struct`.
- `002-droidspaces-gki-config.patch`: mengedit `gki_defconfig` sesuai panduan GKI,
  termasuk IPC/PID/user namespace, devtmpfs, IPv6 NAT, macvlan, firewall/ipset,
  serta tmpfs ACL/xattr.
- `003-drop-missing-driver-references.patch`: source Xiaomi merujuk direktori
  `drivers/misc/hwid` dan `drivers/iio/stm/imu/st_asm330lhhx`, tetapi tidak
  menyertakannya. Patch menghapus referensi Kconfig/Makefile tersebut agar
  kernel GKI dapat dibangun. Ini tidak menyediakan implementasi driver itu.

`CONFIG_NETFILTER_XT_TARGET_REJECT` yang tercantum dalam panduan tidak ada di
tree Linux 6.1 ini. Target yang benar, `CONFIG_IP_NF_TARGET_REJECT` dan
`CONFIG_IP6_NF_TARGET_REJECT`, sudah aktif pada konfigurasi dasar dan diperiksa
oleh skrip verifikasi. Daftar konfigurasi tambahan yang valid ada di
`configs/droidspaces-gki.config`.

`CONFIG_CFS_BANDWIDTH` dan `CONFIG_CGROUP_PIDS` tetap nonaktif. Karena itu,
Droidspaces tidak dapat memberlakukan `--cpus` dan `--pids-limit` dengan build
ini. `CONFIG_MEMCG` tetap aktif untuk batas memori. Pemeriksaan versi modul,
CFI, dan konfigurasi keamanan dasar tidak dinonaktifkan.

## Build ulang

Gunakan host Linux x86_64. Pada Debian/Ubuntu, siapkan dependensi:

```sh
sudo apt update
sudo apt install build-essential bc bison flex m4 patch pkg-config git curl \
  tar xz-utils zip unzip cpio rsync kmod perl python3 libssl-dev libelf-dev \
  pahole libncurses-dev zlib1g-dev libyaml-dev lz4 zstd device-tree-compiler
bash build.sh
```

Skrip mengunduh source dan toolchain yang disebut di atas, menerapkan patch,
memakai `gki_defconfig`, memeriksa konfigurasi hasil resolusi, lalu membangun
`Image`, `Image.gz`, `Image.lz4`, dan modul GKI yang dipilih konfigurasi tersebut.
Build ini tidak menggabungkan fragmen `vendor/pineapple_GKI.config` dan
`vendor/muyu_GKI.config`: fragmen itu digunakan alur mixed build Qualcomm untuk
modul vendor; kernel boot GKI memakai konfigurasi GKI. Build ulang semua driver
vendor/out-of-tree serta image vendor tidak termasuk dalam artefak ini.

Variabel opsional: `JOBS`, `WORK_DIR`, `CLANG_DIR`, dan `DIST_DIR`. Skrip tidak
mereset checkout yang sudah ada. Commit source harus sesuai; untuk source lain
gunakan direktori kerja baru dan tinjau ulang patch serta kompatibilitasnya.

Hasil berada di `output/`. `Image*` adalah payload kernel mentah, **bukan
`boot.img` dan bukan ZIP flashable**. `Module.symvers` disediakan untuk
pemeriksaan CRC simbol. Modul hasil kompilasi tetap ada di direktori build;
jangan mengganti modul vendor stock dengan modul tersebut secara sembarang.

## Sebelum memasang

1. Catat nomor lengkap HyperOS, `uname -r`, dan `/proc/version` pada tablet.
   Cocokkan dengan basis source. Versi 6.1 saja belum membuktikan kompatibilitas
   KMI/CRC. Kernel dari lini 6.6 atau Android/KMI generation berbeda tidak cocok.
2. Ambil `boot.img` asli dari paket ROM **yang persis sedang terpasang**.
   Simpan salinan untuk pemulihan. Bootloader harus sudah terbuka untuk
   menjalankan boot image kustom.
3. Periksa modul stock terhadap `Module.symvers` bila tersedia. Patch padding
   tidak membuktikan semua modul pada ROM terbaru kompatibel.
4. Repack menggunakan `magiskboot` di direktori kerja baru:

   ```sh
   cp /path/to/stock/boot.img ./boot.img
   magiskboot unpack boot.img
   cp /path/to/output/Image ./kernel
   magiskboot repack boot.img
   ```

   Hasilnya `new-boot.img`. Gunakan image asli sebagai basis untuk mempertahankan
   metadata dan ramdisk. Pastikan alat mendukung format kompresi/signature image
   stock. Jangan menulis payload `Image` langsung ke partisi boot. Repack belum
   sama dengan pengujian boot atau validasi AVB pada perangkat.
5. Uji boot sementara bila perangkat mendukungnya dan siapkan pemulihan ke image
   stock. Periksa Wi-Fi, layar, touch, audio, pengisian daya, dan log modul sebelum
   mempertimbangkan pemasangan permanen.
6. Pada Droidspaces jalankan **Settings → Requirements → Check Requirements**,
   atau `droidspaces check` dengan akses root. Uji container, namespace, NAT,
   overlay, serta batas memori. Dukungan konfigurasi belum membuktikan semua
   fungsi berhasil pada perangkat nyata.

Tidak ada akses tablet dalam lingkungan build ini. Root yang dibutuhkan
Droidspaces harus tersedia di perangkat; KernelSU/Magisk tidak ditambahkan ke
source kernel oleh proyek ini.

## Referensi

- https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/muyu-v-oss
- https://github.com/ravindu644/Droidspaces-OSS/blob/0aa20da53656790aee4747537bfacb301b165aec/Documentation/Kernel-Configuration.md
- https://github.com/ravindu644/Android-Kernel-Tutorials/tree/f0e815e5ee1197e7d25142c74060dfa4e10d38da

Patch SYSVIPC mempertahankan atribusi pengarang aslinya. Source kernel mengikuti
lisensi upstream; lisensi repositori pembungkus tidak mengganti lisensi kernel.
