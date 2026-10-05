# ==============================================================================
# MODUL 4: FILTER TRANSAKSI (HARI INI / MINGGU INI / BULAN INI)
# Pembuat : Guido Poli Lau
# File    : transaction_filter.py  (versi perbaikan audit)
# Deskripsi:
#   - Menampilkan pengeluaran harian (daily_expenses), pembayaran tagihan (bill_payments),
#     dan pemasukan (income) pada periode yang dipilih, lengkap dengan total dan selisih.
#   - Periode memakai rentang penuh: hari ini, Senin-Minggu pekan ini,
#     tanggal 1 sampai akhir bulan ini.
#   - Catatan dengan tanggal tidak terbaca tidak dibuang diam-diam: jumlahnya
#     ditampilkan sebagai peringatan.
# Jalankan self-check: py transaction_filter.py --self-check
# ==============================================================================

import calendar
import sys
from datetime import date, datetime, timedelta

import finance_core

PERIODE = {
    "1": "HARI INI",
    "2": "MINGGU INI",
    "3": "BULAN INI",
}


def period_range(kode, today=None):
    """
    Rentang tanggal (mulai, akhir, nama) untuk kode periode "1"/"2"/"3".
    Kode tidak dikenal -> None.
    """
    today = today or datetime.now().date()
    if kode == "1":
        return today, today, PERIODE["1"]
    if kode == "2":
        start = today - timedelta(days=today.weekday())      # Senin
        return start, start + timedelta(days=6), PERIODE["2"]  # s.d. Minggu
    if kode == "3":
        start = today.replace(day=1)
        last = calendar.monthrange(today.year, today.month)[1]
        return start, today.replace(day=last), PERIODE["3"]
    return None


def filter_transactions(wallet, kode, today=None):
    """
    Saring pengeluaran harian, pelunasan tagihan, & pemasukan pada periode `kode`.
    Mengembalikan dict:
      periode, mulai, akhir, pengeluaran [(date, dict)], tagihan_dibayar [(date, dict)],
      pemasukan [(date, dict)], total_belanja, total_tagihan_dibayar, total_pengeluaran,
      total_pemasukan, selisih, tanpa_tanggal (int)
    atau None bila kode tidak valid.
    """
    rng = period_range(kode, today)
    if rng is None:
        return None
    start, end, nama = rng

    pengeluaran, tagihan_dibayar, pemasukan, tanpa_tanggal = [], [], [], 0

    # 1. Pengeluaran Harian
    for e in wallet.get("daily_expenses", []):
        if not (isinstance(e, dict) and finance_core._is_num(e.get("amount"))):
            continue
        d = finance_core.parse_date_any(e.get("date"))
        if d is None:
            tanpa_tanggal += 1
        elif start <= d <= end:
            pengeluaran.append((d, e))

    # 2. Pembayaran Tagihan dari Ledger
    for p in wallet.get("bill_payments", []):
        if not (isinstance(p, dict) and finance_core._is_num(p.get("amount"))):
            continue
        d = finance_core.parse_date_any(p.get("date"))
        if d is None:
            tanpa_tanggal += 1
        elif start <= d <= end:
            tagihan_dibayar.append((d, p))

    # 3. Pemasukan
    for _, tx in finance_core.list_incomes(wallet):
        if not finance_core._is_num(tx.get("amount")):
            continue
        d = finance_core.parse_date_any(tx.get("date"))
        if d is None:
            tanpa_tanggal += 1
        elif start <= d <= end:
            pemasukan.append((d, tx))

    pengeluaran.sort(key=lambda p: (p[0], p[1].get("exp_id") or 0))
    tagihan_dibayar.sort(key=lambda p: (p[0], str(p[1].get("bill_name", ""))))
    pemasukan.sort(key=lambda p: p[0])

    total_belanja = sum(e["amount"] for _, e in pengeluaran)
    total_bill_paid = sum(p["amount"] for _, p in tagihan_dibayar)
    total_out = total_belanja + total_bill_paid
    total_in = sum(tx["amount"] for _, tx in pemasukan)

    return {
        "periode": nama,
        "mulai": start,
        "akhir": end,
        "pengeluaran": pengeluaran,
        "tagihan_dibayar": tagihan_dibayar,
        "pemasukan": pemasukan,
        "total_belanja": total_belanja,
        "total_tagihan_dibayar": total_bill_paid,
        "total_pengeluaran": total_out,
        "total_pemasukan": total_in,
        "selisih": total_in - total_out,
        "tanpa_tanggal": tanpa_tanggal,
    }


def _cut(value, width):
    text = str(value if value is not None else "-")
    return text if len(text) <= width else text[: width - 1] + "~"


def print_filter_result(res):
    """Cetak hasil filter_transactions() ke layar."""
    line = "-" * 86
    print(f"\n=== TRANSAKSI {res['periode']} ===")
    print(f"Periode: {res['mulai'].strftime('%d-%m-%Y')} sampai {res['akhir'].strftime('%d-%m-%Y')}")

    print("\n[PENGELUARAN HARIAN]")
    print(line)
    if not res["pengeluaran"]:
        print("[INFO] Tidak ada belanja harian pada periode ini.")
    else:
        print(f"{'ID':<5}{'Tanggal':<12}{'Kategori':<16}{'Item':<26}{'Nominal':>25}")
        print(line)
        for d, e in res["pengeluaran"]:
            print(f"{_cut(e.get('exp_id'), 4):<5}"
                  f"{d.strftime('%Y-%m-%d'):<12}"
                  f"{_cut(e.get('category'), 15):<16}"
                  f"{_cut(e.get('item_name'), 25):<26}"
                  f"Rp {e['amount']:>22,.2f}")
    print(line)

    print("\n[PEMBAYARAN TAGIHAN BULANAN]")
    print(line)
    if not res.get("tagihan_dibayar"):
        print("[INFO] Tidak ada pembayaran tagihan pada periode ini.")
    else:
        print(f"{'No':<5}{'Tanggal':<12}{'Bulan Siklus':<16}{'Nama Tagihan':<26}{'Nominal':>25}")
        print(line)
        for idx, (d, p) in enumerate(res["tagihan_dibayar"], 1):
            print(f"{idx:<5}"
                  f"{d.strftime('%Y-%m-%d'):<12}"
                  f"{_cut(p.get('month'), 15):<16}"
                  f"{_cut(p.get('bill_name'), 25):<26}"
                  f"Rp {p['amount']:>22,.2f}")
    print(line)

    print("\n[PEMASUKAN]")
    print(line)
    if not res["pemasukan"]:
        print("[INFO] Tidak ada pemasukan pada periode ini.")
    else:
        print(f"{'No':<5}{'Tanggal':<12}{'Sumber':<42}{'Nominal':>25}")
        print(line)
        for n, (d, tx) in enumerate(res["pemasukan"], 1):
            print(f"{n:<5}{d.strftime('%Y-%m-%d'):<12}"
                  f"{_cut(tx.get('source'), 41):<42}"
                  f"Rp {tx['amount']:>22,.2f}")
    print(line)

    print(f"{'TOTAL BELANJA HARIAN':<58} Rp {res.get('total_belanja', 0.0):>20,.2f}")
    print(f"{'TOTAL TAGIHAN DIBAYAR':<58} Rp {res.get('total_tagihan_dibayar', 0.0):>20,.2f}")
    print(f"{'TOTAL PENGELUARAN KAS':<58} Rp {res['total_pengeluaran']:>20,.2f}")
    print(f"{'TOTAL PEMASUKAN':<58} Rp {res['total_pemasukan']:>20,.2f}")
    print(f"{'SELISIH (Pemasukan - Total Keluar)':<58} Rp {res['selisih']:>20,.2f}")
    print(line)
    if res["tanpa_tanggal"]:
        print(f"[PERINGATAN] {res['tanpa_tanggal']} catatan tidak punya tanggal valid "
              f"(format YYYY-MM-DD) sehingga tidak dapat difilter.")


def filter_transaksi(wallet):
    """
    Menu Filter Transaksi:
    1. Hari Ini   2. Minggu Ini   3. Bulan Ini   0. Kembali
    """
    while True:
        print("\n=== FILTER TRANSAKSI ===")
        print("1. Transaksi Hari Ini")
        print("2. Transaksi Minggu Ini")
        print("3. Transaksi Bulan Ini")
        print("0. Kembali")
        pilihan = input("Pilih: ").strip()

        if pilihan == "0":
            break
        res = filter_transactions(wallet, pilihan)
        if res is None:
            print("[ERROR] Pilihan tidak valid.")
            continue
        print_filter_result(res)


# ==============================================================================
# SELF-CHECK
# ==============================================================================

def _self_check():
    import contextlib
    import io

    today = date(2026, 10, 5)  # Senin
    w = {
        "daily_expenses": [
            {"exp_id": 1, "date": "Senin, 2026-10-05", "category": "Makan", "item_name": "A", "amount": 10000.0},
            {"exp_id": 2, "date": "Minggu, 2026-10-04", "category": "Makan", "item_name": "B", "amount": 20000.0},
            {"exp_id": 3, "date": "Selasa, 2026-10-06", "category": "Minum", "item_name": "C", "amount": 30000.0},
            {"exp_id": 4, "date": "Sabtu, 2026-10-31", "category": "Lain", "item_name": "D", "amount": 40000.0},
            {"exp_id": 5, "date": "Rabu, 2026-09-30", "category": "Lain", "item_name": "E", "amount": 50000.0},
            {"exp_id": 6, "date": "ngawur", "category": "Lain", "item_name": "F", "amount": 60000.0},
        ],
        "bill_payments": [
            {"bill_id": 1, "bill_name": "Wifi", "amount": 350000.0, "month": "2026-10", "date": "2026-10-05"},
            {"bill_id": 2, "bill_name": "Listrik Lama", "amount": 200000.0, "month": "2026-09", "date": "2026-09-25"},
        ],
        "transactions": [
            {"type": "income", "source": "Gaji", "amount": 5000000.0, "date": "2026-10-05"},
            {"type": "income", "source": "Lama", "amount": 1000000.0, "date": "2026-09-01"},
            {"type": "expense", "amount": 999.0, "date": "2026-10-05"},  # bukan income -> diabaikan
        ],
    }

    hari = filter_transactions(w, "1", today)
    assert [e["exp_id"] for _, e in hari["pengeluaran"]] == [1]
    assert len(hari["tagihan_dibayar"]) == 1 and hari["tagihan_dibayar"][0][1]["bill_name"] == "Wifi"
    assert hari["total_belanja"] == 10000.0
    assert hari["total_tagihan_dibayar"] == 350000.0
    assert hari["total_pengeluaran"] == 360000.0
    assert hari["total_pemasukan"] == 5000000.0
    assert hari["selisih"] == 4640000.0
    assert hari["tanpa_tanggal"] == 1

    minggu = filter_transactions(w, "2", today)  # Sen 5 - Min 11 Okt
    assert minggu["mulai"] == date(2026, 10, 5) and minggu["akhir"] == date(2026, 10, 11)
    assert [e["exp_id"] for _, e in minggu["pengeluaran"]] == [1, 3]
    assert len(minggu["tagihan_dibayar"]) == 1

    bulan = filter_transactions(w, "3", today)   # 1 - 31 Okt
    assert bulan["mulai"] == date(2026, 10, 1) and bulan["akhir"] == date(2026, 10, 31)
    assert [e["exp_id"] for _, e in bulan["pengeluaran"]] == [2, 1, 3, 4]  # urut tanggal
    assert len(bulan["pemasukan"]) == 1
    assert len(bulan["tagihan_dibayar"]) == 1

    assert filter_transactions(w, "9", today) is None
    assert filter_transactions({}, "3", today)["total_pengeluaran"] == 0.0   # wallet kosong aman

    # Pekan yang melewati pergantian bulan/tahun
    r = period_range("2", date(2026, 12, 31))  # Kamis
    assert r[0] == date(2026, 12, 28) and r[1] == date(2027, 1, 3)

    # Cetak tidak error & menampilkan peringatan tanpa tanggal
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_filter_result(bulan)
        print_filter_result(filter_transactions({}, "1", today))
    out = buf.getvalue()
    assert "TOTAL PEMASUKAN" in out and "PERINGATAN" in out and "PEMBAYARAN TAGIHAN BULANAN" in out

    # Menu interaktif: pilihan salah, lalu 1, lalu keluar
    import builtins
    jawaban = iter(["x", "1", "0"])
    asli = builtins.input
    builtins.input = lambda _="": next(jawaban)
    try:
        with contextlib.redirect_stdout(io.StringIO()) as sink:
            filter_transaksi(w)
    finally:
        builtins.input = asli
    assert "[ERROR] Pilihan tidak valid." in sink.getvalue()

    print("SELF-CHECK PASS: transaction_filter (hari/minggu/bulan, tagihan dibayar, pemasukan, lintas tahun, tanpa tanggal, menu).")
    return 0


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        raise SystemExit(_self_check())
    wallet_ = finance_core.load_data("data.json")
    try:
        filter_transaksi(wallet_)
    except (KeyboardInterrupt, EOFError):
        print("\n[INFO] Keluar.")
