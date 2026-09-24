from datetime import datetime

from finance_core import parse_money

# ==========================================
# FUNGSI DASAR (TETAP TANPA UBAHAN)
# ==========================================

def add_daily_expense(wallet, item_name, category, amount, date_str=None):
    """Mencatat transaksi belanja harian langsung ke daftar rekap."""
    if not item_name or not item_name.strip():
        return False, "Error: Nama item tidak boleh kosong."
    if not category or not category.strip():
        return False, "Error: Kategori tidak boleh kosong."
    ok, amount = parse_money(amount)
    if not ok:
        return False, "Error: Nominal belanja harian harus angka valid (> 0, bukan inf/nan, maks Rp 1.000.000.000.000,00)."
        
    if not date_str or not date_str.strip():
        date_str = datetime.now().strftime("%A, %Y-%m-%d")
        
    exp_id = max(
        (e["exp_id"] for e in wallet["daily_expenses"] if isinstance(e.get("exp_id"), int)),
        default=0,
    ) + 1
    new_expense = {
        "exp_id": exp_id,
        "date": date_str,
        "category": category,
        "item_name": item_name,
        "amount": amount
    }
    wallet["daily_expenses"].append(new_expense)
    return True, f"Belanja '{item_name}' [{category}] Rp {amount:,.2f} pada {date_str} berhasil dicatat."

def view_daily_expenses(wallet):
    """Menampilkan seluruh daftar riwayat belanja harian yang pernah diinput."""
    if not wallet["daily_expenses"]:
        print("\n[INFO] Belum ada catatan belanja harian.")
        return False
        
    print("\n----------------------------------------------------------------------")
    print(f"ID  | TANGGAL                  | KATEGORI        | ITEM            | NOMINAL")
    print("----------------------------------------------------------------------")
    for exp in wallet["daily_expenses"]:
        print(f"{exp['exp_id']:<3} | {exp['date']:<26} | {exp['category']:<15} | {exp['item_name']:<15} | Rp {exp['amount']:,.2f}")
    print("----------------------------------------------------------------------")
    return True

def update_daily_expense(wallet, exp_id, new_item, new_cat, new_amount):
    """Mengedit catatan belanja harian berdasarkan ID."""
    ok, new_amount = parse_money(new_amount)
    if not ok:
        return False, "Error: Nominal belanja baru harus angka valid (> 0, bukan inf/nan, maks Rp 1.000.000.000.000,00)."
    for exp in wallet["daily_expenses"]:
        if exp["exp_id"] == exp_id:
            exp["item_name"] = new_item
            exp["category"] = new_cat
            exp["amount"] = new_amount
            return True, f"Catatan belanja ID {exp_id} berhasil diperbarui!"
    return False, f"Error: Catatan belanja ID {exp_id} tidak ditemukan."

def delete_daily_expense(wallet, exp_id):
    """Menghapus catatan belanja harian berdasarkan ID."""
    for i, exp in enumerate(wallet["daily_expenses"]):
        if exp["exp_id"] == exp_id:
            removed = wallet["daily_expenses"].pop(i)
            return True, f"Catatan belanja '{removed['item_name']}' (ID {exp_id}) berhasil dihapus!"
    return False, f"Error: Catatan belanja ID {exp_id} tidak ditemukan."


# ==========================================
# ADD-ON: LOGIKA LOOPING & INTERAKSI (CLI)
# ==========================================

def main_menu():
    wallet = {"daily_expenses": []}
    
    # Loop utama menggunakan while loop agar menu terus berjalan hingga user keluar
    while True:
        print("\n=== EXPENSE TRACKER MENU ===")
        print("1. Tambah Belanja Harian")
        print("2. Lihat Semua Belanjaan")
        print("3. Edit Catatan Belanja")
        print("4. Hapus Catatan Belanja")
        print("5. Keluar")
        
        choice = input("Pilih menu (1-5): ").strip()
        
        # Pengkondisian if-elif-else untuk navigasi menu
        if choice == "1":
            print("\n--- Tambah Belanja ---")
            item = input("Nama Item: ")
            category = input("Kategori: ")
            
            # Input validation loop untuk nominal
            while True:
                ok, amount = parse_money(input("Nominal (Rp): "))
                if ok:
                    break
                print("Error: Nominal harus angka valid (> 0, bukan inf/nan, maks Rp 1.000.000.000.000,00).")
                    
            date_str = input("Tanggal (opsional, tekan Enter untuk hari ini): ")
            success, msg = add_daily_expense(wallet, item, category, amount, date_str)
            print(msg)
            
        elif choice == "2":
            view_daily_expenses(wallet)
            
        elif choice == "3":
            if view_daily_expenses(wallet):
                try:
                    exp_id = int(input("\nMasukkan ID yang ingin diedit: "))
                    item = input("Nama Item Baru: ")
                    cat = input("Kategori Baru: ")
                    while True:
                        ok, amount = parse_money(input("Nominal Baru (Rp): "))
                        if ok:
                            break
                        print("Error: Nominal harus angka valid (> 0, bukan inf/nan, maks Rp 1.000.000.000.000,00).")
                    success, msg = update_daily_expense(wallet, exp_id, item, cat, amount)
                    print(msg)
                except ValueError:
                    print("Error: Input ID/Nominal harus berupa angka!")
                    
        elif choice == "4":
            if view_daily_expenses(wallet):
                try:
                    exp_id = int(input("\nMasukkan ID yang ingin dihapus: "))
                    success, msg = delete_daily_expense(wallet, exp_id)
                    print(msg)
                except ValueError:
                    print("Error: Input ID harus berupa angka!")
                    
        elif choice == "5":
            print("\nTerima kasih telah menggunakan Expense Tracker!")
            break
            
        else:
            print("Pilihan tidak valid, silakan coba lagi.")

if __name__ == "__main__":
    main_menu()