# ==============================================================================
# MAIN APPLICATION LOOP - DOMPETKELUARGA (ENTRY POINT)
# Pembuat : Adzril Adzim Hendrynov (Project Lead)
# File    : main.py
# Deskripsi:
#   - Entry point aplikasi CLI interaktif (menu utama berbahasa Indonesia)
#   - Mengintegrasikan seluruh modul:
#       * finance_core.py   (Lead  : pemasukan, saldo, kesehatan anggaran)
#       * bills_analytics.py (Darell: tagihan bulanan & smart alert)
#       * expense_tracker.py (Adriel: pencatatan harian - via try-import)
# ==============================================================================

try:
    import finance_core
except ImportError:
    print("[FATAL] Modul finance_core.py tidak ditemukan. Jalankan dari folder proyek.")
    raise SystemExit(1)

try:
    import bills_analytics
except ImportError:
    print("[FATAL] Modul bills_analytics.py tidak ditemukan. Jalankan dari folder proyek.")
    raise SystemExit(1)

# Modul Adriel bersifat OPSIONAL saat ini (belum diimplementasikan).
# Gunakan try-import agar aplikasi TETAP berjalan walau modul masih kosong.
try:
    import expense_tracker
    # Deteksi apakah modul sudah diisi: minimal harus ada fungsi add_expense
    HAS_EXPENSE_TRACKER = callable(getattr(expense_tracker, "add_expense", None))
except ImportError:
    expense_tracker = None
    HAS_EXPENSE_TRACKER = False

DATA_FILE = "data.json"

from typing import Any, cast


# ==============================================================================
# FUNGSI BANTU INPUT
# ==============================================================================

def input_number(prompt):
    """Ambil input angka float valid (tolak non-angka, inf/nan, <= 0, > MAX_AMOUNT)."""
    while True:
        raw = input(prompt).strip()
        ok, value = finance_core.parse_money(raw)
        if ok:
            return value
        print("  [ERROR] Masukkan angka valid (bilangan > 0, maks Rp 1.000.000.000.000).")


def input_int(prompt, min_val=None, max_val=None):
    """Ambil input integer dengan rentang opsional."""
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("  [ERROR] Masukkan angka bulat yang valid.")
            continue
        if min_val is not None and value < min_val:
            print(f"  [ERROR] Nilai minimal {min_val}.")
            continue
        if max_val is not None and value > max_val:
            print(f"  [ERROR] Nilai maksimal {max_val}.")
            continue
        return value


# ==============================================================================
# SUBMENU TAGIHAN BULANAN (MODUL DARELL)
# ==============================================================================

def menu_bills(wallet):
    """Submenu CRUD + Smart Alert tagihan bulanan (delegasi ke bills_analytics)."""
    while True:
        print("\n============= MENU TAGIHAN BULANAN =============")
        print("  1. Lihat Daftar Tagihan")
        print("  2. Tambah Tagihan Baru")
        print("  3. Lunasikan Tagihan")
        print("  4. Edit Tagihan")
        print("  5. Hapus Tagihan")
        print("  6. Cek Smart Alert (Jatuh Tempo)")
        print("  0. Kembali ke Menu Utama")
        print("================================================")

        choice = input_int("Pilih menu (0-6): ", 0, 6)

        if choice == 1:
            q = input("Cari nama tagihan (Enter = semua): ").strip()
            bills_analytics.view_monthly_bills(wallet, q or None)

        elif choice == 2:
            name = input("Nama tagihan: ").strip()
            amount = input_number("Nominal tagihan: Rp ")
            due_day = input_int("Tanggal jatuh tempo (1-31): ", 1, 31)
            ok, msg = bills_analytics.add_monthly_bill(wallet, name, amount, due_day)
            print(f"  {'[OK]' if ok else '[GAGAL]'} {msg}")
            if ok:
                print("  " + finance_core.save_data(wallet, DATA_FILE))

        elif choice == 3:
            bill_id = input_int("ID tagihan yang dilunasi: ", 1)
            ok, msg = bills_analytics.mark_bill_as_paid(wallet, bill_id)
            print(f"  {'[OK]' if ok else '[GAGAL]'} {msg}")
            if ok:
                print("  " + finance_core.save_data(wallet, DATA_FILE))

        elif choice == 4:
            bill_id = input_int("ID tagihan yang diedit: ", 1)
            name = input("Nama tagihan baru: ").strip()
            amount = input_number("Nominal tagihan baru: Rp ")
            due_day = input_int("Tanggal jatuh tempo baru (1-31): ", 1, 31)
            ok, msg = bills_analytics.update_monthly_bill(wallet, bill_id, name, amount, due_day)
            print(f"  {'[OK]' if ok else '[GAGAL]'} {msg}")
            if ok:
                print("  " + finance_core.save_data(wallet, DATA_FILE))

        elif choice == 5:
            bill_id = input_int("ID tagihan yang dihapus: ", 1)
            ok, msg = bills_analytics.delete_monthly_bill(wallet, bill_id)
            print(f"  {'[OK]' if ok else '[GAGAL]'} {msg}")
            if ok:
                print("  " + finance_core.save_data(wallet, DATA_FILE))

        elif choice == 6:
            show_alerts(wallet)

        elif choice == 0:
            break


def show_alerts(wallet):
    """Tampilkan Smart Alert H-3 dari modul Darell."""
    alerts = bills_analytics.check_due_date_alerts(wallet)
    if not alerts:
        print("\n[INFO] Tidak ada tagihan yang perlu diingatkan. Semua aman.")
        return
    print("\n============= SMART ALERT JATUH TEMPO =============")
    for alert in alerts:
        print("  " + alert)
    print("====================================================")


# ==============================================================================
# SUBMENU PENGELUARAN HARIAN (MODUL ADRIEL - OPSIONAL)
# ==============================================================================

def show_balance(wallet):
    """Tampilkan ringkasan saldo (engine Lead)."""
    b = finance_core.compute_balance(wallet)
    print("\n=============== RINGKASAN KEUANGAN ===============")
    print(f"  Total Pemasukan          : Rp {b['total_pemasukan']:,.2f}")
    print(f"  Total Pengeluaran Harian : Rp {b['total_pengeluaran']:,.2f}")
    print(f"  Komitmen Tagihan Total   : Rp {b['komitmen_tagihan_total']:,.2f}")
    print(f"    - Sudah Lunas          : Rp {b['komitmen_lunas']:,.2f}")
    print(f"    - Belum Lunas          : Rp {b['komitmen_belum_lunas']:,.2f}")
    print(f"--------------------------------------------------")
    print(f"  Saldo Kas                : Rp {b['saldo_kas']:,.2f}")
    print(f"  Saldo Setelah Komitmen   : Rp {b['saldo_setelah_komitmen']:,.2f}")
    print("===================================================")


def menu_expense(wallet):
    """Pencatatan pengeluaran harian -> delegasi ke modul Adriel (jika tersedia)."""
    if not HAS_EXPENSE_TRACKER:
        print("\n[INFO] Modul pencatatan pengeluaran harian (Adriel) BELUM TERSEDIA.")
        print("       Modul expense_tracker.py masih kosong - fitur ini menyusul.")
        return

    print("\n[OK] Modul expense_tracker (Adriel) aktif.")
    # Integration placeholder: sesuaikan dengan API modul Adriel saat dirilis
    et = expense_tracker
    et_menu: Any = getattr(et, "menu", None) if et is not None else None
    et_add: Any = getattr(et, "add_expense", None) if et is not None else None
    if callable(et_menu):
        et_menu(wallet)
    elif callable(et_add):
        ok, msg = cast(Any, et_add(
            wallet,
            amount=input_number("Nominal pengeluaran: Rp "),
            category=input("Kategori pengeluaran: ").strip(),
        ))
        print(f"  {'[OK]' if ok else '[GAGAL]'} {msg}")
        if ok:
            print("  " + finance_core.save_data(wallet, DATA_FILE))


# ==============================================================================
# MENU UTAMA
# ==============================================================================

def main():
    print("\n====================================================")
    print("  SELAMAT DATANG DI DOMPETKELUARGA  (v0.1 Lead)")
    print("  Manajemen Keuangan & Utilitas Rumah Tangga")
    print("====================================================")

    # Muat data dari persistence layer; jika kosong, buat wallet baru
    wallet = finance_core.load_data(DATA_FILE)

    # Reset status tagihan saat bulan berganti (last_reset_month)
    if finance_core.reset_monthly_bills_if_needed(wallet):
        print("\n[INFO] Bulan baru terdeteksi - semua status tagihan di-reset menjadi BELUM DIBAYAR.")

    # Smart Alert otomatis saat aplikasi dibuka (modul Darell)
    print("\n[SMART ALERT] Memeriksa tagihan jatuh tempo...")
    show_alerts(wallet)

    while True:
        print("\n=================== MENU UTAMA ===================")
        print("  1. Tambah Pemasukan")
        print("  2. Ringkasan Keuangan")
        print("  3. Kesehatan Anggaran (HIJAU/KUNING/MERAH)")
        print("  4. Kelola Tagihan Bulanan (Darell)")
        print("  5. Pencatatan Pengeluaran Harian (Adriel)")
        print("  0. Keluar")
        print("===================================================")

        choice = input_int("Pilih menu (0-5): ", 0, 5)

        if choice == 1:
            amount = input_number("Nominal pemasukan: Rp ")
            source = input("Sumber pemasukan (mis. Gaji, THR): ").strip() or "Pemasukan"
            ok, msg = finance_core.add_income(wallet, amount, source)
            print(f"  {'[OK]' if ok else '[GAGAL]'} {msg}")
            if ok:
                print("  " + finance_core.save_data(wallet, DATA_FILE))

        elif choice == 2:
            show_balance(wallet)

        elif choice == 3:
            report = finance_core.compute_budget(wallet)
            finance_core.display_budget_report(report)

        elif choice == 4:
            menu_bills(wallet)

        elif choice == 5:
            menu_expense(wallet)

        elif choice == 0:
            finance_core.save_data(wallet, DATA_FILE)
            print("\nTerima kasih telah menggunakan DompetKeluarga. Sampai jumpa!")
            break


if __name__ == "__main__":
    main()