# ==============================================================================
# MODUL 1: CORE ENGINE & KALKULASI KESEHATAN FINANSIAL (PROJECT LEAD)
# Pembuat : Adzril Adzim Hendrynov (Project Lead)
# File    : finance_core.py
# Deskripsi:
#   - Inisialisasi struktur data akun (wallet)
#   - Konsolidasi pemasukan (income)
#   - Persistence layer data.json (load/save)
#   - Engine kalkulasi kesehatan finansial (HIJAU / KUNING / MERAH)
# Kontrak antar-modul:
#   - wallet["transactions"]   : list dict riwayat pemasukan/pengeluaran (Lead)
#   - wallet["daily_expenses"] : list dict belanja harian (modul Adriel)
#   - wallet["monthly_bills"]  : list dict tagihan bulanan (modul Darell)
#   - wallet["income"]         : float total pemasukan terkonsolidasi
# ==============================================================================

import json
import math
import os
import sys
from datetime import datetime

# ==============================================================================
# KONSTANTA & HELPER PARSING (DRY — dipakai finance_core, main, bills_analytics)
# ==============================================================================

# Batas nominal masuk akal: 1 triliun rupiah, tolak nilai raksasa/korup
MAX_AMOUNT = 1e12


def parse_money(raw):
    """
    Helper parsing nominal -> (ok: bool, amount: float | None)
    Tolak: non-angka, inf/nan, <= 0, > MAX_AMOUNT.
    """
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        return False, None
    if math.isnan(amount) or math.isinf(amount):
        return False, None
    if amount <= 0:
        return False, None
    if amount > MAX_AMOUNT:
        return False, None
    return True, amount


def parse_day(raw):
    """
    Helper parsing tanggal jatuh tempo -> (ok: bool, day: int | None)
    Tolak: non-angka, di luar rentang 1 - 31.
    """
    try:
        day = int(raw)
    except (TypeError, ValueError):
        return False, None
    if not (1 <= day <= 31):
        return False, None
    return True, day


def is_due_passed(due_day, today_day=None):
    """
    True jika tanggal hari ini sudah MELEWATI jatuh tempo bulan ini.
    (Logika kalender sederhana: due bulan ini sudah lewat.)
    """
    if today_day is None:
        today_day = datetime.now().day
    if not isinstance(due_day, int):
        return False
    return today_day > due_day


# ==============================================================================
# INISIALISASI & PERSISTENCE LAYER
# ==============================================================================

def init_wallet():
    """
    Fitur 1: Inisialisasi Struktur Data Akun
    - OUTPUT: Dictionary 'wallet' dengan skema data standar antar-modul.
    - Skema ini KOMPATIBEL dengan modul Darell (monthly_bills) dan modul Adriel
      (transactions), sehingga semua developer memakai satu sumber data.
    """
    return {
        "transactions": [],      # list dict   -> riwayat income/expense (Lead)
        "daily_expenses": [],    # list dict   -> belanja harian (Dev 1: Adriel)
        "monthly_bills": [],     # list dict   -> tagihan bulanan (Dev 2: Darell)
        "income": 0.0,           # float       -> total pemasukan terkonsolidasi (Lead)
        "last_reset_month": None,  # str "YYYY-MM" -> penanda reset status tagihan tiap bulan
    }


def load_data(path="data.json"):
    """
    Fitur 2: Muat Data dari File Persistence (Read)
    - INPUT  : path (str) lokasi file data.json
    - PROCESS: Baca JSON; jika file kosong/rusak, otomatis fallback ke wallet baru
    - OUTPUT : Dictionary 'wallet' siap pakai
    """
    if not os.path.exists(path):
        return init_wallet()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # File kosong (data.json default = {}) atau rusak -> wallet baru
        return init_wallet()

    # Gabungkan dengan skema standar agar key lama yg hilang tetap ada
    wallet = init_wallet()
    wallet.update(data or {})
    wallet.setdefault("transactions", [])
    wallet.setdefault("daily_expenses", [])
    wallet.setdefault("monthly_bills", [])
    wallet.setdefault("income", 0.0)
    wallet.setdefault("last_reset_month", None)
    return sanitize_wallet(wallet)


def sanitize_wallet(wallet):
    """
    Pembersih data korup setelah load:
    - Validasi tipe income / transactions / monthly_bills
    - Skip item rusak, log lewat stderr
    - Normalisasi nilai ke tipe aman
    """
    def log(msg):
        print(f"[SANITIZE] {msg}", file=sys.stderr)

    if not isinstance(wallet, dict):
        log("wallet bukan dict -> dibuat baru.")
        return init_wallet()

    # --- income: harus angka finite, bukan bool ---
    inc = wallet.get("income")
    if isinstance(inc, (int, float)) and not isinstance(inc, bool) and math.isfinite(inc):
        wallet["income"] = float(inc)
    else:
        log(f"income tidak valid ({inc!r}) -> direset 0.0")
        wallet["income"] = 0.0

    # --- transactions: harus list, item dict dgn amount angka finite ---
    if not isinstance(wallet.get("transactions"), list):
        log("transactions bukan list -> direset []")
        wallet["transactions"] = []
    else:
        kept = []
        for i, tx in enumerate(wallet["transactions"]):
            amt = tx.get("amount") if isinstance(tx, dict) else None
            if isinstance(tx, dict) and isinstance(amt, (int, float)) \
                    and not isinstance(amt, bool) and math.isfinite(amt):
                kept.append(tx)
            else:
                log(f"transactions item #{i} rusak, dilewati.")
        wallet["transactions"] = kept

    # --- daily_expenses: harus list, item dict dgn amount angka finite ---
    if not isinstance(wallet.get("daily_expenses"), list):
        log("daily_expenses bukan list -> direset []")
        wallet["daily_expenses"] = []
    else:
        kept = []
        for i, tx in enumerate(wallet["daily_expenses"]):
            amt = tx.get("amount") if isinstance(tx, dict) else None
            if isinstance(tx, dict) and isinstance(amt, (int, float)) \
                    and not isinstance(amt, bool) and math.isfinite(amt):
                kept.append(tx)
            else:
                log(f"daily_expenses item #{i} rusak, dilewati.")
        wallet["daily_expenses"] = kept

    # --- monthly_bills: harus list, item dict lengkap & tipe benar ---
    if not isinstance(wallet.get("monthly_bills"), list):
        log("monthly_bills bukan list -> direset []")
        wallet["monthly_bills"] = []
    else:
        kept = []
        for i, b in enumerate(wallet["monthly_bills"]):
            amt = b.get("amount") if isinstance(b, dict) else None
            ok_item = (
                isinstance(b, dict)
                and isinstance(b.get("bill_id"), int)
                and isinstance(b.get("bill_name"), str) and b["bill_name"].strip()
                and isinstance(amt, (int, float)) and not isinstance(amt, bool)
                and math.isfinite(amt)
                and isinstance(b.get("due_day"), int)
                and 1 <= b["due_day"] <= 31
                and isinstance(b.get("is_paid"), bool)
            )
            if ok_item:
                kept.append(b)
            else:
                log(f"monthly_bills item #{i} rusak, dilewati.")
        wallet["monthly_bills"] = kept

    wallet.setdefault("last_reset_month", None)
    return wallet


def reset_monthly_bills_if_needed(wallet, now=None):
    """
    Reset status tagihan tiap bulan: jika bulan berjalan berubah dari
    'last_reset_month' -> semua is_paid di-set False. Kembalikan bool (reset terjadi?).
    """
    if now is None:
        now = datetime.now()
    month_key = now.strftime("%Y-%m")
    if wallet.get("last_reset_month") == month_key:
        return False
    for b in wallet.get("monthly_bills", []):
        if isinstance(b, dict):
            b["is_paid"] = False
    wallet["last_reset_month"] = month_key
    return True


def save_data(wallet, path="data.json"):
    """
    Fitur 3: Simpan Data ke File Persistence (Write)
    - INPUT  : wallet (dict), path (str)
    - PROCESS: Serialisasi wallet ke JSON dengan format rapi (indent 2)
    - OUTPUT : Pesan konfirmasi tersimpan (str)
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(wallet, f, indent=2, ensure_ascii=False)
    return "Data berhasil disimpan ke data.json."


# ==============================================================================
# KONSOLIDASI PEMASUKAN (INCOME)
# ==============================================================================

def add_income(wallet, amount, source="Pemasukan"):
    """
    Fitur 4: Tambah & Konsolidasi Pemasukan
    - INPUT  : amount (float), source (str) keterangan sumber dana
    - PROCESS: Validasi nominal, akumulasi ke wallet["income"], catat di transaksi
    - OUTPUT : (status bool, pesan str)
    """
    ok, amount = parse_money(amount)

    if not ok:
        return False, "Error: Nominal pemasukan harus angka valid (> 0, bukan inf/nan, maks Rp 1.000.000.000.000,00)."

    # OPERATOR ARITMATIKA (+): Konsolidasi pemasukan ke saldo total
    wallet["income"] += amount

    # Catat riwayat pemasukan di transactions (tipe khusus "income")
    wallet["transactions"].append({
        "type": "income",
        "source": str(source).strip(),
        "amount": amount,
    })

    return True, f"Pemasukan Rp {amount:,.2f} ({source}) berhasil dicatat. Total pemasukan: Rp {wallet['income']:,.2f}."


# ==============================================================================
# ENGINE KALKULASI FINANSIAL (CORE CALCULATION)
# ==============================================================================

def get_totals(wallet):
    """
    Fitur 5: Hitung Total-Total Keuangan (Read - Kalkulasi)
    - PROCESS: Akumulasi pemasukan, pengeluaran harian, dan tagihan (paid/unpaid)
    - OUTPUT : dict berisi ringkasan seluruh total (dipakai modul lain & main.py)
    """
    # Konsolidasi pemasukan: ambil dari akumulator utama
    total_income = wallet.get("income") or 0.0

    # Konsolidasi pengeluaran harian: hanya transaksi bertipe "expense"
    total_expense = sum(
        tx["amount"] for tx in wallet.get("transactions", [])
        if isinstance(tx, dict) and tx.get("type") == "expense"
        and isinstance(tx.get("amount"), (int, float))
    )

    # Konsolidasi belanja harian (modul Adriel, key daily_expenses)
    total_expense += sum(
        e["amount"] for e in wallet.get("daily_expenses", [])
        if isinstance(e, dict) and isinstance(e.get("amount"), (int, float))
    )

    # Konsolidasi komitmen tagihan bulanan (dari modul Darell)
    total_bills = 0.0
    paid_bills = 0.0
    overdue_bills = 0.0  # belum lunas & sudah lewat jatuh tempo bulan ini
    for b in wallet.get("monthly_bills", []):
        if not isinstance(b, dict):
            continue
        amt = b.get("amount")
        if not isinstance(amt, (int, float)):
            continue
        total_bills += amt
        if b.get("is_paid"):
            paid_bills += amt
        elif is_due_passed(b.get("due_day")):
            overdue_bills += amt
    unpaid_bills = total_bills - paid_bills
    pending_bills = unpaid_bills - overdue_bills  # belum lunas, belum jatuh tempo

    # Saldo kas = pemasukan dikurangi yang sudah benar-benar terpakai
    # (pengeluaran harian + tagihan yang sudah lunas dibayar)
    balance_cash = total_income - total_expense - paid_bills

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "total_bills": total_bills,
        "paid_bills": paid_bills,
        "unpaid_bills": unpaid_bills,
        "overdue_bills": overdue_bills,
        "pending_bills": pending_bills,
        "balance_cash": balance_cash,
        # Sisa setelah semua komitmen (tagihan yg belum lunas) terpenuhi
        "remaining_after_bills": balance_cash - unpaid_bills,
    }


def compute_balance(wallet):
    """
    Fitur 6: Hitung Saldo Akun (Core Calculation)
    - PROCESS: Memakai get_totals() lalu menyajikan saldo kas & sisa komitmen
    - OUTPUT : dict berisi rincian saldo (untuk ditampilkan di main.py)
    """
    t = get_totals(wallet)
    return {
        "saldo_kas": t["balance_cash"],
        "total_pengeluaran": t["total_expense"],
        "komitmen_tagihan_total": t["total_bills"],
        "komitmen_lunas": t["paid_bills"],
        "komitmen_belum_lunas": t["unpaid_bills"],
        "komitmen_terlambat": t["overdue_bills"],
        "komitmen_menunggu": t["pending_bills"],
        "total_pemasukan": t["total_income"],
        # Saldo yang benar-benar bebas setelah komitmen tagihan terpenuhi
        "saldo_setelah_komitmen": t["remaining_after_bills"],
    }


def compute_budget(wallet):
    """
    Fitur 7: Engine Kesehatan Anggaran (HIJAU / KUNING / MERAH) - Core Calculation
    - PROCESS:
      1) Ambil total pemasukan, pengeluaran, dan tagihan (Paid & Unpaid).
      2) Sisa anggaran  = pemasukan - pengeluaran - total komitmen tagihan.
      3) Rasio kesehatan = (sisa anggaran / pemasukan) * 100.
      4) STATUS:
         - HIJAU  : sisa anggaran >= 30% dari pemasukan (aman)
         - KUNING : sisa anggaran > 0 tetapi kurang dari 30% (hampir defisit)
         - MERAH  : sisa anggaran <= 0 (defisit) ATAU pemasukan nihil
    - OUTPUT : dict berisi rasio kesehatan + status HIJAU/KUNING/MERAH
    """
    t = get_totals(wallet)
    income = t["total_income"]
    # Total komitmen: pengeluaran harian + seluruh tagihan rutin (Paid & Unpaid)
    total_obligation = t["total_expense"] + t["total_bills"]
    remaining = income - total_obligation

    # Rasio kesehatan anggaran (persen), hindari pembagian dengan nol
    if income <= 0:
        ratio = 0.0
        health = "MERAH"
        reason = "Belum ada pemasukan tercatat."
    else:
        ratio = (remaining / income) * 100
        if remaining >= income * 0.30:
            health = "HIJAU"
            reason = "Sisa anggaran masih di atas 30% dari pemasukan."
        elif remaining > 0:
            health = "KUNING"
            reason = "Sisa anggaran tersisa tetapi kurang dari 30% dari pemasukan."
        else:
            health = "MERAH"
            reason = "Anggaran defisit: pemasukan tidak menutupi pengeluaran & tagihan."

    return {
        "total_pemasukan": income,
        "total_kewajiban": total_obligation,
        "sisa_anggaran": remaining,
        "rasio_kesehatan_persen": ratio,
        "status": health,
        "alasan": reason,
    }


def display_budget_report(report):
    """
    Fitur 8: Cetak Laporan Kesehatan Anggaran ke Layar
    - INPUT  : report (dict) hasil compute_budget()
    - PROCESS: Format hasil kalkulasi menjadi tabel ringkas
    - OUTPUT : - (mencetak langsung ke layar)
    """
    status_icon = {"HIJAU": "[HIJAU] AMAN", "KUNING": "[KUNING] WASPADA", "MERAH": "[MERAH] DEFISIT"}
    print("\n=============== LAPORAN KESEHATAN ANGGARAN ===============")
    print(f"  Total Pemasukan       : Rp {report['total_pemasukan']:,.2f}")
    print(f"  Total Kewajiban       : Rp {report['total_kewajiban']:,.2f}")
    print(f"  Sisa Anggaran         : Rp {report['sisa_anggaran']:,.2f}")
    print(f"  Rasio Kesehatan       : {report['rasio_kesehatan_persen']:.1f}%")
    print(f"  Status                : {status_icon.get(report['status'], report['status'])}")
    print(f"  Keterangan            : {report['alasan']}")
    print("===========================================================")


# ==============================================================================
# TES MANDIRI (SELF-CHECK) - Jalan: py finance_core.py
# ==============================================================================

if __name__ == "__main__":
    print("[SELF-CHECK] finance_core.py")

    # 1) Inisialisasi skema
    w = init_wallet()
    assert w == {"transactions": [], "daily_expenses": [], "monthly_bills": [], "income": 0.0, "last_reset_month": None}

    # 2) Konsolidasi pemasukan
    ok, msg = add_income(w, 5000000, "Gaji")
    assert ok and w["income"] == 5000000.0

    # 3) Simulasi pengeluaran (format transaksi modul Adriel)
    w["transactions"].append({"type": "expense", "amount": 500000})
    w["daily_expenses"].append({"exp_id": 1, "date": "2026-09-20", "category": "Makan", "item_name": "Nasi", "amount": 250000})
    # 4) Simulasi tagihan (modul Darell): 1 lunas, 1 belum
    w["monthly_bills"] = [
        {"bill_id": 1, "bill_name": "Listrik", "amount": 300000, "due_day": 5, "is_paid": True},
        {"bill_id": 2, "bill_name": "Internet", "amount": 400000, "due_day": 20, "is_paid": False},
    ]

    # 5) Verifikasi totals & balance
    t = get_totals(w)
    assert t["total_income"] == 5000000.0
    assert t["total_expense"] == 750000.0  # 500rb transactions + 250rb daily_expenses
    assert t["paid_bills"] == 300000.0 and t["unpaid_bills"] == 400000.0
    assert t["balance_cash"] == 3950000.0
    assert t["remaining_after_bills"] == 3550000.0

    b = compute_balance(w)
    assert b["saldo_kas"] == 3950000.0
    assert b["saldo_setelah_komitmen"] == 3550000.0

    # 6) Verifikasi health: kewajiban = expense 750rb + tagihan 700rb -> sisa 3.55jt (71% -> HIJAU)
    r = compute_budget(w)
    assert r["status"] == "HIJAU" and r["sisa_anggaran"] == 3550000.0

    # 7) Kasus defisit -> MERAH
    w2 = init_wallet()
    ok, _ = add_income(w2, 1000000, "Gaji")
    w2["transactions"].append({"type": "expense", "amount": 1200000})
    assert compute_budget(w2)["status"] == "MERAH"

    # 8) Kasus tanpa pemasukan -> MERAH
    assert compute_budget(init_wallet())["status"] == "MERAH"

    # 9) Round-trip persistence
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "dk_selftest.json")
    save_data(w2, tmp)
    w3 = load_data(tmp)
    assert w3["income"] == 1000000.0 and len(w3["transactions"]) == 2
    os.remove(tmp)

    # 10) Helper parsing: tolak inf/nan/<=0/>MAX, terima valid
    assert parse_money(float("inf"))[0] is False
    assert parse_money(float("nan"))[0] is False
    assert parse_money("0")[0] is False
    assert parse_money(MAX_AMOUNT + 1)[0] is False
    assert parse_money("abc")[0] is False
    ok, val = parse_money("125000.5")
    assert ok and val == 125000.5
    assert parse_day("0")[0] is False and parse_day("32")[0] is False
    assert parse_day("abc")[0] is False
    ok, d = parse_day("15")
    assert ok and d == 15

    # 11) Sanitizer data korup
    corrupt = {
        "income": "bukan_angka",
        "transactions": [
            {"type": "expense", "amount": 1000},
            {"type": "expense", "amount": "rusak"},
            "bukan_dict",
        ],
        "monthly_bills": [
            {"bill_id": 1, "bill_name": "Listrik", "amount": 100000, "due_day": 5, "is_paid": False},
            {"bill_id": "rusak", "bill_name": "X", "amount": 10, "due_day": 1, "is_paid": True},
            {"bill_id": 3, "bill_name": "Y", "amount": float("nan"), "due_day": 1, "is_paid": False},
        ],
    }
    clean = sanitize_wallet(corrupt)
    assert clean["income"] == 0.0
    assert len(clean["transactions"]) == 1
    assert len(clean["monthly_bills"]) == 1
    assert clean["monthly_bills"][0]["bill_id"] == 1

    # 12) Pemisahan pending vs overdue di get_totals / compute_balance
    wb = init_wallet()
    wb["income"] = 1000000.0
    wb["monthly_bills"] = [
        {"bill_id": 1, "bill_name": "Due 1", "amount": 100000, "due_day": 1, "is_paid": False},
        {"bill_id": 2, "bill_name": "Due 31", "amount": 200000, "due_day": 31, "is_paid": False},
        {"bill_id": 3, "bill_name": "Lunas", "amount": 300000, "due_day": 1, "is_paid": True},
    ]
    tb = get_totals(wb)
    # Today ada-ada di bulan berjalan; asumsi today.day > 1 dan < 31 SAAAT self-check dijalankan.
    # (Validasi relatif, bukan absolut.)
    assert tb["paid_bills"] == 300000.0
    assert tb["unpaid_bills"] == 300000.0
    assert tb["overdue_bills"] + tb["pending_bills"] == tb["unpaid_bills"]
    assert tb["overdue_bills"] >= 0.0 and tb["pending_bills"] >= 0.0
    cb = compute_balance(wb)
    assert cb["komitmen_terlambat"] + cb["komitmen_menunggu"] == cb["komitmen_belum_lunas"]

    # 13) Reset bulanan: ganti bulan -> is_paid=False; bulan sama -> skip
    wr = init_wallet()
    wr["monthly_bills"] = [
        {"bill_id": 1, "bill_name": "Listrik", "amount": 100000, "due_day": 5, "is_paid": True},
    ]
    wr["last_reset_month"] = "2026-08"
    assert reset_monthly_bills_if_needed(wr, datetime(2026, 9, 1)) is True
    assert wr["monthly_bills"][0]["is_paid"] is False
    assert wr["last_reset_month"] == "2026-09"
    assert reset_monthly_bills_if_needed(wr, datetime(2026, 9, 20)) is False

    # 14) MAX_AMOUNT ditolak di add_income
    wm = init_wallet()
    assert add_income(wm, MAX_AMOUNT + 1)[0] is False
    assert add_income(wm, float("inf"))[0] is False

    print("[PASS] Semua assertion finance_core lolos.")