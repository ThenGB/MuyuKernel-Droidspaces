# Droidspaces + KernelSU-Next LKM untuk muyu

Target ROM: stock Global **3.0.304.0.WOYMIXM.C07**, basis OTA resmi
**OS3.0.304.0.WOYMIXM**. Kernel **6.1.138-android14-11-Droidspaces**,
arsitektur ARM64, KMI **android14-6.1**. Versi Android userspace 16 tidak
mengubah pilihan modul menjadi android16-6.12.

## File yang digunakan

Di `output/stock-6.1.138-ksunext-lkm-spoofed/`:

- `boot-Droidspaces-KSUNext-LKM-v3.4.2-OS3.0.304.0.WOYMIXM.img`: boot image
  kandidat uji, berisi kernel Droidspaces dan KernelSU-Next LKM.
- `KernelSU_Next_v3.4.2-spoofed_33355-release.apk`: APK Manager resmi yang cocok.
- `boot-stock-OS3.0.304.0.WOYMIXM.img`: boot asli dari OTA resmi untuk pemulihan.
- `kernelsu.ko`: modul resmi untuk reproduksi patch; jangan dimuat dengan
  perintah `insmod` biasa. Patcher/loader resmi menyiapkan alamat simbolnya.
- `SHA256SUMS`, laporan JSON, dan log patch/verifikasi.

## Metode patch

Dipakai **KernelSU-Next v3.4.2**, commit
`4c706b5938665866ebe16944a481a7b91e3396af`. Modul `.ko`, ksud host, dan APK
berasal dari release resmi dan hash SHA256-nya cocok dengan metadata release.
APK yang disediakan adalah **varian spoofed v3.4.2-spoofed (33355)**, rilis
terbaru yang diperiksa pada 15 Oktober 2026. Package APK ini adalah
`kqvdie.zeykvw.hpbcyd`; sertifikatnya sama dengan varian normal dan cocok
dengan sertifikat yang diperiksa LKM. Loader resmi menemukan Manager
berdasarkan tanda tangan; package normal tidak dipin pada modul rilis.
Library ksud pada kedua varian APK identik. Gunakan satu varian Manager saja.
Ini memverifikasi kecocokan secara offline; deteksi root tetap perlu diuji.

Patcher resmi `ksud boot-patch-v2` menyisipkan bootstrap dan kapsul LKM ke
kernel pada `boot.img`. Ini tetap **LKM**, bukan driver `CONFIG_KSU=y`
yang dikompilasi ke dalam source kernel. Metode ini tidak mengubah
`init_boot`, `vendor_boot`, atau partisi modul. Kebutuhan KPROBES,
KALLSYMS_ALL, MODULES, dan BTF sudah aktif pada kernel dasar; konfigurasi
tersebut kini dipastikan secara eksplisit dalam pipeline build.

Patcher memanfaatkan metadata BTF dari kernel yang sebenarnya, menyediakan
228 perbaikan alamat simbol, lalu menyiapkan pemuatan modul pada awal boot.
Checker terpisah memastikan isi modul persis sama dengan aset resmi dan
seluruh alamat fixup cocok dengan `System.map` build ini. Checker juga
memastikan konfigurasi embedded tidak berubah dan perubahan pada kernel
dasar terbatas pada ukuran Image, bootstrap di padding kosong, serta tiga
instruksi pemanggil yang digunakan patcher resmi.

Modul resmi ini memiliki tabel `__versions` kosong sesuai desain upstream,
sehingga pemeriksaan CRC modul biasa **tidak berlaku untuk kernelsu.ko**.
Yang diperiksa untuk LKM adalah keberadaan simbol dan ketepatan fixup.
`modinfo` pada modul rilis menampilkan `6.1.166-dirty`, yaitu basis build aset
generik android14-6.1 milik upstream. Kernel tablet tetap 6.1.138; pemilihan
aset mengikuti KMI, dan 228 alamatnya diperiksa terhadap kernel yang dipakai.
Untuk modul vendor/GKI stock, pemeriksaan CRC tetap dilakukan: 39.180 impor
simbol kernel pada 789 berkas `.ko`, tanpa perbedaan atau simbol hilang.
Pengaturan MODVERSIONS dan MODULE_SIG_PROTECT kernel dasar tetap aktif.

Tidak ditambahkan opsi `--allow-shell`, mode debug ADB, atau modul SUSFS guard.
Akses root diberikan melalui persetujuan normal di Manager.

## Footer AVB pada paket terbaru

Footer bawaan repack sebelumnya masih memuat hash stock. Paket **spoofed**
ini menggantikan artefak LKM sebelumnya: hash descriptor dihitung ulang untuk
payload baru, diverifikasi dengan avbtool resmi, dan ditandai unsigned
(`Algorithm: NONE`, flags 0). Header serta payload kernel tidak berubah
selama langkah ini. Metadata ROM dan rollback index stock dipertahankan.
Tidak ada tanda tangan Xiaomi yang valid pada image kustom; metadata unsigned
yang konsisten tidak menjamin kebijakan bootloader menerima image tersebut.
Tidak diperlukan perubahan vbmeta dalam paket ini.

## Uji pada tablet

Belum ada pengujian boot, root, hardware, atau Droidspaces pada tablet nyata.
Laporan offline tidak dapat menggantikan pengujian tersebut. Bootloader perlu
terbuka. Paket `.tar.gz` adalah arsip biasa, bukan ZIP recovery.

1. Verifikasi file dengan `sha256sum -c SHA256SUMS`. Simpan boot asli dan
   pastikan ROM yang terpasang sesuai target. Jika ada root lain yang sudah
   memodifikasi `init_boot`, kembalikan image partisi itu ke stock ROM yang
   sama sebelum menggabungkan dengan kandidat ini.
2. Mulai dari boot sementara jika bootloader mendukungnya:

   ```sh
   fastboot boot boot-Droidspaces-KSUNext-LKM-v3.4.2-OS3.0.304.0.WOYMIXM.img
   ```

   Ini bukan perintah flash permanen. Bila boot sementara tidak didukung,
   gunakan alur pengujian/pemulihan perangkat yang sesuai sebelum memilih
   pemasangan permanen.
3. Setelah Android masuk, pasang APK Manager yang disertakan dan periksa
   bahwa KernelSU-Next terdeteksi aktif dalam mode LKM. Ikuti langkah setup
   userspace yang diminta Manager; tidak perlu mem-patch ulang image ini.
4. Periksa `uname -r`: harus menunjukkan
   `6.1.138-android14-11-Droidspaces`. Uji layar, touch, Wi-Fi, audio,
   pengisian daya, sleep/wake, serta reboot.
5. Berikan izin root kepada aplikasi terminal atau Shell melalui Manager,
   lalu uji:

   ```sh
   su -c id
   su -c 'droidspaces check'
   ```

   `id` harus melaporkan UID 0. Jika binary Droidspaces tidak ada di PATH,
   gunakan **Settings → Requirements → Check Requirements** dalam aplikasinya.
   Uji juga container, akses jaringan/NAT, overlay, dan batas memori. Batas
   CPU/PID tetap tidak tersedia sesuai batasan kABI yang dijelaskan di README.
6. Pertimbangkan pemasangan permanen hanya setelah pengujian di atas lulus.
   Simpan hasil pemeriksaan Manager dan Droidspaces untuk diagnosis bila
   ada kegagalan. Jangan mengganti modul stock dengan hasil kompilasi lain.

## Pemulihan

Boot sementara hilang setelah reboot. Jika sudah memasang kandidat secara
permanen dan perlu memulihkan, kembalikan **boot stock pada slot yang tadi
diubah**, menggunakan image ROM yang sama. Jangan mem-flash kedua slot
sebagai percobaan. Boot stock yang disertakan mempunyai SHA256:

```text
1f2f319f3ab051b5b5ebdefb92abba250f9dba7a65798f917b457bab7076d131
```

## Reproduksi

```sh
DIST_DIR="$PWD/output/rebuilt-base" bash build-stock.sh
MAGISKBOOT=/path/to/magiskboot bash scripts/repack-boot.sh \
  output/stock-6.1.138-ksunext-lkm-spoofed/boot-stock-OS3.0.304.0.WOYMIXM.img \
  output/rebuilt-base/Image output/rebuilt-base/boot-Droidspaces.img
BASE_BOOT="$PWD/output/rebuilt-base/boot-Droidspaces.img" \
KERNEL_CONFIG="$PWD/output/rebuilt-base/kernel.config" \
KSU_DIST_DIR="$PWD/output/rebuilt-lkm" bash patch-ksunext-lkm.sh
```

Skrip patch memerlukan host Linux x86_64. Variabel opsional:
`KSU_ASSET_DIR`, `KSU_DIST_DIR`, `BASE_BOOT`, `KERNEL_CONFIG`, dan `SYSTEM_MAP`.
`KSU_MANAGER_VARIANT=spoofed` adalah default; `normal` memilih APK normal.
Pipeline memverifikasi hash avbtool yang dipin sebelum memperbarui footer.
`scripts/normalize-avb.py` khusus ukuran, kernel, dan metadata ROM target ini.
Skrip menolak menimpa output yang sudah ada. Untuk mengulangi verifikasi
independen, diperlukan boot dasar dan `System.map` dari build yang sama:

```sh
python3 scripts/check-ksunext-image.py \
  output/stock-6.1.138/boot-Droidspaces-OS3.0.304.0.WOYMIXM.img \
  output/stock-6.1.138-ksunext-lkm-spoofed/boot-Droidspaces-KSUNext-LKM-v3.4.2-OS3.0.304.0.WOYMIXM.img \
  output/stock-6.1.138-ksunext-lkm-spoofed/kernelsu.ko \
  /path/to/kernel-build/System.map \
  output/stock-6.1.138-ksunext-lkm-spoofed/patch.log
```

Referensi resmi:

- https://github.com/KernelSU-Next/KernelSU-Next/releases/tag/v3.4.2
- https://github.com/KernelSU-Next/KernelSU-Next/blob/4c706b5938665866ebe16944a481a7b91e3396af/userspace/ksud/src/lkm_image.rs
- https://github.com/KernelSU-Next/KernelSU-Next/blob/4c706b5938665866ebe16944a481a7b91e3396af/kernel/tools/check_symbol.c
