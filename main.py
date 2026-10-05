# ==============================================================================
# MAIN APPLICATION LOOP - DOMPETKELUARGA (ENTRY POINT)  (versi patch audit)
# Pembuat : Adzril Adzim Hendrynov (Project Lead)
# File    : main.py
# Deskripsi:
# - Entry point aplikasi CLI interaktif (menu utama berbahasa Indonesia)
# - Mengintegrasikan seluruh modul:
#   * finance_core.py       (Lead : pemasukan, saldo, kesehatan anggaran)
#   * bills_analytics.py    (Darell: tagihan bulanan & smart alert)
#   * expense_tracker.py    (Adriel: pencatatan harian - via try-import)
#   * transaction_filter.py (Filter hari/minggu/bulan - via try-import)
# ==============================================================================

import sys
from datetime import datetime
from typing import Any

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

# Modul Adriel: expense_tracker.py (try-import agar aplikasi tetap jalan tanpa modul ini)
expense_tracker: Any = None
HAS_EXPENSE_TRACKER = False
try:
    import expense_tracker as _et
    if callable(getattr(_et, "add_daily_expense", None)):
        expense_tracker = _et
        HAS_EXPENSE_TRACKER = True
except ImportError:
    pass

# Modul filter transaksi (hari ini / minggu ini / bulan ini)
transaction_filter: Any = None
HAS_FILTER = False
try:
    import transaction_filter as _tf
    if callable(getattr(_tf, "filter_transaksi", None)):
        transaction_filter = _tf
        HAS_FILTER = True
except ImportError:
    pass

DATA_FILE = "data.json"


# ==============================================================================
# FUNGSI BANTU INPUT
# ==============================================================================

def input_number(prompt):
    """Ambil input nominal valid (mendukung 'Rp 5.000.000'); tolak non-angka, inf/nan, <= 0, > MAX."""
    while True:
        raw = input(prompt).strip()
        ok, value = finance_core.parse_money(raw)
        if ok:
            return value
        print("  [ERROR] Masukkan angka valid (bilangan > 0, maks Rp 1.000.000.000.000).")


def input_number_optional(prompt, default):
    """Seperti input_number, tetapi Enter (kosong) mengembalikan `default`."""
    while True:
        raw = input(prompt).strip()
        if not raw:
            return default
        ok, value = finance_core.parse_money(raw)
        if ok:
            return value
        print("  [ERROR] Masukkan angka valid, atau tekan Enter untuk tidak mengubah.")


def input_text_optional(prompt, default):
    """Enter (kosong) -> `default`."""
    raw = input(prompt).strip()
    return raw if raw else default


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


def input_yes_no(prompt, default=True):
    """Pertanyaan ya/tidak. Enter = default."""
    hint = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} ({hint}): ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "ya", "yes"):
            return True
        if raw in ("n", "t", "tidak", "no"):
            return False
        print("  [ERROR] Jawab dengan y atau n.")


def input_date_optional(prompt):
    """Tanggal opsional (YYYY-MM-DD atau DD-MM-YYYY). Enter -> None (= hari ini)."""
    while True:
        raw = input(prompt).strip()
        if not raw:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        print("  [ERROR] Format tanggal tidak dikenali. Contoh: 2026-10-05 atau 05-10-2026.")


def persist(wallet):
    """Simpan wallet dan tampilkan hasilnya."""
    print(" " + finance_core.save_data(wallet, DATA_FILE))


def result(ok, msg):
    print(f" {'[OK]' if ok else '[GAGAL]'} {msg}")


# ==============================================================================
# SMART ALERT
# ==============================================================================

def show_alerts(wallet):
    """Smart Alert H-3 (modul Darell) + alert siklus bulan depan (finance_core)."""
    alerts = list(bills_analytics.check_due_date_alerts(wallet))
    alerts += finance_core.check_next_cycle_alerts(wallet)
    if not alerts:
        print("\n[INFO] Tidak ada tagihan yang perlu diingatkan. Semua aman.")
        return
    print("\n============= SMART ALERT JATUH TEMPO =============")
    for alert in alerts:
        print(" " + alert)
    print("====================================================")


# ==============================================================================
# SUBMENU PEMASUKAN
# ==============================================================================

def add_income_flow(wallet):
    """Tambah pemasukan; nominal & sumber di-prefill dari profil."""
    profile = wallet.get("profile") or {}
    nama = (profile.get("nama") or "").strip()
    default_amount = float(profile.get("pemasukan_bulanan") or 0.0)
    if default_amount > 0:
        amount = input_number_optional(
            f"Nominal pemasukan (Enter = {default_amount:,.0f}): Rp ", default_amount)
    else:
        amount = input_number("Nominal pemasukan: Rp ")
    default_source = f"Gaji bulanan {nama}".strip() if nama else "Gaji bulanan"
    source = input(f"Sumber pemasukan (Enter = {default_source}): ").strip() or default_source
    ok, msg = finance_core.add_income(wallet, amount, source)
    result(ok, msg)
    if ok:
        persist(wallet)


def offer_monthly_income(wallet):
    """Bila belum ada pemasukan bulan ini dan profil punya pemasukan bulanan -> tawarkan pencatatan."""
    pb = float((wallet.get("profile") or {}).get("pemasukan_bulanan") or 0.0)
    if pb <= 0 or finance_core.has_income_this_month(wallet):
        return
    print(f"\n[INFO] Belum ada pemasukan tercatat bulan ini ({finance_core.month_key()}).")
    if input_yes_no(f"Catat pemasukan bulanan Rp {pb:,.0f} sekarang?", True):
        ok, msg = finance_core.add_income(wallet, pb, "")
        result(ok, msg)
        if ok:
            persist(wallet)


def menu_income(wallet):
    """Submenu pemasukan: tambah, lihat riwayat, edit, hapus."""
    while True:
        print("\n============== MENU PEMASUKAN ==============")
        print(" 1. Tambah Pemasukan")
        print(" 2. Lihat Riwayat Pemasukan")
        print(" 3. Edit Pemasukan")
        print(" 4. Hapus Pemasukan")
        print(" 0. Kembali ke Menu Utama")
        print("============================================")
        choice = input_int("Pilih menu (0-4): ", 0, 4)

        if choice == 1:
            add_income_flow(wallet)
        elif choice == 2:
            finance_core.view_incomes(wallet)
        elif choice == 3:
            if finance_core.view_incomes(wallet):
                items = finance_core.list_incomes(wallet)
                number = input_int("Nomor pemasukan yang diedit: ", 1, len(items))
                old = items[number - 1][1]
                amount = input_number_optional(
                    f"Nominal baru (Enter = {old['amount']:,.0f}): Rp ", old["amount"])
                source = input_text_optional(
                    f"Sumber baru (Enter = {old.get('source', '-')}): ", None)
                ok, msg = finance_core.update_income(wallet, number, amount, source)
                result(ok, msg)
                if ok:
                    persist(wallet)
        elif choice == 4:
            if finance_core.view_incomes(wallet):
                items = finance_core.list_incomes(wallet)
                number = input_int("Nomor pemasukan yang dihapus: ", 1, len(items))
                if input_yes_no(f"Yakin hapus pemasukan nomor {number}?", False):
                    ok, msg = finance_core.delete_income(wallet, number)
                    result(ok, msg)
                    if ok:
                        persist(wallet)
                else:
                    print(" [INFO] Dibatalkan.")
        elif choice == 0:
            break


# ==============================================================================
# SUBMENU TAGIHAN BULANAN (MODUL DARELL)
# ==============================================================================

def _find_bill(wallet, bill_id):
    return next((b for b in wallet["monthly_bills"] if b.get("bill_id") == bill_id), None)


def menu_bills(wallet):
    """Submenu CRUD + Smart Alert tagihan bulanan (delegasi ke bills_analytics)."""
    while True:
        print("\n============= MENU TAGIHAN BULANAN =============")
        print(" 1. Lihat Daftar Tagihan")
        print(" 2. Tambah Tagihan Baru")
        print(" 3. Lunasikan Tagihan")
        print(" 4. Batal Pelunasan Tagihan (Undo)")
        print(" 5. Edit Tagihan")
        print(" 6. Hapus Tagihan")
        print(" 7. Cek Smart Alert (Jatuh Tempo)")
        print(" 0. Kembali ke Menu Utama")
        print("================================================")
        choice = input_int("Pilih menu (0-7): ", 0, 7)

        if choice == 1:
            q = input("Cari nama tagihan (Enter = semua): ").strip()
            bills_analytics.view_monthly_bills(wallet, q or None)

        elif choice == 2:
            name = input("Nama tagihan: ").strip()
            amount = input_number("Nominal tagihan: Rp ")
            due_day = input_int("Tanggal jatuh tempo (1-31): ", 1, 31)
            ok, msg = bills_analytics.add_monthly_bill(wallet, name, amount, due_day)
            result(ok, msg)
            if ok:
                persist(wallet)

        elif choice == 3:
            if bills_analytics.view_monthly_bills(wallet):
                bill_id = input_int("ID tagihan yang dilunasi: ", 1)
                ok, msg = bills_analytics.mark_bill_as_paid(wallet, bill_id)
                result(ok, msg)
                if ok:
                    # Catat ke ledger permanen -> saldo kas stabil saat reset bulan / hapus
                    finance_core.sync_bill_payments(wallet)
                    persist(wallet)

        elif choice == 4:
            if bills_analytics.view_monthly_bills(wallet):
                bill_id = input_int("ID tagihan yang dibatalkan pelunasannya: ", 1)
                if input_yes_no(f"Yakin batalkan status lunas tagihan ID {bill_id}?", False):
                    ok, msg = bills_analytics.unmark_bill_as_paid(wallet, bill_id)
                    result(ok, msg)
                    if ok:
                        persist(wallet)
                else:
                    print(" [INFO] Dibatalkan.")

        elif choice == 5:
            if bills_analytics.view_monthly_bills(wallet):
                bill_id = input_int("ID tagihan yang diedit: ", 1)
                bill = _find_bill(wallet, bill_id)
                if bill is None:
                    result(False, f"Error: Tagihan dengan ID {bill_id} tidak ditemukan.")
                    continue
                name = input_text_optional(f"Nama tagihan baru (Enter = {bill['bill_name']}): ", bill["bill_name"])
                amount = input_number_optional(
                    f"Nominal baru (Enter = {bill['amount']:,.0f}): Rp ", bill["amount"])
                due_day = bill["due_day"]
                raw_day = input(f"Tanggal jatuh tempo baru 1-31 (Enter = {bill['due_day']}): ").strip()
                if raw_day:
                    ok_day, parsed_day = finance_core.parse_day(raw_day)
                    if not ok_day:
                        result(False, "Error: Tanggal jatuh tempo harus angka bulat antara 1 - 31.")
                        continue
                    due_day = parsed_day
                dup = next((b for b in wallet["monthly_bills"]
                            if b.get("bill_id") != bill_id
                            and str(b.get("bill_name", "")).strip().lower() == name.strip().lower()), None)
                finance_core.sync_bill_payments(wallet)  # amankan catatan pelunasan lama dulu
                ok, msg = bills_analytics.update_monthly_bill(wallet, bill_id, name, amount, due_day)
                result(ok, msg)
                if ok:
                    if dup:
                        print(f" [WARNING] Nama '{name}' juga dipakai tagihan ID {dup['bill_id']}.")
                    persist(wallet)

        elif choice == 6:
            if bills_analytics.view_monthly_bills(wallet):
                bill_id = input_int("ID tagihan yang dihapus: ", 1)
                if _find_bill(wallet, bill_id) is None:
                    result(False, f"Error: Tagihan dengan ID {bill_id} tidak ditemukan.")
                    continue
                if not input_yes_no(f"Yakin hapus tagihan ID {bill_id}?", False):
                    print(" [INFO] Dibatalkan.")
                    continue
                finance_core.sync_bill_payments(wallet)  # pelunasan tetap tercatat di ledger
                ok, msg = bills_analytics.delete_monthly_bill(wallet, bill_id)
                result(ok, msg)
                if ok:
                    persist(wallet)

        elif choice == 7:
            show_alerts(wallet)

        elif choice == 0:
            break


# ==============================================================================
# RINGKASAN KEUANGAN
# ==============================================================================

def show_balance(wallet):
    """Tampilkan ringkasan saldo (engine Lead)."""
    b = finance_core.compute_balance(wallet)
    print("\n=============== RINGKASAN KEUANGAN ===============")
    print(f" Total Pemasukan          : Rp {b['total_pemasukan']:,.2f}")
    print(f" Total Pengeluaran Harian : Rp {b['total_pengeluaran']:,.2f}")
    print(f" Tagihan Dibayar (semua)  : Rp {b['total_tagihan_dibayar']:,.2f}")
    print(f" Komitmen Tagihan Bulan Ini: Rp {b['komitmen_tagihan_total']:,.2f}")
    print(f"  - Sudah Lunas           : Rp {b['komitmen_lunas']:,.2f}")
    print(f"  - Belum Lunas           : Rp {b['komitmen_belum_lunas']:,.2f}")
    print(f"     * Terlambat          : Rp {b['komitmen_terlambat']:,.2f}")
    print(f"     * Menunggu           : Rp {b['komitmen_menunggu']:,.2f}")
    print("--------------------------------------------------")
    print(f" Saldo Kas                : Rp {b['saldo_kas']:,.2f}")
    print(f" Saldo Setelah Komitmen   : Rp {b['saldo_setelah_komitmen']:,.2f}")
    print("===================================================")


# ==============================================================================
# SUBMENU PENGELUARAN HARIAN (MODUL ADRIEL)
# ==============================================================================

def _find_expense(wallet, exp_id):
    return next((e for e in wallet["daily_expenses"] if e.get("exp_id") == exp_id), None)


def show_expense_recap(wallet):
    """Rekap pengeluaran harian per kategori dan per tanggal."""
    exps = wallet.get("daily_expenses", [])
    if not exps:
        print("\n[INFO] Belum ada catatan belanja harian.")
        return
    per_cat, per_day = {}, {}
    for e in exps:
        cat = str(e.get("category", "")).strip().title() or "Lainnya"
        per_cat[cat] = per_cat.get(cat, 0.0) + e["amount"]
        d = finance_core.parse_date_any(e.get("date"))
        key = d.strftime("%Y-%m-%d") if d else "Tanpa tanggal"
        per_day[key] = per_day.get(key, 0.0) + e["amount"]
    total = sum(per_cat.values())
    print("\n=========== REKAP PENGELUARAN HARIAN ===========")
    print(" Per Kategori:")
    for cat, amt in sorted(per_cat.items(), key=lambda kv: -kv[1]):
        print(f"  {cat:<20} Rp {amt:>16,.2f}  ({amt / total * 100:5.1f}%)")
    print(" Per Tanggal:")
    for key in sorted(per_day):
        print(f"  {key:<20} Rp {per_day[key]:>16,.2f}")
    print("-------------------------------------------------")
    print(f"  {'TOTAL':<20} Rp {total:>16,.2f}")
    print("=================================================")


def menu_expense(wallet):
    """Pencatatan pengeluaran harian -> CRUD modul Adriel (expense_tracker)."""
    if not HAS_EXPENSE_TRACKER:
        print("\n[INFO] Modul pencatatan pengeluaran harian BELUM TERSEDIA.")
        print("       expense_tracker.py tidak ditemukan - fitur ini menyusul.")
        return

    while True:
        print("\n=========== PENGELUARAN HARIAN ===========")
        print(" 1. Tambah Belanja Harian")
        print(" 2. Lihat Daftar Belanja")
        print(" 3. Edit Catatan Belanja")
        print(" 4. Hapus Catatan Belanja")
        print(" 5. Rekap per Kategori & Tanggal")
        print(" 0. Kembali ke Menu Utama")
        print("==========================================")
        choice = input_int("Pilih menu (0-5): ", 0, 5)

        if choice == 1:
            item = input("Nama item: ").strip()
            category = input("Kategori: ").strip()
            amount = input_number("Nominal belanja: Rp ")
            d = input_date_optional("Tanggal belanja (Enter = hari ini, format YYYY-MM-DD): ")
            date_str = finance_core.format_date_id(d or datetime.now().date())
            ok, msg = expense_tracker.add_daily_expense(wallet, item, category, amount, date_str)
            result(ok, msg)
            if ok:
                persist(wallet)

        elif choice == 2:
            expense_tracker.view_daily_expenses(wallet)

        elif choice == 3:
            if expense_tracker.view_daily_expenses(wallet):
                exp_id = input_int("ID belanja yang diedit: ", 1)
                exp = _find_expense(wallet, exp_id)
                if exp is None:
                    result(False, f"Error: Catatan belanja ID {exp_id} tidak ditemukan.")
                    continue
                item = input_text_optional(f"Nama item baru (Enter = {exp['item_name']}): ", exp["item_name"])
                category = input_text_optional(f"Kategori baru (Enter = {exp['category']}): ", exp["category"])
                amount = input_number_optional(
                    f"Nominal baru (Enter = {exp['amount']:,.0f}): Rp ", exp["amount"])
                new_date = input_date_optional(
                    f"Tanggal baru YYYY-MM-DD (Enter = {exp['date']}): ")
                ok, msg = expense_tracker.update_daily_expense(wallet, exp_id, item, category, amount)
                result(ok, msg)
                if ok:
                    if new_date:
                        exp["date"] = finance_core.format_date_id(new_date)
                    persist(wallet)

        elif choice == 4:
            if expense_tracker.view_daily_expenses(wallet):
                exp_id = input_int("ID belanja yang dihapus: ", 1)
                if _find_expense(wallet, exp_id) is None:
                    result(False, f"Error: Catatan belanja ID {exp_id} tidak ditemukan.")
                    continue
                if not input_yes_no(f"Yakin hapus catatan belanja ID {exp_id}?", False):
                    print(" [INFO] Dibatalkan.")
                    continue
                ok, msg = expense_tracker.delete_daily_expense(wallet, exp_id)
                result(ok, msg)
                if ok:
                    persist(wallet)

        elif choice == 5:
            show_expense_recap(wallet)

        elif choice == 0:
            break


# ==============================================================================
# FILTER TRANSAKSI
# ==============================================================================

def menu_filter(wallet):
    """Filter belanja harian: hari ini / minggu ini / bulan ini (transaction_filter.py)."""
    if not HAS_FILTER:
        print("\n[INFO] Modul transaction_filter.py tidak ditemukan - fitur filter belum tersedia.")
        return
    try:
        transaction_filter.filter_transaksi(wallet)
    except NameError as exc:
        print(f"\n[ERROR] transaction_filter.py belum lengkap ({exc}).")
        print("        Tambahkan di baris paling atas file itu:  from datetime import datetime, timedelta")


# ==============================================================================
# MENU UTAMA
# ==============================================================================

def main():
    wallet = None
    try:
        print("\n====================================================")
        print(" SELAMAT DATANG DI DOMPETKELUARGA (v1.0)")
        print(" Manajemen Keuangan & Utilitas Rumah Tangga")
        print("====================================================")

        # Muat data (JSON rusak otomatis dibackup ke data.json.bak)
        wallet = finance_core.load_data(DATA_FILE)

        # Onboarding SEKALI: bila profile.nama kosong, isi nama + pemasukan bulanan
        if not ((wallet.get("profile") or {}).get("nama") or "").strip():
            print("\n[ONBOARDING] Selamat datang! Lengkapi profil akun dulu ya.")
            while True:
                nama = input("Nama Anda: ").strip()
                if nama:
                    break
                print("  [ERROR] Nama tidak boleh kosong.")
            pemasukan = input_number("Pemasukan bulanan Anda: Rp ")
            wallet["profile"]["nama"] = nama
            wallet["profile"]["pemasukan_bulanan"] = pemasukan
            print(f" [OK] Profil tersimpan untuk {nama}.")
            persist(wallet)

        # Arsipkan pelunasan lama ke ledger, lalu reset status tagihan bila bulan berganti
        finance_core.sync_bill_payments(wallet, month_override=wallet.get("last_reset_month"))
        if finance_core.reset_monthly_bills_if_needed(wallet):
            print("\n[INFO] Bulan baru terdeteksi - semua status tagihan di-reset menjadi BELUM DIBAYAR.")
        finance_core.save_data(wallet, DATA_FILE)  # simpan diam-diam (ledger/reset)

        # Tawarkan pencatatan pemasukan bulanan (onboarding / awal bulan baru)
        offer_monthly_income(wallet)

        # Smart Alert otomatis saat aplikasi dibuka
        print("\n[SMART ALERT] Memeriksa tagihan jatuh tempo...")
        show_alerts(wallet)

        while True:
            # Pengecekan runtime: jika aplikasi dibiarkan terbuka melewati pergantian bulan, reset otomatis berjalan
            if finance_core.reset_monthly_bills_if_needed(wallet):
                print("\n[INFO] Pergantian bulan terdeteksi - status tagihan bulanan otomatis di-reset.")
                persist(wallet)

            nama = (wallet.get("profile") or {}).get("nama", "").strip()
            if nama:
                print(f"\n======== MENU UTAMA - Halo, {nama}! =========")
            else:
                print("\n=================== MENU UTAMA ===================")
            print(" 1. Kelola Pemasukan")
            print(" 2. Ringkasan Keuangan")
            print(" 3. Kesehatan Anggaran (HIJAU/KUNING/MERAH)")
            print(" 4. Kelola Tagihan Bulanan")
            print(" 5. Pencatatan Pengeluaran Harian")
            print(" 6. Filter Transaksi (Hari/Minggu/Bulan)")
            print(" 0. Keluar")
            print("===================================================")
            choice = input_int("Pilih menu (0-6): ", 0, 6)

            if choice == 1:
                menu_income(wallet)
            elif choice == 2:
                show_balance(wallet)
            elif choice == 3:
                report = finance_core.compute_budget(wallet)
                finance_core.display_budget_report(report, nama)
            elif choice == 4:
                menu_bills(wallet)
            elif choice == 5:
                menu_expense(wallet)
            elif choice == 6:
                menu_filter(wallet)
            elif choice == 0:
                finance_core.sync_bill_payments(wallet)
                persist(wallet)
                print("\nTerima kasih telah menggunakan DompetKeluarga. Sampai jumpa!")
                break

    except (KeyboardInterrupt, EOFError):
        print("\n[INFO] Keluar paksa (Ctrl+C / EOF) - menyimpan data terakhir...")
        if wallet is not None:
            finance_core.sync_bill_payments(wallet)
            print(" " + finance_core.save_data(wallet, DATA_FILE))
        print("\nTerima kasih telah menggunakan DompetKeluarga. Sampai jumpa!")


# ==============================================================================
# SELF-CHECK
# ==============================================================================

def _self_check():
    """Self-check: Smart Alert (tanggal simulasi), profil, parsing nominal,
    alert lintas bulan, dan stabilitas saldo kas terhadap ledger tagihan."""
    wallet = {
        "monthly_bills": [
            {"bill_id": 1, "bill_name": "Listrik", "amount": 500000.0, "due_day": 10, "is_paid": False},
            {"bill_id": 2, "bill_name": "Wifi", "amount": 300000.0, "due_day": 3, "is_paid": False},
            {"bill_id": 3, "bill_name": "Lunas", "amount": 100000.0, "due_day": 15, "is_paid": True},
        ]
    }

    # 1) Tanggal 8: Listrik H-2 -> warning
    a1 = bills_analytics.check_due_date_alerts(wallet, 8, 9, 2026)
    assert any("Listrik" in x and "[WARNING MERAH]" in x for x in a1), f"FAIL H-2: {a1}"

    # 2) Tanggal 10: H-0 -> warning
    a2 = bills_analytics.check_due_date_alerts(wallet, 10, 9, 2026)
    assert any("Listrik" in x and "[WARNING MERAH]" in x for x in a2), f"FAIL H-0: {a2}"

    # 3) Tanggal 15: lewat due_day -> EXPIRED; tagihan lunas tidak dialert
    a3 = bills_analytics.check_due_date_alerts(wallet, 15, 9, 2026)
    assert any("Listrik" in x and "[EXPIRED MERAH]" in x for x in a3), f"FAIL EXPIRED: {a3}"
    assert all("Lunas" not in x for x in a3), f"FAIL: tagihan lunas ikut dialert: {a3}"

    # 4) due_day 31 di bulan 30 hari di-clamp
    w4 = {"monthly_bills": [{"bill_id": 1, "bill_name": "Tgl31", "amount": 1.0, "due_day": 31, "is_paid": False}]}
    a4 = bills_analytics.check_due_date_alerts(w4, 30, 9, 2026)
    assert any("Hari-H" in x and "[WARNING MERAH]" in x for x in a4) or any("dalam 0 hari" in x for x in a4), \
        f"FAIL clamp: {a4}"

    # 5) Profil: migrasi, onboarding, prefill, parse
    old = {"income": 1000.0, "transactions": [], "daily_expenses": [], "monthly_bills": []}
    mig = finance_core.sanitize_wallet(old)
    assert mig.get("profile") == {"nama": "", "pemasukan_bulanan": 0.0}, f"FAIL migrasi: {mig.get('profile')!r}"
    assert (not ((mig.get("profile") or {}).get("nama") or "").strip()) is True
    done = {"profile": {"nama": "Budi", "pemasukan_bulanan": 5000000.0}}
    assert (not ((done.get("profile") or {}).get("nama") or "").strip()) is False
    nama_budi = (done.get("profile") or {}).get("nama", "").strip()
    assert (f"Gaji bulanan {nama_budi}".strip() if nama_budi else "Gaji bulanan") == "Gaji bulanan Budi"
    ok_pb, pb = finance_core.parse_money("7500000")
    assert ok_pb and pb == 7500000.0
    assert finance_core.parse_money("-5")[0] is False
    assert finance_core.parse_money(finance_core.MAX_AMOUNT + 1)[0] is False

    # 6) Parsing nominal format Indonesia
    assert finance_core.parse_money("Rp 5.000.000") == (True, 5000000.0)
    assert finance_core.parse_money("1.250.000,50") == (True, 1250000.5)
    assert finance_core.parse_money("abc")[0] is False

    # 7) Alert lintas bulan: lunas, jatuh tempo tgl 2, hari ini 30 -> H-2 bulan depan
    w7 = {"monthly_bills": [{"bill_id": 1, "bill_name": "Wifi", "amount": 1.0, "due_day": 2, "is_paid": True}]}
    a7 = finance_core.check_next_cycle_alerts(w7, datetime(2026, 9, 30))
    assert len(a7) == 1 and "Wifi" in a7[0], f"FAIL lintas bulan: {a7}"

    # 8) Saldo kas stabil setelah pelunasan + ganti bulan + hapus tagihan
    w8 = finance_core.init_wallet()
    w8["income"] = 1000000.0
    w8["last_reset_month"] = "2026-09"
    w8["monthly_bills"] = [{"bill_id": 1, "bill_name": "Listrik", "amount": 100000.0, "due_day": 5, "is_paid": True}]
    finance_core.sync_bill_payments(w8, now=datetime(2026, 9, 10))
    finance_core.reset_monthly_bills_if_needed(w8, datetime(2026, 10, 1))
    w8["monthly_bills"].clear()
    assert finance_core.get_totals(w8, now=datetime(2026, 10, 2))["balance_cash"] == 900000.0, "FAIL ledger"

    # 8b) Batal pelunasan (unmark_bill_as_paid)
    w8b = finance_core.init_wallet()
    w8b["income"] = 500000.0
    bills_analytics.add_monthly_bill(w8b, "Air", 50000, 10)
    bills_analytics.mark_bill_as_paid(w8b, 1)
    finance_core.sync_bill_payments(w8b)
    assert finance_core.get_totals(w8b)["balance_cash"] == 450000.0
    ok_unmark, _ = bills_analytics.unmark_bill_as_paid(w8b, 1)
    assert ok_unmark and w8b["monthly_bills"][0]["is_paid"] is False
    assert finance_core.get_totals(w8b)["balance_cash"] == 500000.0

    # 9) Helper tanggal belanja (hari Indonesia, bisa dibaca filter 10 karakter terakhir)
    s = finance_core.format_date_id(datetime(2026, 10, 5).date())
    assert s == "Senin, 2026-10-05" and finance_core.parse_date_any(s) == datetime(2026, 10, 5).date()

    print("SELF-CHECK PASS: H-2/H-0 warning, EXPIRED, lunas diabaikan, clamp tgl 31, "
          "profil, parsing Rp, alert lintas bulan, ledger saldo kas, undo lunasi, format tanggal OK.")
    return 0


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        raise SystemExit(_self_check())
    main()