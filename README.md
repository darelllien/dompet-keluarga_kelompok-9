# 👛 DompetKeluarga - Household Finance & Utility Manager

> **Mini Startup Project - Meet 2: Data and Calculation Design**  
> _Mata Kuliah: Programming Fundamentals (Python) | Universitas Cakrawala_

---

## 📌 Deskripsi Proyek

**DompetKeluarga** adalah aplikasi manajemen keuangan rumah tangga berbasis Python yang dirancang untuk membantu keluarga mencatat pengeluaran harian, mengelola komitmen tagihan bulanan, memantau arus kas, serta menganalisis kesehatan anggaran secara otomatis dan _real-time_.

Aplikasi ini menerapkan pendekatan **Separation of Input and Analytics**, di mana proses pencatatan pengeluaran dilakukan secara independen, dan kalkulasi rasio kesehatan finansial diproses saat diminta oleh pengguna (_manual trigger_).

---

## 🌟 Unique Selling Points (USP)

- 🚀 **Smart Alert H-3 Engine:** Notifikasi proaktif berbasis kalkulasi mundur hari (`days_left`) untuk tagihan yang mendekati jatuh tempo (H-3 sampai Hari-H, `[WARNING MERAH]`), tagihan lewat jatuh tempo (`[EXPIRED MERAH]`), serta peringatan siklus bulan depan untuk tagihan yang sudah lunas.
- 📊 **Real Commitment Analytics & Monthly Health:** Engine kesehatan anggaran bulanan berbasis rasio `HIJAU` (sisa >= 30%), `KUNING` (sisa > 0%), dan `MERAH` (defisit/pemasukan nihil) yang terisolasi per siklus bulan berjalan.
- 🔒 **Permanent Bill Ledger:** Pembukuan kas stabil dengan buku besar (*ledger*) permanen pelunasan tagihan (`bill_payments`) sehingga saldo kas riil tidak melonjak saat tagihan di-reset bulanan, diedit, atau dihapus, lengkap dengan fitur **Undo Pembatalan Pelunasan**.
- 🔍 **Multi-Period Transaction Filter:** Penyaringan transaksi terpadu (Hari Ini, Minggu Ini, Bulan Ini) mencakup belanja harian, pelunasan tagihan bulanan, dan pemasukan.
- 🧘 **Zero-Stress Tracking:** Pemisahan antara fase pencatatan harian pasif dengan fase eksekusi kalkulasi analisis keuangan.
- 🛠️ **Modular Multi-Developer Architecture:** Kode modular terpisah antar file modul mandiri dengan kontrak skema data terpusat dan penyimpanan atomik aman.

---

## 👥 Anggota Project Dompet Keluarga

| Nama Developer               | Peran / Modul | File Modul                    | Tanggung Jawab Utama                                                                                                         |
| :--------------------------- | :------------ | :---------------------------- | :--------------------------------------------------------------------------------------------------------------------------- |
| **Adzril Adzim Hendrynov**   | Project Lead  | `finance_core.py` & `main.py` | Inisialisasi struktur data akun, konsolidasi pemasukan (CRUD), buku besar kas & ledger tagihan, engine kalkulasi kesehatan finansial per bulan, penyimpanan atomik, dan _main application loop_. |
| **Adriel Massimo Rafinaldi** | Dev 1         | `expense_tracker.py`          | Modul pencatatan belanja harian (CRUD), validasi teks & tanggal standar, pemetaan kategori belanja, dan rekapitulasi riwayat harian. |
| **Darell Damiri**            | Dev 2         | `bills_analytics.py`          | Modul manajemen tagihan rutin bulanan (CRUD), status pelunasan & pembatalan pelunasan (*undo mark paid*), proteksi edit nominal tagihan lunas, dan _Smart Alert System_ H-3 jatuh tempo. |
| **Guido Poli Lau**           | Dev 3         | `transaction_filter.py`       | Modul filter transaksi multi-periode (Hari Ini, Minggu Ini, Bulan Ini) yang menyaring belanja harian, pembayaran tagihan bulanan, dan pemasukan secara komprehensif. |

---

## 🗂️ Struktur Repositori

```text
dompet-keluarga_kelompok-9/
│
├── .gitignore             # Mengabaikan file cache Python dan data lokal (data.json, data.json.bak, data.json.tmp)
├── README.md              # Dokumentasi lengkap proyek
├── main.py                # Entry point aplikasi & interaksi menu utama CLI
├── finance_core.py        # Logika core engine, kalkulasi analisis, ledger, & persistence (Project Lead - Adzril)
├── expense_tracker.py     # Modul pengeluaran harian CRUD (Dev 1 - Adriel)
├── bills_analytics.py     # Modul tagihan bulanan & Smart Alert (Dev 2 - Darell)
├── transaction_filter.py  # Modul filter transaksi hari/minggu/bulan (Dev 3 - Guido Poli Lau)
├── simulate_session.py    # Skrip simulasi pengujian alur interaktif end-to-end
└── data.json              # File penyimpanan lokal (Persistence Layer - tidak di-commit)
```

---

## 🚀 Cara Menjalankan

Pastikan **Python 3** terpasang, lalu jalankan dari terminal folder proyek:

### 1. Menjalankan Aplikasi Utama

```bash
py main.py
```
*(atau `python main.py` / `python3 main.py`)*

Saat aplikasi dibuka:
- Data otomatis dimuat dari `data.json` (dibuat baru secara otomatis jika belum ada).
- **Onboarding profil SEKALI:** jika `profile.nama` masih kosong, aplikasi meminta **nama** + **pemasukan bulanan**. Setelah tersimpan, onboarding tidak muncul lagi.
- Arsip pelunasan lama disinkronkan ke ledger kas dan status tagihan bulanan di-reset otomatis jika bulan berganti (termasuk deteksi pergantian bulan saat aplikasi tetap terbuka).
- Smart Alert H-3 langsung memeriksa tagihan jatuh tempo dan menampilkan notifikasi.

### 2. Self-Check (Tes Otomatis Masing-Masing Modul)

Setiap modul dilengkapi tes mandiri (*self-check* bawaan):

```bash
# Uji modul finance_core (skema, kalkulasi, ledger, parsing angka)
py finance_core.py

# Uji modul bills_analytics (CRUD tagihan, pelunasan, undo, proteksi)
py bills_analytics.py

# Uji modul expense_tracker (CRUD belanja harian, normalisasi tanggal)
py expense_tracker.py --self-check

# Uji modul transaction_filter (filter belanja, tagihan dibayar, pemasukan)
py transaction_filter.py --self-check

# Uji integrasi main application
py main.py --self-check
```

### 3. Simulasi Sesi End-to-End

Uji otomatis alur menu CLI interaktif dari onboarding sampai checkout/keluar:

```bash
py simulate_session.py
```

### 4. Penyimpanan Data Aman (Persistence & Ctrl+C)

Semua perubahan tersimpan atomik ke `data.json` saat:
- Melakukan transaksi (tambah/edit/hapus/lunasi).
- Keluar normal lewat menu **0. Keluar**.
- Tekan **Ctrl+C** (atau sinyal EOF) kapan saja — aplikasi secara aman menyimpan data terakhir sebelum proses berakhir.

---

## 👤 Profil Akun & Onboarding (Project Lead)

Profil akun (`wallet["profile"]`) menyimpan `nama` (str) dan `pemasukan_bulanan` (float). Dipakai untuk menyapa pengguna, prefill sumber pemasukan, dan label laporan.

### Onboarding Sekali

Saat pertama kali dijalankan (atau wallet lama tanpa `profile`), aplikasi meminta **nama** + **pemasukan bulanan** sekali lalu menyimpan:

```text
[ONBOARDING] Selamat datang! Lengkapi profil akun dulu ya.
Nama Anda: Budi
Pemasukan bulanan Anda: Rp 7500000
```

- Nama tidak boleh kosong (dipinta ulang sampai terisi).
- `pemasukan_bulanan` divalidasi lewat `parse_money` (tolak `<= 0`, `inf/nan`, `> 1e12`, non-angka).
- Format ribuan Indonesia (`5.000.000`), format internasional (`5,000,000`), maupun input bertanda `Rp` didukung secara cerdas tanpa kesalahan baca desimal.

---

## 📝 Log Kontribusi Individu (Individual Contribution Log)

### 👤 **Adzril Adzim Hendrynov (Project Lead)**
- **Modul Dikerjakan:** `finance_core.py` & `main.py`
- **Fitur & Logika:**
  1. **Core Data Structure:** Inisialisasi dan sanitasi data `wallet` terpusat.
  2. **Persistence Layer Atomik:** Load/save `data.json` dengan penulisan file temporer dan auto-backup jika file rusak (`.bak`).
  3. **Konsolidasi Pemasukan:** CRUD pemasukan dan pencatatan riwayat transaksi.
  4. **Permanent Bill Ledger:** Mekanisme pembukuan permanen tagihan terbayar (`bill_payments`) agar saldo kas tidak melompat saat pergantian siklus atau penghapusan tagihan, serta fungsi pembatalan pelunasan (`unmark_bill_payment`).
  5. **Engine Kesehatan Anggaran:** Kalkulasi rasio kesehatan finansial per bulan (`HIJAU`, `KUNING`, `MERAH`).

### 👤 **Adriel Massimo Rafinaldi (Dev 1)**
- **Modul Dikerjakan:** `expense_tracker.py`
- **Fitur & Logika:**
  1. **CRUD Belanja Harian:** Tambah, lihat, edit, dan hapus pengeluaran harian.
  2. **Normalisasi Data:** Validasi pembersihan teks nama item, kategori, serta standardisasi tanggal format hari berbahasa Indonesia (`Senin, 2026-10-05`).
  3. **Robust View Display:** Tampilan tabel belanja yang tahan terhadap *missing fields* dan teks berukuran panjang.

### 👤 **Darell Damiri (Dev 2)**
- **Modul Dikerjakan:** `bills_analytics.py`
- **Fitur & Logika:**
  1. **CRUD Tagihan Bulanan:** Pendaftaran, penayangan, perbaruan, dan penghapusan komitmen tagihan.
  2. **Status Pelunasan & Pembatalan:** Fungsi pelunasan (`mark_bill_as_paid()`) serta pembatalan pelunasan (`unmark_bill_as_paid()`).
  3. **Proteksi Ledger:** Menolak pengubahan nominal pada tagihan yang sudah berstatus lunas agar pembukuan kas tetap sinkron.
  4. **Smart Alert Engine:** Algoritma peringatan H-3 hingga Hari-H (`[WARNING MERAH]`), tagihan lewat jatuh tempo (`[EXPIRED MERAH]`), serta penanganan *calendar clamp* tanggal 31.

### 👤 **Guido Poli Lau (Dev 3)**
- **Modul Dikerjakan:** `transaction_filter.py`
- **Fitur & Logika:**
  1. **Multi-Period Filtering:** Menampilkan transaksi berdasarkan rentang tanggal: Hari Ini, Minggu Ini (Senin s.d. Minggu), dan Bulan Ini (tanggal 1 s.d. akhir bulan).
  2. **Komprehensif 3 Aliran Kas:** Menggabungkan belanja harian (`daily_expenses`), pembayaran tagihan dari ledger (`bill_payments`), dan pemasukan (`transactions` income).
  3. **Rekapitulasi Arus Kas:** Menghitung total belanja, total tagihan terbayar, total pengeluaran kas riil, pemasukan, serta selisih surplus/defisit periode.
