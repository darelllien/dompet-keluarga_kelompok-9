# ==============================================================================
# MODUL 2: TAGIHAN BULANAN & INGATAN JATUH TEMPO (SMART ALERT)
# Pembuat : Darell Damiri (Dev 2)
# File    : bills_analytics.py
# ==============================================================================

import calendar
from datetime import datetime  # Library untuk ambil tanggal hari ini dari komputer

import finance_core  # Helper DRY: parse_money / parse_day / is_due_passed / MAX_AMOUNT


def add_monthly_bill(wallet, bill_name, amount, due_day):
    """
    Fitur 1: Tambah Tagihan Bulanan Baru (Create)
    - INPUT  : bill_name (str), amount (float), due_day (int)
    - PROCESS: Validasi input & simpan dictionary ke list 'monthly_bills'
    - OUTPUT : Pesan status berhasil/gagal (str)
    """

    # VALIDASI: nama tidak boleh kosong
    name = str(bill_name or "").strip()
    if not name:
        return False, "Error: Nama tagihan tidak boleh kosong."

    # VALIDASI: nominal (tolak non-angka, inf/nan, <= 0, > MAX_AMOUNT)
    ok_money, amount = finance_core.parse_money(amount)
    if not ok_money:
        return False, "Error: Nominal harus angka valid (> 0, bukan inf/nan, maks Rp 1.000.000.000.000,00)."

    # VALIDASI: tanggal jatuh tempo (angka bulat 1 - 31)
    ok_day, due_day = finance_core.parse_day(due_day)
    if not ok_day:
        return False, "Error: Tanggal jatuh tempo harus angka bulat antara 1 - 31."

    # PERINGATAN duplikat nama (bukan error - tetap diproses)
    duplicate = next(
        (b for b in wallet["monthly_bills"]
         if str(b.get("bill_name", "")).strip().lower() == name.lower()),
        None,
    )
    warn = f" [WARNING] Nama '{name}' sudah dipakai oleh tagihan ID {duplicate['bill_id']}." if duplicate else ""

    # OPERATOR ARITMATIKA (+): ID otomatis = max(ID yang ada) + 1 (default 0)
    # Fix: pakai max()+1, bukan len()+1, agar ID tidak bentrok setelah hapus item.
    bill_id = max(
        (b["bill_id"] for b in wallet["monthly_bills"] if isinstance(b.get("bill_id"), int)),
        default=0,
    ) + 1  # Tipe Data: int

    # PROCESS & DATA STRUCTURE: Menyiapkan dictionary tagihan baru
    new_bill = {
        "bill_id": bill_id,                  # Tipe Data: int
        "bill_name": name,                   # Tipe Data: str
        "amount": amount,                    # Tipe Data: float
        "due_day": due_day,                  # Tipe Data: int
        "is_paid": False                     # Tipe Data: bool (Default: Belum Dibayar)
    }

    # PROCESS: Tambahkan data baru ke dalam list 'monthly_bills'
    wallet["monthly_bills"].append(new_bill)

    # OUTPUT: Kembalikan status True dan pesan konfirmasi
    return True, f"Tagihan bulanan '{name}' sebesar Rp {amount:,.2f} berhasil didaftarkan.{warn}"


def view_monthly_bills(wallet, search=None):
    """
    Fitur 2: Lihat Daftar Tagihan Bulanan (Read)
    - INPUT  : wallet; search (str opsional) -> filter nama (case-insensitive)
    - PROCESS: Looping, filter nama, dan cek status pembayaran
    - OUTPUT : Tabel rekap tagihan di layar
    """

    bills = wallet["monthly_bills"]
    if search:
        q = str(search).strip().lower()
        bills = [b for b in bills if q in str(b.get("bill_name", "")).lower()]

    # OPERATOR LOGIKA (not): Cek jika list (hasil filter) masih kosong
    if not bills:
        if search:
            print(f"\n[INFO] Tidak ada tagihan yang cocok dengan nama '{search}'.")
        else:
            print("\n[INFO] Belum ada daftar tagihan bulanan.")
        return False

    # OUTPUT: Cetak header tabel rekapitulasi
    print("\n------------------------------------------------------------------")
    print(f"ID  | NAMA TAGIHAN      | JATUH TEMPO | NOMINAL          | STATUS")
    print("------------------------------------------------------------------")

    # PROCESS: Perulangan (looping) untuk mengambil tiap data tagihan
    for b in bills:
        # OPERATOR RELASIONAL (==): Ubah boolean True/False jadi teks "LUNAS" / "BELUM DIBAYAR"
        status_str = "LUNAS" if b.get("is_paid") else "BELUM DIBAYAR"  # Tipe Data: str

        # OUTPUT: Cetak baris data tagihan yang rapi
        print(f"{b['bill_id']:<3} | {b['bill_name']:<17} | Tgl {b['due_day']:<7} | Rp {b['amount']:<14,.2f} | {status_str}")

    print("------------------------------------------------------------------")
    return True


def mark_bill_as_paid(wallet, bill_id):
    """
    Fitur 3: Pelunasan Tagihan (Update Status)
    - INPUT  : bill_id (int)
    - PROCESS: Ubah status 'is_paid' dari False menjadi True; catat paid_late / paid_on_day
    - OUTPUT : Pesan status pelunasan (str)
    """

    # PROCESS: Cari tagihan berdasarkan nomor ID
    for bill in wallet["monthly_bills"]:
        # OPERATOR RELASIONAL (==): Mencocokkan ID tagihan
        if bill.get("bill_id") == bill_id:
            # OPERATOR LOGIKA: Cek apakah sudah lunas sebelumnya
            if bill.get("is_paid"):
                return False, f"Tagihan '{bill['bill_name']}' sudah berstatus LUNAS sebelumnya."

            # PROCESS: Catat metadata pelunasan (telat / tepat di hari jatuh tempo)
            bill["paid_on_day"] = bill["due_day"] == datetime.now().day
            bill["paid_late"] = finance_core.is_due_passed(bill.get("due_day"))

            # PROCESS: Ubah nilai variabel boolean status menjadi True (Lunas)
            bill["is_paid"] = True

            # OUTPUT: Pesan konfirmasi lunas (+ notifikasi telat)
            note = " (TELAT: lewat jatuh tempo bulan ini)" if bill["paid_late"] else ""
            return True, f"Tagihan '{bill['bill_name']}' sebesar Rp {bill['amount']:,.2f} berhasil DILUNASI!{note}"

    return False, f"Error: Tagihan dengan ID {bill_id} tidak ditemukan."


def update_monthly_bill(wallet, bill_id, new_name, new_amount, new_due_day):
    """
    Fitur 4: Edit/Perbarui Data Tagihan (Update Data)
    - INPUT  : bill_id (int), new_name (str), new_amount (float), new_due_day (int)
    - PROCESS: Overwrite data lama dengan data baru setelah validasi
    - OUTPUT : Pesan konfirmasi update (str)
    """

    # PROCESS: Cari tagihan berdasarkan ID
    for bill in wallet["monthly_bills"]:
        if bill.get("bill_id") == bill_id:
            # VALIDASI: nama baru tidak boleh kosong
            name = str(new_name or "").strip()
            if not name:
                return False, "Error: Nama tagihan baru tidak boleh kosong."

            # VALIDASI: nominal & tanggal baru
            ok_money, new_amount = finance_core.parse_money(new_amount)
            ok_day, new_due_day = finance_core.parse_day(new_due_day)
            if not ok_money or not ok_day:
                return False, "Error: Nominal & tanggal jatuh tempo baru tidak valid."

            # PROCESS: Timpa variabel lama dengan data baru
            bill["bill_name"] = name  # Tipe Data: str
            bill["amount"] = new_amount  # Tipe Data: float
            bill["due_day"] = new_due_day  # Tipe Data: int

            # OUTPUT: Pesan berhasil edit
            return True, f"Tagihan ID {bill_id} ({name}) berhasil diperbarui!"

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
        if bill.get("bill_id") == bill_id:
            # PROCESS: Hapus item dari list pakai .pop()
            removed = wallet["monthly_bills"].pop(i)
            # OUTPUT: Pesan berhasil hapus
            return True, f"Tagihan '{removed['bill_name']}' (ID {bill_id}) berhasil dihapus!"

    return False, f"Error: Tagihan dengan ID {bill_id} tidak ditemukan."


def check_due_date_alerts(wallet, current_day=None, current_month=None, current_year=None):
    """
    Fitur 6: Engine Smart Alert / Ingatan Jatuh Tempo (Core Calculation)
    - INPUT  : current_day (int) -> Tanggal simulasi/hari ini (opsional)
              current_month, current_year (int) -> konteks kalender (opsional)
    - PROCESS: Hitung sisa hari dengan logika kalender BENAR:
              - current_day <= due_day  -> jatuh tempo hari ini / bulan ini
              - current_day >  due_day  -> SUDAH LEWAT JATUH TEMPO (EXPIRED)
    - OUTPUT : List berisi pesan peringatan [WARNING MERAH]
    """

    # PROCESS: Tanggal konteks hari ini (bisa disimulasikan lewat parameter)
    now = datetime.now()
    if current_day is None:
        current_day = now.day  # Tipe Data: int
    if current_month is None:
        current_month = now.month
    if current_year is None:
        current_year = now.year

    # Jumlah hari di bulan berjalan -> dipakai hitungan lintas bulan
    days_in_month = calendar.monthrange(current_year, current_month)[1]

    alerts = []  # Tipe Data: list (Menampung string pesan peringatan)

    # PROCESS: Cek satu per satu tagihan yang BELUM DIBAYAR
    for bill in wallet["monthly_bills"]:
        # OPERATOR LOGIKA (not): Hanya periksa jika status 'is_paid' == False
        if not bill.get("is_paid"):
            due = bill.get("due_day")
            if not isinstance(due, int):
                continue

            # P4: clamp jatuh tempo ke hari terakhir bulan (due 31 di bulan 30 hari -> tgl 30)
            due = min(due, days_in_month)

            if current_day <= due:
                # ==============================================================
                # JATUH TEMPO BULAN INI:
                # OPERATOR ARITMATIKA (-): sisa_hari = tanggal_jatuh_tempo - tanggal_hari_ini
                # ==============================================================
                days_left = due - current_day  # Tipe Data: int

                # OPERATOR RELASIONAL (<=, >=) & LOGIKA (and): H-3 sampai Hari-H
                if 0 <= days_left <= 3:
                    alerts.append(
                        f"!!! [WARNING MERAH] Tagihan '{bill['bill_name']}' Rp {bill['amount']:,.2f} "
                        f"jatuh tempo dalam {days_left} hari (Tanggal {due}) !!!"
                    )
            else:
                # ==============================================================
                # SUDAH LEWAT JATUH TEMPO (EXPIRED):
                # OPERATOR ARITMATIKA (-): days_overdue = hari_ini - tanggal_jatuh_tempo
                # ==============================================================
                days_overdue = current_day - due  # Tipe Data: int

                alerts.append(
                    f"!!! [EXPIRED MERAH] Tagihan '{bill['bill_name']}' "
                    f"SUDAH LEWAT JATUH TEMPO ({days_overdue} hari yang lalu) !!!"
                )

    # OUTPUT: Kembalikan list kumpulan peringatan
    return alerts