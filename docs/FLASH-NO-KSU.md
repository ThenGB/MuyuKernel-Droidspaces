# Boot Droidspaces tanpa patch KernelSU

Target: Xiaomi Pad 7 Pro (`muyu`), ROM Global **3.0.304.0.WOYMIXM.C07**.
Kernel: **6.1.138-android14-11-Droidspaces**. Nama artefak:
`boot-Droidspaces-NO-KSU-OS3.0.304.0.WOYMIXM.img`, ukuran 96 MiB, boot v4.

Image ini berisi build Droidspaces dasar, tanpa KernelSU built-in, bootstrap,
atau kapsul LKM KernelSU-Next. Partisi tujuannya `boot`; image ini tidak
mengubah `init_boot`, `vendor_boot`, atau modul stock.

## Root yang sudah ada pada init_boot

`init_boot` yang dipatch dari ROM yang sama dapat tetap digunakan saat
menguji boot image ini. Kesesuaian ROM membantu mempertahankan ramdisk yang
tepat, tetapi tidak membuktikan bahwa LKM root cocok dengan kernel baru.
Kebutuhan konfigurasi KernelSU-Next LKM sudah aktif. Pada 15 Oktober 2026,
pengguna melaporkan boot berhasil dan KernelSU yang sudah terpasang bekerja
dengan boot image tanpa patch KernelSU ini. Log pemuatan LKM belum tersedia.

Jangan menambahkan patch KernelSU ke boot ini hanya karena root sudah
dipasang melalui init_boot. Mulai dengan boot sementara jika didukung:

```sh
fastboot boot boot-Droidspaces-NO-KSU-OS3.0.304.0.WOYMIXM.img
```

Setelah Android masuk, periksa Manager, `uname -r`, dan `su -c id`.
Uji juga Wi-Fi, touch, layar, audio, pengisian daya, sleep/wake, serta
**Settings → Requirements → Check Requirements** di Droidspaces. Jika root
gagal, periksa kecocokan LKM dan log pemuatannya sebelum pemasangan permanen.
Simpan boot stock dari ROM yang sama untuk pemulihan slot yang diuji.

## Verifikasi artefak

```sh
sha256sum -c boot-Droidspaces-NO-KSU-OS3.0.304.0.WOYMIXM.img.sha256
```

SHA256 image yang telah dibuat dan diunggah:

```text
b966c2087363848b6f1352e109cab5c417d2a38cd3696391717f708455a5e5ba
```

Payload kernel identik dengan build dasar. Header dan payload tidak berubah
ketika footer AVB dinormalisasi. Hash AVB cocok dengan image baru; algoritma
`NONE`, flags 0. Image unsigned dan memerlukan bootloader unlocked.
Pemeriksaan offline tidak menggantikan uji pada masing-masing perangkat.
Pengguna telah melaporkan boot dan KernelSU berhasil, serta backend
Droidspaces berstatus installed. Keberhasilan membuat/menjalankan container,
jaringan container, fungsi hardware, dan status flash permanen belum
dilaporkan. Laporan ini belum disertai log perangkat dan hanya berlaku untuk
varian tanpa patch KernelSU yang dibahas di sini, bukan varian boot LKM terpisah.
Laporan ringkas ada di [verified-no-ksu.json](verified-no-ksu.json).

## Reproduksi dari hasil build

Gunakan boot stock dari ROM target; skrip repack memverifikasi SHA256-nya.
Sediakan magiskboot dan avbtool resmi yang dipin berikut, lalu jalankan dari
root repositori:

```sh
bash build-stock.sh
mkdir -p output/droidspaces-no-kernelsu work-stock
curl -fL --retry 3 \
  'https://android.googlesource.com/platform/external/avb/+/761178607206f4cb2af79ed9eec52d8cbd814adb/avbtool.py?format=TEXT' \
  -o work-stock/avbtool.py.base64
base64 -d work-stock/avbtool.py.base64 > work-stock/avbtool.py
echo 'e5a664a38db623da00f080219bc0ee60a640a9dc4a872803616fae4938ac749b  work-stock/avbtool.py' | sha256sum -c -
MAGISKBOOT=/path/to/magiskboot bash scripts/repack-boot.sh \
  /path/to/stock-boot.img output/stock-6.1.138/Image \
  output/droidspaces-no-kernelsu/boot-Droidspaces-NO-KSU-OS3.0.304.0.WOYMIXM.img
python3 scripts/normalize-avb.py \
  output/droidspaces-no-kernelsu/boot-Droidspaces-NO-KSU-OS3.0.304.0.WOYMIXM.img \
  work-stock/avbtool.py > output/droidspaces-no-kernelsu/avb-check.json
cd output/droidspaces-no-kernelsu
sha256sum boot-Droidspaces-NO-KSU-OS3.0.304.0.WOYMIXM.img \
  > boot-Droidspaces-NO-KSU-OS3.0.304.0.WOYMIXM.img.sha256
```

Sertifikat kunci build modul dapat berbeda pada build ulang sehingga hash
hasil rebuild tidak harus identik dengan artefak di atas. Lakukan pemeriksaan
konfigurasi, modul stock, dan uji perangkat untuk hasil build ulang.
