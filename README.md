# 👛 DompetKeluarga - Household Finance & Utility Manager

> **Mini Startup Project - Meet 2: Data and Calculation Design**  
> _Mata Kuliah: Programming Fundamentals (Python) | Universitas Cakrawala_

---

## 📌 Deskripsi Proyek

**DompetKeluarga** adalah aplikasi manajemen keuangan rumah tangga berbasis Python yang dirancang untuk membantu keluarga mencatat pengeluaran harian, mengelola komitmen tagihan bulanan, serta menganalisis kesehatan anggaran secara otomatis dan _real-time_.

Aplikasi ini menerapkan pendekatan **Separation of Input and Analytics**, di mana proses pencatatan pengeluaran dilakukan secara independen, dan kalkulasi rasio kesehatan finansial diproses saat diminta oleh pengguna (_manual trigger_).

---

## 🌟 Unique Selling Points (USP)

- 🚀 **Smart Alert H-3 Engine:** Notifikasi proaktif berbasis kalkulasi mundur hari (`days_left`) untuk tagihan yang mendekati jatuh tempo (H-3 sampai Hari-H, `[WARNING MERAH]`) atau yang sudah lewat jatuh tempo (`[EXPIRED MERAH]`).
- 📊 **Real Commitment Analytics:** Menghitung tagihan wajib bulanan (Paid & Unpaid) ke dalam rasio kesehatan anggaran agar analisis status keuangan (`HIJAU`, `KUNING`, `MERAH`) 100% akurat.
- 🧘 **Zero-Stress Tracking:** Pemisahan antara fase pencatatan harian pasif dengan fase eksekusi kalkulasi analisis keuangan.
- 🛠️ **Modular Multi-Developer Architecture:** Kode terpisah antar modul yang siap dimigrasikan ke antarmuka visual (Figma UI / Mobile App).

---

## 👥 Anggota Projec Dompet Keluarga

| Nama Developer               | Peran / Modul | File Modul                    | Tanggung Jawab Utama                                                                                                         |
| :--------------------------- | :------------ | :---------------------------- | :--------------------------------------------------------------------------------------------------------------------------- |
| **Adzril Adzim Hendrynov**   | Project Lead  | `finance_core.py` & `main.py` | Inisialisasi struktur data akun, konsolidasi pemasukan, _engine_ kalkulasi kesehatan finansial, dan _main application loop_. |
| **Adriel Massimo Rafinaldi** | Dev 1         | `expense_tracker.py`          | Modul pencatatan belanja harian (CRUD), pemetaan kategori belanja, dan rekapitulasi riwayat harian.                          |
| **Darell Damiri**            | Dev 2         | `bills_analytics.py`          | Modul manajemen tagihan rutin bulanan (CRUD), status pelunasan (`is_paid`), dan _Smart Alert System_ H-3 jatuh tempo.        |

---

## 🗂️ Struktur Repositori

```text
dompet-keluarga_kelompok-9/
│
├── .gitignore          # Mencegah file cache Python ter-push
├── README.md           # Dokumentasi lengkap proyek
├── main.py             # Entry point aplikasi & interaksi menu utama
├── finance_core.py     # Logika core engine & kalkulasi analisis (Project Lead)
├── expense_tracker.py  # Modul pengeluaran harian (Dev 1 - Adriel)
├── bills_analytics.py  # Modul tagihan bulanan & Smart Alert (Dev 2 - Darell)
└── data.json           # File penyimpanan lokal (Persistence Layer)
```

---

## 🚀 Cara Menjalankan

Pastikan **Python 3** terpasang, lalu jalankan dari folder proyek:

### 1. Menjalankan Aplikasi Utama

```bash
py main.py
```

Saat aplikasi dibuka:
- Data otomatis dimuat dari `data.json` (dibuat baru jika belum ada).
- Status tagihan bulanan di-reset otomatis jika bulan berganti.
- Smart Alert H-3 langsung memeriksa tagihan jatuh tempo.

### 2. Self-Check (Tes Otomatis)

Uji mandiri **Smart Alert Engine** (modul `bills_analytics.py`) dengan tanggal simulasi:

```bash
py main.py --self-check
```

Output sukses: `SELF-CHECK PASS: ...` (exit code `0`).

### 3. Self-Check Finance Core

Uji mandiri **core engine** (`finance_core.py`) — inisialisasi skema, konsolidasi pemasukan, kalkulasi balance & kesehatan anggaran:

```bash
py finance_core.py
```

### 4. Menyimpan Data (Ctrl+C)

Semua perubahan tersimpan otomatis ke `data.json` saat:
- Keluar normal lewat menu **0. Keluar**, atau
- Tekan **Ctrl+C** (atau EOF) kapan saja — aplikasi menyimpan data terakhir **sebelum** keluar (`[INFO] Keluar paksa (Ctrl+C / EOF) - menyimpan data terakhir...`).

---

## 📝 Log Kontribusi Individu (Individual Contribution Log)

### 👤 **Darell Damiri (Dev 2)**

- **Modul Dikerjakan:** `bills_analytics.py` (Monthly Bills & Smart Alert System)
- **Spesifikasi Data:**
  - `bill_id` (`int`), `bill_name` (`str`), `amount` (`float`), `due_day` (`int`), `is_paid` (`bool`).
- **Fitur & Logika yang Dibuat:**
  1. **Registrasi & Rekap Tagihan:** Fungsi `add_monthly_bill()` dan `view_monthly_bills()` untuk pencatatan dan menampilkan tabel tagihan bulanan.
  2. **Pelunasan Tagihan:** Fungsi `mark_bill_as_paid()` untuk merubah status pembayaran dari `BELUM DIBAYAR` (`False`) menjadi `LUNAS` (`True`).
  3. **Manajemen Record:** Fungsi `update_monthly_bill()` dan `delete_monthly_bill()` untuk edit dan hapus data tagihan.
  4. **Smart Alert Engine (H-3 Warning):** Fungsi `check_due_date_alerts()` menggunakan kalkulasi aritmatika selisih hari `(due_day - current_day)` dan operator relasional/logika untuk pemicu notifikasi `[WARNING MERAH]` (H-3 sampai Hari-H) dan `[EXPIRED MERAH]` (sudah lewat jatuh tempo). `due_day` melebihi akhir bulan otomatis di-clamp (mis. tgl 31 di bulan 30 hari → tgl 30), dan fungsi mendukung parameter tanggal simulasi `current_day`/`current_month`/`current_year` untuk pengujian.

---
