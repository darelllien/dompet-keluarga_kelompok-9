# ==============================================================================
# MODUL 3: PENCATATAN PENGELUARAN HARIAN (CRUD)  (versi perbaikan audit)
# Pembuat : Adriel Massimo Rafinaldi (Dev 1)
# File    : expense_tracker.py
# Perbaikan:
#   - Nama item & kategori di-strip dan divalidasi (add DAN update)
#   - Tanggal divalidasi (YYYY-MM-DD) dan dinormalkan ke "Hari, YYYY-MM-DD"
#     berbahasa Indonesia, sehingga selalu terbaca filter & rekap
#   - view tahan terhadap field yang hilang dan memotong teks panjang
#   - Mode standalone memakai load/save data.json (data tidak hilang)
# Jalankan self-check: py expense_tracker.py --self-check
# ==============================================================================

import sys
from datetime import datetime

import finance_core
from finance_core import parse_money

DATA_FILE = "data.json"
MAX_TEXT = 60  # batas panjang nama item / kategori


# ==========================================
# HELPER
# ==========================================

def _clean_text(value):
    """Strip + rapikan spasi ganda. Kembalikan string (bisa kosong)."""
    return " ".join(str(value or "").split())


def normalize_date(date_str=None):
    """
    Normalisasi tanggal belanja -> (ok, nilai_atau_pesan_error).
    - Kosong/None  -> hari ini
    - Valid        -> "Hari, YYYY-MM-DD" (hari bahasa Indonesia)
    - Tidak valid  -> (False, pesan)
    Menerima "2026-10-05" maupun "Senin, 2026-10-05".
    """
    if date_str is None or not str(date_str).strip():
        return True, finance_core.format_date_id(datetime.now().date())
    d = finance_core.parse_date_any(str(date_str))
    if d is None:
        return False, "Error: Format tanggal harus YYYY-MM-DD (contoh: 2026-10-05)."
    return True, finance_core.format_date_id(d)


def _cut(value, width):
    text = str(value if value is not None else "-")
    return text if len(text) <= width else text[: width - 1] + "~"


# ==========================================
# FUNGSI CRUD
# ==========================================

def add_daily_expense(wallet, item_name, category, amount, date_str=None):
    """Mencatat transaksi belanja harian langsung ke daftar rekap."""
    item_name = _clean_text(item_name)
    category = _clean_text(category)
    if not item_name:
        return False, "Error: Nama item tidak boleh kosong."
    if not category:
        return False, "Error: Kategori tidak boleh kosong."
    if len(item_name) > MAX_TEXT or len(category) > MAX_TEXT:
        return False, f"Error: Nama item/kategori maksimal {MAX_TEXT} karakter."

    ok, amount = parse_money(amount)
    if not ok:
        return False, "Error: Nominal belanja harian harus angka valid (> 0, bukan inf/nan, maks Rp 1.000.000.000.000,00)."

    ok, date_str = normalize_date(date_str)
    if not ok:
        return False, date_str

    expenses = wallet.setdefault("daily_expenses", [])
    exp_id = max(
        (e["exp_id"] for e in expenses if isinstance(e.get("exp_id"), int)),
        default=0,
    ) + 1

    expenses.append({
        "exp_id": exp_id,
        "date": date_str,
        "category": category,
        "item_name": item_name,
        "amount": amount,
    })
    return True, f"Belanja '{item_name}' [{category}] Rp {amount:,.2f} pada {date_str} berhasil dicatat."


def view_daily_expenses(wallet):
    """Menampilkan seluruh daftar riwayat belanja harian yang pernah diinput."""
    expenses = wallet.get("daily_expenses") or []
    if not expenses:
        print("\n[INFO] Belum ada catatan belanja harian.")
        return False

    line = "-" * 86
    print("\n" + line)
    print(f"{'ID':<4}| {'TANGGAL':<19} | {'KATEGORI':<15} | {'ITEM':<20} | NOMINAL")
    print(line)
    for exp in expenses:
        amount = exp.get("amount")
        amount_txt = f"Rp {amount:,.2f}" if isinstance(amount, (int, float)) else "-"
        print(f"{_cut(exp.get('exp_id'), 3):<4}| {_cut(exp.get('date'), 19):<19} | "
              f"{_cut(exp.get('category'), 15):<15} | {_cut(exp.get('item_name'), 20):<20} | {amount_txt}")
    print(line)
    return True


def update_daily_expense(wallet, exp_id, new_item, new_cat, new_amount, new_date=None):
    """Mengedit catatan belanja harian berdasarkan ID (tanggal opsional)."""
    new_item = _clean_text(new_item)
    new_cat = _clean_text(new_cat)
    if not new_item:
        return False, "Error: Nama item baru tidak boleh kosong."
    if not new_cat:
        return False, "Error: Kategori baru tidak boleh kosong."
    if len(new_item) > MAX_TEXT or len(new_cat) > MAX_TEXT:
        return False, f"Error: Nama item/kategori maksimal {MAX_TEXT} karakter."

    ok, new_amount = parse_money(new_amount)
    if not ok:
        return False, "Error: Nominal belanja baru harus angka valid (> 0, bukan inf/nan, maks Rp 1.000.000.000.000,00)."

    date_value = None
    if new_date is not None and str(new_date).strip():
        ok, date_value = normalize_date(new_date)
        if not ok:
            return False, date_value

    for exp in wallet.get("daily_expenses", []):
        if exp.get("exp_id") == exp_id:
            exp["item_name"] = new_item
            exp["category"] = new_cat
            exp["amount"] = new_amount
            if date_value:
                exp["date"] = date_value
            return True, f"Catatan belanja ID {exp_id} berhasil diperbarui!"
    return False, f"Error: Catatan belanja ID {exp_id} tidak ditemukan."


def delete_daily_expense(wallet, exp_id):
    """Menghapus catatan belanja harian berdasarkan ID."""
    for i, exp in enumerate(wallet.get("daily_expenses", [])):
        if exp.get("exp_id") == exp_id:
            removed = wallet["daily_expenses"].pop(i)
            return True, f"Catatan belanja '{removed.get('item_name', '-')}' (ID {exp_id}) berhasil dihapus!"
    return False, f"Error: Catatan belanja ID {exp_id} tidak ditemukan."


# ==========================================
# MODE STANDALONE (CLI) - data tersimpan ke data.json
# ==========================================

def _ask_amount(prompt):
    while True:
        ok, amount = parse_money(input(prompt))
        if ok:
            return amount
        print("Error: Nominal harus angka valid (> 0, bukan inf/nan, maks Rp 1.000.000.000.000,00).")


def _ask_id(prompt):
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("Error: ID harus berupa angka bulat!")


def main_menu():
    wallet = finance_core.load_data(DATA_FILE)

    try:
        while True:
            print("\n=== EXPENSE TRACKER MENU ===")
            print("1. Tambah Belanja Harian")
            print("2. Lihat Semua Belanjaan")
            print("3. Edit Catatan Belanja")
            print("4. Hapus Catatan Belanja")
            print("5. Keluar")
            choice = input("Pilih menu (1-5): ").strip()

            if choice == "1":
                print("\n--- Tambah Belanja ---")
                item = input("Nama Item: ")
                category = input("Kategori: ")
                amount = _ask_amount("Nominal (Rp): ")
                date_str = input("Tanggal YYYY-MM-DD (opsional, Enter untuk hari ini): ")
                success, msg = add_daily_expense(wallet, item, category, amount, date_str)
                print(msg)
                if success:
                    print(finance_core.save_data(wallet, DATA_FILE))

            elif choice == "2":
                view_daily_expenses(wallet)

            elif choice == "3":
                if view_daily_expenses(wallet):
                    exp_id = _ask_id("\nMasukkan ID yang ingin diedit: ")
                    item = input("Nama Item Baru: ")
                    cat = input("Kategori Baru: ")
                    amount = _ask_amount("Nominal Baru (Rp): ")
                    new_date = input("Tanggal Baru YYYY-MM-DD (Enter = tidak diubah): ")
                    success, msg = update_daily_expense(wallet, exp_id, item, cat, amount, new_date)
                    print(msg)
                    if success:
                        print(finance_core.save_data(wallet, DATA_FILE))

            elif choice == "4":
                if view_daily_expenses(wallet):
                    exp_id = _ask_id("\nMasukkan ID yang ingin dihapus: ")
                    success, msg = delete_daily_expense(wallet, exp_id)
                    print(msg)
                    if success:
                        print(finance_core.save_data(wallet, DATA_FILE))

            elif choice == "5":
                print("\nTerima kasih telah menggunakan Expense Tracker!")
                break

            else:
                print("Pilihan tidak valid, silakan coba lagi.")
    except (KeyboardInterrupt, EOFError):
        print("\n[INFO] Keluar paksa - menyimpan data terakhir...")
        print(finance_core.save_data(wallet, DATA_FILE))


# ==========================================
# SELF-CHECK
# ==========================================

def _self_check():
    import contextlib
    import io

    w = {"daily_expenses": []}

    # Tambah: strip, normalisasi tanggal, ID otomatis
    ok, msg = add_daily_expense(w, "  Nasi   Goreng ", "  Makan ", "25.000", "2026-10-05")
    assert ok, msg
    e = w["daily_expenses"][0]
    assert e["item_name"] == "Nasi Goreng" and e["category"] == "Makan"
    assert e["amount"] == 25000.0 and e["date"] == "Senin, 2026-10-05" and e["exp_id"] == 1

    # Tanggal berformat hari-lengkap tetap diterima; tanpa tanggal -> hari ini
    ok, _ = add_daily_expense(w, "Kopi", "Minum", 15000, "Selasa, 2026-10-06")
    assert ok and w["daily_expenses"][1]["date"] == "Selasa, 2026-10-06"
    ok, _ = add_daily_expense(w, "Teh", "Minum", 5000)
    assert ok and finance_core.parse_date_any(w["daily_expenses"][2]["date"]) == datetime.now().date()

    # Validasi gagal
    assert add_daily_expense(w, "   ", "Makan", 1000)[0] is False
    assert add_daily_expense(w, "X", "", 1000)[0] is False
    assert add_daily_expense(w, "X", "Y", "abc")[0] is False
    assert add_daily_expense(w, "X", "Y", 0)[0] is False
    ok, msg = add_daily_expense(w, "X", "Y", 1000, "besok")
    assert ok is False and "YYYY-MM-DD" in msg
    assert add_daily_expense(w, "x" * (MAX_TEXT + 1), "Y", 1000)[0] is False
    assert len(w["daily_expenses"]) == 3  # tidak ada yang masuk saat gagal

    # ID tidak bentrok setelah hapus
    assert delete_daily_expense(w, 3)[0] is True
    ok, _ = add_daily_expense(w, "Roti", "Makan", 7000, "2026-10-07")
    assert ok and w["daily_expenses"][-1]["exp_id"] == 3

    # Update: validasi kosong sekarang ditolak, tanggal opsional
    assert update_daily_expense(w, 1, "  ", "Makan", 1000)[0] is False
    assert update_daily_expense(w, 1, "Nasi", "   ", 1000)[0] is False
    assert update_daily_expense(w, 1, "Nasi", "Makan", "abc")[0] is False
    ok, msg = update_daily_expense(w, 1, " Nasi Uduk ", " Sarapan ", "30.000", "2026-10-08")
    assert ok, msg
    e = w["daily_expenses"][0]
    assert e["item_name"] == "Nasi Uduk" and e["category"] == "Sarapan"
    assert e["amount"] == 30000.0 and e["date"] == "Kamis, 2026-10-08"
    assert update_daily_expense(w, 1, "Nasi", "Makan", 1000, "ngawur")[0] is False
    assert w["daily_expenses"][0]["item_name"] == "Nasi Uduk"            # tidak berubah saat gagal
    ok, _ = update_daily_expense(w, 1, "Nasi", "Makan", 1000)             # tanpa tanggal -> tanggal lama
    assert ok and w["daily_expenses"][0]["date"] == "Kamis, 2026-10-08"
    assert update_daily_expense(w, 999, "A", "B", 1)[0] is False

    # Delete
    assert delete_daily_expense(w, 999)[0] is False
    assert delete_daily_expense(w, 2)[0] is True

    # View tahan field hilang & teks panjang, dan wallet tanpa key daily_expenses
    rusak = {"daily_expenses": [{"amount": 5000}, {"exp_id": 2, "item_name": "y" * 80, "amount": 1.0}]}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert view_daily_expenses(rusak) is True
        assert view_daily_expenses({}) is False
    assert "~" in buf.getvalue()
    assert add_daily_expense({}, "A", "B", 100)[0] is True               # setdefault
    assert delete_daily_expense({}, 1)[0] is False

    print("SELF-CHECK PASS: expense_tracker (strip, validasi, tanggal, update/delete, view tahan data rusak).")
    return 0


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        raise SystemExit(_self_check())
    main_menu()