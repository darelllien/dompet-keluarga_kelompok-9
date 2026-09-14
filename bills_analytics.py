# ==============================================================================
# MODUL 2: TAGIHAN BULANAN & INGATAN JATUH TEMPO (SMART ALERT)
# Pembuat : Darell Damiri (Dev 2)
# File    : bills_analytics.py
# ==============================================================================

from datetime import datetime  # Library untuk ambil tanggal hari ini dari komputer


def add_monthly_bill(wallet, bill_name, amount, due_day):
    """
    Fitur 1: Tambah Tagihan Bulanan Baru (Create)
    - INPUT  : bill_name (str), amount (float), due_day (int)
    - PROCESS: Validasi input & simpan dictionary ke list 'monthly_bills'
    - OUTPUT : Pesan status berhasil/gagal (str)
    """
    
    # OPERATOR RELASIONAL & LOGIKA (or, not): Cek nominal > 0 & tanggal di antara 1 - 31
    if float(amount) <= 0 or not (1 <= int(due_day) <= 31):
        return False, "Error: Nominal harus > 0 dan tanggal jatuh tempo harus antara 1 - 31."
        
    # OPERATOR ARITMATIKA (+): Bikin ID tagihan otomatis dari jumlah item + 1
    bill_id = len(wallet["monthly_bills"]) + 1  # Tipe Data: int
    
    # PROCESS & DATA STRUCTURE: Menyiapkan dictionary tagihan baru
    new_bill = {
        "bill_id": bill_id,                  # Tipe Data: int
        "bill_name": str(bill_name).strip(), # Tipe Data: str
        "amount": float(amount),             # Tipe Data: float
        "due_day": int(due_day),             # Tipe Data: int
        "is_paid": False                     # Tipe Data: bool (Default: Belum Dibayar)
    }
    
    # PROCESS: Tambahkan data baru ke dalam list 'monthly_bills'
    wallet["monthly_bills"].append(new_bill)
    
    # OUTPUT: Kembalikan status True dan pesan konfirmasi
    return True, f"Tagihan bulanan '{bill_name}' sebesar Rp {amount:,.2f} berhasil didaftarkan."


def view_monthly_bills(wallet):
    """
    Fitur 2: Lihat Daftar Tagihan Bulanan (Read)
    - INPUT  : Data 'wallet' yang berisi list 'monthly_bills'
    - PROCESS: Looping dan cek status pembayaran
    - OUTPUT : Tabel rekap tagihan di layar
    """
    
    # OPERATOR LOGIKA (not): Cek jika list tagihan masih kosong
    if not wallet["monthly_bills"]:
        print("\n[INFO] Belum ada daftar tagihan bulanan.")
        return False
        
    # OUTPUT: Cetak header tabel rekapitulasi
    print("\n------------------------------------------------------------------")
    print(f"ID  | NAMA TAGIHAN      | JATUH TEMPO | NOMINAL          | STATUS")
    print("------------------------------------------------------------------")
    
    # PROCESS: Perulangan (looping) untuk mengambil tiap data tagihan
    for b in wallet["monthly_bills"]:
        # OPERATOR RELASIONAL (==): Ubah boolean True/False jadi teks "LUNAS" / "BELUM DIBAYAR"
        status_str = "LUNAS" if b["is_paid"] == True else "BELUM DIBAYAR"  # Tipe Data: str
        
        # OUTPUT: Cetak baris data tagihan yang rapi
        print(f"{b['bill_id']:<3} | {b['bill_name']:<17} | Tgl {b['due_day']:<7} | Rp {b['amount']:<14,.2f} | {status_str}")
        
    print("------------------------------------------------------------------")
    return True


def mark_bill_as_paid(wallet, bill_id):
    """
    Fitur 3: Pelunasan Tagihan (Update Status)
    - INPUT  : bill_id (int)
    - PROCESS: Ubah status 'is_paid' dari False menjadi True
    - OUTPUT : Pesan status pelunasan (str)
    """
    
    # PROCESS: Cari tagihan berdasarkan nomor ID
    for bill in wallet["monthly_bills"]:
        # OPERATOR RELASIONAL (==): Mencocokkan ID tagihan
        if bill["bill_id"] == bill_id:
            # OPERATOR LOGIKA: Cek apakah sudah lunas sebelumnya
            if bill["is_paid"]:
                return False, f"Tagihan '{bill['bill_name']}' sudah berstatus LUNAS sebelumnya."
                
            # PROCESS: Ubah nilai variabel boolean status menjadi True (Lunas)
            bill["is_paid"] = True
            
            # OUTPUT: Pesan konfirmasi lunas
            return True, f"Tagihan '{bill['bill_name']}' sebesar Rp {bill['amount']:,.2f} berhasil DILUNASI!"
            
    return False, f"Error: Tagihan dengan ID {bill_id} tidak ditemukan."


def update_monthly_bill(wallet, bill_id, new_name, new_amount, new_due_day):
    """
    Fitur 4: Edit/Perbarui Data Tagihan (Update Data)
    - INPUT  : bill_id (int), new_name (str), new_amount (float), new_due_day (int)
    - PROCESS: Overwrite data lama dengan data baru
    - OUTPUT : Pesan konfirmasi update (str)
    """
    
    # PROCESS: Cari tagihan berdasarkan ID
    for bill in wallet["monthly_bills"]:
        if bill["bill_id"] == bill_id:
            # OPERATOR RELASIONAL & LOGIKA: Validasi input baru
            if float(new_amount) <= 0 or not (1 <= int(new_due_day) <= 31):
                return False, "Error: Nominal & tanggal jatuh tempo baru tidak valid."
                
            # PROCESS: Timpa variabel lama dengan data baru
            bill["bill_name"] = str(new_name).strip()  # Tipe Data: str
            bill["amount"] = float(new_amount)         # Tipe Data: float
            bill["due_day"] = int(new_due_day)         # Tipe Data: int
            
            # OUTPUT: Pesan berhasil edit
            return True, f"Tagihan ID {bill_id} ({new_name}) berhasil diperbarui!"
            
    return False, f"Error: Tagihan dengan ID {bill_id} tidak ditemukan."


def delete_monthly_bill(wallet, bill_id):
    """
    Fitur 5: Hapus Tagihan (Delete)
    - INPUT  : bill_id (int)
    - PROCESS: Hapus item dari list 'monthly_bills'
    - OUTPUT : Pesan konfirmasi terhapus (str)
    """
    
    # PROCESS: Loop indeks dan item tagihan
    for i, bill in enumerate(wallet["monthly_bills"]):
        if bill["bill_id"] == bill_id:
            # PROCESS: Hapus item dari list pakai .pop()
            removed = wallet["monthly_bills"].pop(i)
            # OUTPUT: Pesan berhasil hapus
            return True, f"Tagihan '{removed['bill_name']}' (ID {bill_id}) berhasil dihapus!"
            
    return False, f"Error: Tagihan dengan ID {bill_id} tidak ditemukan."


def check_due_date_alerts(wallet, current_day=None):
    """
    Fitur 6: Engine Smart Alert / Ingatan Jatuh Tempo (Core Calculation)
    - INPUT  : current_day (int) -> Tanggal simulasi/hari ini
    - PROCESS: Hitung sisa hari (days_left = due_day - current_day)
    - OUTPUT : List berisi pesan peringatan [WARNING MERAH] / [EXPIRED MERAH]
    """
    
    # PROCESS: Ambil tanggal hari ini dari komputer jika tidak diisi manual
    if current_day is None:
        current_day = datetime.now().day  # Tipe Data: int
        
    alerts = []  # Tipe Data: list (Menampung string pesan peringatan)
    
    # PROCESS: Cek satu per satu tagihan yang BELUM DIBAYAR
    for bill in wallet["monthly_bills"]:
        # OPERATOR LOGIKA (not): Hanya periksa jika status 'is_paid' == False
        if not bill["is_paid"]:
            
            # ==================================================================
            # KALKULASI UTAMA MODUL DEV 2 (BASIC CALCULATION):
            # OPERATOR ARITMATIKA (-): Hitung selisih hari menuju jatuh tempo
            # Formula: sisa_hari = tanggal_jatuh_tempo - tanggal_hari_ini
            # ==================================================================
            days_left = bill["due_day"] - current_day  # Tipe Data: int
            
            # OPERATOR RELASIONAL (<=, >=) & LOGIKA (and): Peringatan H-3 sampai Hari-H (0 <= days_left <= 3)
            if 0 <= days_left <= 3:
                alerts.append(
                    f"!!! [WARNING MERAH] Tagihan '{bill['bill_name']}' Rp {bill['amount']:,.2f} "
                    f"jatuh tempo dalam {days_left} hari (Tanggal {bill['due_day']}) !!!"
                )
            # OPERATOR RELASIONAL (<): Jika tanggal sudah kelewat (minus)
            elif days_left < 0:
                # OPERATOR ARITMATIKA (abs()): Mengubah angka minus jadi positif untuk hari keterlambatan
                alerts.append(
                    f"!!! [EXPIRED MERAH] Tagihan '{bill['bill_name']}' SUDAH LEWAT JATUH TEMPO "
                    f"({abs(days_left)} hari yang lalu) !!!"
                )
                
    # OUTPUT: Kembalikan list kumpulan peringatan
    return alerts