# ==============================================================================
# MODUL 1: CORE ENGINE & KALKULASI KESEHATAN FINANSIAL (PROJECT LEAD)
# Pembuat : Adzril Adzim Hendrynov (Project Lead)
# File    : finance_core.py  (versi patch audit)
# Deskripsi:
#   - Inisialisasi struktur data akun (wallet)
#   - Konsolidasi pemasukan (income) + CRUD riwayat pemasukan
#   - Persistence layer data.json (load/save, backup otomatis bila korup)
#   - Engine kalkulasi kesehatan finansial (HIJAU / KUNING / MERAH) PER BULAN
#   - Ledger pembayaran tagihan (bill_payments) agar saldo kas tidak "melompat"
#     saat bulan berganti atau tagihan dihapus
# Kontrak antar-modul:
#   - wallet["transactions"]   : list dict riwayat pemasukan/pengeluaran (Lead)
#   - wallet["daily_expenses"] : list dict belanja harian (modul Adriel)
#   - wallet["monthly_bills"]  : list dict tagihan bulanan (modul Darell)
#   - wallet["bill_payments"]  : list dict riwayat pelunasan tagihan (BARU, Lead)
#   - wallet["income"]         : float total pemasukan terkonsolidasi
# ==============================================================================

import calendar
import json
import math
import os
import re
import sys
from datetime import date, datetime

# ==============================================================================
# KONSTANTA & HELPER PARSING (DRY - dipakai finance_core, main, bills_analytics)
# ==============================================================================

# Batas nominal masuk akal: 1 triliun rupiah, tolak nilai raksasa/korup
MAX_AMOUNT = 1e12

HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

_RE_PLAIN = re.compile(r"^\d+(\.\d+)?$")
_RE_THOUSAND_DOT = re.compile(r"^\d{1,3}(\.\d{3})+$")


def _normalize_number_text(raw):
    """
    Normalisasi teks nominal ke format float Python, atau None bila tidak valid.
    Mendukung: "5000000", "5.000.000", "Rp 5.000.000", "5.000.000,50",
    "1,5" (koma = desimal), "5,000,000" (banyak koma = pemisah ribuan),
    "1,234.56" (format Inggris).
    Catatan: "1.500" dibaca 1500 (konvensi Indonesia), "1.5" dibaca 1,5.
    """
    s = re.sub(r"(?i)^\s*rp\.?\s*", "", raw).replace(" ", "")
    if not s:
        return None
    has_comma, has_dot = "," in s, "." in s
    if has_comma and has_dot:
        # Karakter yang muncul TERAKHIR dianggap pemisah desimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_comma:
        if s.count(",") > 1:
            s = s.replace(",", "")          # 5,000,000 -> pemisah ribuan
        else:
            # Cegah ambiguitas (misal "5,000" yang dimaksud 5000 tapi terbaca 5 desimal)
            # Jika tepat 3 digit di belakang koma (misal 5,000), anggap pemisah ribuan
            parts = s.split(",")
            if len(parts) == 2 and len(parts[1]) == 3:
                s = parts[0] + parts[1]     # 5,000 -> 5000
            else:
                s = s.replace(",", ".")     # 12,5 -> desimal (12.5)
    elif has_dot:
        if _RE_THOUSAND_DOT.match(s):
            s = s.replace(".", "")          # 5.000.000 -> pemisah ribuan
    return s if _RE_PLAIN.match(s) else None


def parse_money(raw):
    """
    Helper parsing nominal -> (ok: bool, amount: float | None)
    Tolak: non-angka, bool, inf/nan, <= 0, > MAX_AMOUNT.
    Menerima format Indonesia ("Rp 5.000.000", "1.250.000,50").
    """
    if isinstance(raw, bool):
        return False, None
    if isinstance(raw, str):
        text = _normalize_number_text(raw)
        if text is None:
            return False, None
        raw = text
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
    """
    if today_day is None:
        today_day = datetime.now().day
    if not isinstance(due_day, int):
        return False
    return today_day > due_day


def _is_num(x):
    """True jika x angka finite (bukan bool)."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


# ==============================================================================
# HELPER TANGGAL
# ==============================================================================

def parse_date_any(raw):
    """
    Ambil tanggal dari 10 karakter terakhir format YYYY-MM-DD
    (cocok untuk "2026-10-05" maupun "Senin, 2026-10-05"). Gagal -> None.
    """
    if not isinstance(raw, str):
        return None
    try:
        return datetime.strptime(raw.strip()[-10:], "%Y-%m-%d").date()
    except ValueError:
        return None


def format_date_id(d):
    """Format tanggal standar belanja: 'Senin, 2026-10-05' (hari bahasa Indonesia)."""
    return f"{HARI_ID[d.weekday()]}, {d.strftime('%Y-%m-%d')}"


def month_key(now=None):
    """Kunci bulan 'YYYY-MM'."""
    return (now or datetime.now()).strftime("%Y-%m")


def _in_month(raw_date, mkey):
    """
    True jika tanggal jatuh pada bulan mkey. Tanggal yang tidak bisa dibaca
    (data lama / input bebas) dihitung masuk bulan berjalan agar tidak
    hilang diam-diam dari perhitungan.
    """
    d = parse_date_any(raw_date)
    if d is None:
        return True
    return d.strftime("%Y-%m") == mkey


# ==============================================================================
# INISIALISASI & PERSISTENCE LAYER
# ==============================================================================

def init_wallet():
    """
    Fitur 1: Inisialisasi Struktur Data Akun
    - OUTPUT: Dictionary 'wallet' dengan skema data standar antar-modul.
    """
    return {
        "transactions": [],        # riwayat income/expense (Lead)
        "daily_expenses": [],      # belanja harian (Dev 1: Adriel)
        "monthly_bills": [],       # tagihan bulanan (Dev 2: Darell)
        "bill_payments": [],       # ledger pelunasan tagihan (permanen)
        "income": 0.0,             # total pemasukan terkonsolidasi
        "last_reset_month": None,  # "YYYY-MM" -> penanda reset status tagihan
        "profile": {
            "nama": "",
            "pemasukan_bulanan": 0.0,
        },
    }


def _backup_corrupt(path):
    """Pindahkan file korup ke <path>.bak agar tidak tertimpa save berikutnya."""
    bak = path + ".bak"
    try:
        os.replace(path, bak)
        return bak
    except OSError:
        return None


def load_data(path="data.json"):
    """
    Fitur 2: Muat Data dari File Persistence (Read)
    - File tidak ada / kosong      -> wallet baru
    - JSON rusak / bukan objek     -> file lama DIBACKUP ke .bak, wallet baru
    - Gagal baca (izin, dsb.)      -> wallet baru TANPA menyentuh file
    """
    if not os.path.exists(path):
        return init_wallet()

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        print(f"[WARNING] Gagal membaca {path}: {exc}. Memakai data baru.", file=sys.stderr)
        return init_wallet()

    if not text.strip():
        return init_wallet()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        bak = _backup_corrupt(path)
        print(f"[WARNING] {path} rusak. Salinan disimpan di {bak or '(gagal backup)'}; "
              f"memulai data baru.", file=sys.stderr)
        return init_wallet()

    if not isinstance(data, dict):
        bak = _backup_corrupt(path)
        print(f"[WARNING] Isi {path} bukan objek JSON. Salinan disimpan di "
              f"{bak or '(gagal backup)'}; memulai data baru.", file=sys.stderr)
        return init_wallet()

    wallet = init_wallet()
    wallet.update(data)
    return sanitize_wallet(wallet)


def sanitize_wallet(wallet):
    """
    Pembersih data korup setelah load:
    - Validasi tipe income / profile / transactions / daily_expenses /
      monthly_bills / bill_payments
    - Skip item rusak (log lewat stderr), lengkapi field belanja yang hilang
    """
    def log(msg):
        print(f"[SANITIZE] {msg}", file=sys.stderr)

    if not isinstance(wallet, dict):
        log("wallet bukan dict -> dibuat baru.")
        return init_wallet()

    # --- income ---
    inc = wallet.get("income")
    if _is_num(inc):
        wallet["income"] = float(inc)
    else:
        log(f"income tidak valid ({inc!r}) -> direset 0.0")
        wallet["income"] = 0.0

    # --- profile ---
    profile = wallet.get("profile")
    if not isinstance(profile, dict):
        if profile is not None:
            log(f"profile tidak valid ({profile!r}) -> dibuat baru")
        profile = {}
        wallet["profile"] = profile
    nama = profile.get("nama")
    if isinstance(nama, str):
        profile["nama"] = nama.strip()
    else:
        if nama not in (None, ""):
            log(f"profile.nama tidak valid ({nama!r}) -> dikosongkan")
        profile["nama"] = ""
    ok_pb, pb = parse_money(profile.get("pemasukan_bulanan"))
    if ok_pb and pb is not None:
        profile["pemasukan_bulanan"] = float(pb)
    else:
        if profile.get("pemasukan_bulanan") not in (None, 0, 0.0, ""):
            log("profile.pemasukan_bulanan tidak valid -> direset 0.0")
        profile["pemasukan_bulanan"] = 0.0

    # --- transactions ---
    if not isinstance(wallet.get("transactions"), list):
        if wallet.get("transactions") is not None:
            log("transactions bukan list -> direset []")
        wallet["transactions"] = []
    else:
        kept = []
        for i, tx in enumerate(wallet["transactions"]):
            if isinstance(tx, dict) and _is_num(tx.get("amount")):
                kept.append(tx)
            else:
                log(f"transactions item #{i} rusak, dilewati.")
        wallet["transactions"] = kept

    # --- daily_expenses: amount wajib valid; field lain dilengkapi default ---
    if not isinstance(wallet.get("daily_expenses"), list):
        if wallet.get("daily_expenses") is not None:
            log("daily_expenses bukan list -> direset []")
        wallet["daily_expenses"] = []
    else:
        kept, used_ids = [], set()
        for i, e in enumerate(wallet["daily_expenses"]):
            if not (isinstance(e, dict) and _is_num(e.get("amount"))):
                log(f"daily_expenses item #{i} rusak, dilewati.")
                continue
            e["amount"] = float(e["amount"])
            if not (isinstance(e.get("item_name"), str) and e["item_name"].strip()):
                log(f"daily_expenses item #{i}: item_name kosong -> '(tanpa nama)'")
                e["item_name"] = "(tanpa nama)"
            if not (isinstance(e.get("category"), str) and e["category"].strip()):
                log(f"daily_expenses item #{i}: category kosong -> 'Lainnya'")
                e["category"] = "Lainnya"
            if not (isinstance(e.get("date"), str) and e["date"].strip()):
                log(f"daily_expenses item #{i}: date kosong -> hari ini")
                e["date"] = format_date_id(date.today())
            eid = e.get("exp_id")
            if isinstance(eid, int) and not isinstance(eid, bool) and eid > 0 and eid not in used_ids:
                used_ids.add(eid)
            else:
                e["exp_id"] = None  # diberi ID baru di bawah
            kept.append(e)
        next_id = max(used_ids, default=0) + 1
        for e in kept:
            if e["exp_id"] is None:
                log(f"daily_expenses '{e['item_name']}': exp_id tidak valid -> {next_id}")
                e["exp_id"] = next_id
                next_id += 1
        wallet["daily_expenses"] = kept

    # --- monthly_bills ---
    if not isinstance(wallet.get("monthly_bills"), list):
        if wallet.get("monthly_bills") is not None:
            log("monthly_bills bukan list -> direset []")
        wallet["monthly_bills"] = []
    else:
        kept = []
        for i, b in enumerate(wallet["monthly_bills"]):
            ok_item = (
                isinstance(b, dict)
                and isinstance(b.get("bill_id"), int) and not isinstance(b.get("bill_id"), bool)
                and isinstance(b.get("bill_name"), str) and b["bill_name"].strip()
                and _is_num(b.get("amount"))
                and isinstance(b.get("due_day"), int) and not isinstance(b.get("due_day"), bool)
                and 1 <= b["due_day"] <= 31
                and isinstance(b.get("is_paid"), bool)
            )
            if ok_item:
                kept.append(b)
            else:
                log(f"monthly_bills item #{i} rusak, dilewati.")
        wallet["monthly_bills"] = kept

    # --- bill_payments (ledger) ---
    if not isinstance(wallet.get("bill_payments"), list):
        if wallet.get("bill_payments") is not None:
            log("bill_payments bukan list -> direset []")
        wallet["bill_payments"] = []
    else:
        kept = []
        for i, p in enumerate(wallet["bill_payments"]):
            if (isinstance(p, dict) and _is_num(p.get("amount"))
                    and isinstance(p.get("month"), str)
                    and re.match(r"^\d{4}-\d{2}$", p["month"])):
                kept.append(p)
            else:
                log(f"bill_payments item #{i} rusak, dilewati.")
        wallet["bill_payments"] = kept

    lrm = wallet.get("last_reset_month")
    if not (lrm is None or (isinstance(lrm, str) and re.match(r"^\d{4}-\d{2}$", lrm))):
        log(f"last_reset_month tidak valid ({lrm!r}) -> None")
        lrm = None
    wallet["last_reset_month"] = lrm
    return wallet


def save_data(wallet, path="data.json"):
    """
    Fitur 3: Simpan Data ke File Persistence (Write) - ATOMIC
    Tulis ke file temp lalu os.replace; gagal -> pesan error (tidak melempar).
    """
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(wallet, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except OSError as exc:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return f"Error: Data gagal disimpan ke {path}: {exc}"
    return f"Data berhasil disimpan ke {path}."


# ==============================================================================
# LEDGER PEMBAYARAN TAGIHAN & RESET BULANAN
# ==============================================================================

def sync_bill_payments(wallet, now=None, month_override=None):
    """
    Catat tagihan berstatus LUNAS ke ledger permanen wallet["bill_payments"]
    (satu kali per tagihan per bulan, ditandai b["paid_recorded_month"]).
    Dengan ledger ini saldo kas TIDAK berubah saat tagihan di-reset (ganti bulan),
    dihapus, atau diedit. Mengembalikan jumlah entri baru.
    Panggil setelah pelunasan dan SEBELUM edit/hapus/reset tagihan.
    """
    mkey = month_override or month_key(now)
    when = (now or datetime.now()).strftime("%Y-%m-%d")
    ledger = wallet.setdefault("bill_payments", [])
    added = 0
    for b in wallet.get("monthly_bills", []):
        if not isinstance(b, dict) or not b.get("is_paid"):
            continue
        if b.get("paid_recorded_month") == mkey:
            continue
        if not _is_num(b.get("amount")):
            continue
        ledger.append({
            "bill_id": b.get("bill_id"),
            "bill_name": b.get("bill_name"),
            "amount": float(b["amount"]),
            "month": mkey,
            "date": when,
        })
        b["paid_recorded_month"] = mkey
        added += 1
    return added


def unmark_bill_payment(wallet, bill_id, now=None):
    """
    Batalkan status lunas suatu tagihan dan hapus dari ledger bulan berjalan.
    Mengembalikan (ok: bool, pesan: str).
    """
    mkey = month_key(now)
    target_bill = None
    for b in wallet.get("monthly_bills", []):
        if b.get("bill_id") == bill_id:
            target_bill = b
            break

    if target_bill is None:
        return False, f"Error: Tagihan dengan ID {bill_id} tidak ditemukan."

    if not target_bill.get("is_paid"):
        return False, f"Tagihan '{target_bill.get('bill_name')}' memang belum lunas."

    # Hapus entri dari ledger bill_payments untuk bulan ini
    ledger = wallet.get("bill_payments", [])
    wallet["bill_payments"] = [
        p for p in ledger
        if not (p.get("bill_id") == bill_id and p.get("month") == mkey)
    ]

    # Reset metadata tagihan
    target_bill["is_paid"] = False
    for k in ("paid_late", "paid_on_day", "paid_recorded_month"):
        target_bill.pop(k, None)

    return True, f"Status tagihan '{target_bill.get('bill_name')}' berhasil dikembalikan menjadi BELUM DIBAYAR."



def reset_monthly_bills_if_needed(wallet, now=None):
    """
    Reset status tagihan tiap bulan. Sebelum reset, pelunasan bulan lama
    diarsipkan ke ledger. Mengembalikan True hanya bila reset benar-benar
    terjadi (bukan pada run pertama saat last_reset_month masih kosong).
    """
    mkey = month_key(now)
    last = wallet.get("last_reset_month")
    if last == mkey:
        return False

    sync_bill_payments(wallet, now=now, month_override=last or mkey)

    if last is None:
        wallet["last_reset_month"] = mkey
        return False

    for b in wallet.get("monthly_bills", []):
        if isinstance(b, dict):
            b["is_paid"] = False
            for k in ("paid_late", "paid_on_day", "paid_recorded_month"):
                b.pop(k, None)
    wallet["last_reset_month"] = mkey
    return True


# ==============================================================================
# KONSOLIDASI PEMASUKAN (INCOME) + RIWAYAT
# ==============================================================================

def add_income(wallet, amount, source="", now=None):
    """
    Fitur 4: Tambah & Konsolidasi Pemasukan
    - source kosong -> otomatis "Gaji bulanan {nama}" dari profile wallet
    - OUTPUT : (status bool, pesan str)
    """
    ok, amount = parse_money(amount)
    if not ok:
        return False, "Error: Nominal pemasukan harus angka valid (> 0, bukan inf/nan, maks Rp 1.000.000.000.000,00)."

    source = str(source).strip()
    if not source:
        nama = (wallet.get("profile") or {}).get("nama", "").strip()
        source = f"Gaji bulanan {nama}".strip() if nama else "Gaji bulanan"

    wallet["income"] += amount
    wallet["transactions"].append({
        "type": "income",
        "source": source,
        "amount": amount,
        "date": (now or datetime.now()).strftime("%Y-%m-%d"),
    })
    return True, f"Pemasukan Rp {amount:,.2f} ({source}) berhasil dicatat. Total pemasukan: Rp {wallet['income']:,.2f}."


def list_incomes(wallet):
    """Daftar (index_di_transactions, tx) khusus pemasukan, urut sesuai pencatatan."""
    return [(i, tx) for i, tx in enumerate(wallet.get("transactions", []))
            if isinstance(tx, dict) and tx.get("type") == "income"]


def view_incomes(wallet):
    """Tampilkan riwayat pemasukan bernomor 1..n. Return False bila kosong."""
    items = list_incomes(wallet)
    if not items:
        print("\n[INFO] Belum ada riwayat pemasukan.")
        return False
    print("\n--------------------------------------------------------------------")
    print("NO  | TANGGAL      | SUMBER                       | NOMINAL")
    print("--------------------------------------------------------------------")
    for n, (_, tx) in enumerate(items, 1):
        print(f"{n:<3} | {str(tx.get('date', '-')):<12} | {str(tx.get('source', '-'))[:28]:<28} | Rp {tx['amount']:,.2f}")
    print("--------------------------------------------------------------------")
    return True


def update_income(wallet, number, new_amount, new_source=None):
    """Edit pemasukan nomor `number` (1..n sesuai view_incomes). Saldo ikut disesuaikan."""
    items = list_incomes(wallet)
    if not (isinstance(number, int) and 1 <= number <= len(items)):
        return False, f"Error: Pemasukan nomor {number} tidak ditemukan."
    ok, amt = parse_money(new_amount)
    if not ok:
        return False, "Error: Nominal pemasukan baru harus angka valid (> 0, maks Rp 1.000.000.000.000,00)."
    _, tx = items[number - 1]
    wallet["income"] = max(0.0, wallet["income"] + (amt - tx["amount"]))
    tx["amount"] = amt
    if new_source is not None and str(new_source).strip():
        tx["source"] = str(new_source).strip()
    return True, f"Pemasukan nomor {number} berhasil diperbarui. Total pemasukan: Rp {wallet['income']:,.2f}."


def delete_income(wallet, number):
    """Hapus pemasukan nomor `number`; total pemasukan dikurangi sesuai nominalnya."""
    items = list_incomes(wallet)
    if not (isinstance(number, int) and 1 <= number <= len(items)):
        return False, f"Error: Pemasukan nomor {number} tidak ditemukan."
    idx, tx = items[number - 1]
    wallet["transactions"].pop(idx)
    wallet["income"] = max(0.0, wallet["income"] - tx["amount"])
    return True, f"Pemasukan '{tx.get('source', '-')}' Rp {tx['amount']:,.2f} berhasil dihapus."


def has_income_this_month(wallet, now=None):
    """True bila ada pemasukan tercatat pada bulan berjalan."""
    mkey = month_key(now)
    return any(_in_month(tx.get("date"), mkey) and parse_date_any(tx.get("date")) is not None
               for _, tx in list_incomes(wallet))


# ==============================================================================
# ENGINE KALKULASI FINANSIAL (CORE CALCULATION)
# ==============================================================================

def get_totals(wallet, today_day=None, now=None):
    """
    Fitur 5: Hitung Total-Total Keuangan (ALL-TIME untuk saldo kas)
    - total_bills / paid_bills / unpaid_bills : tagihan siklus BULAN INI (flag is_paid)
    - paid_all_time : seluruh pelunasan tagihan sepanjang waktu (ledger + yang
                      sudah lunas tetapi belum tercatat di ledger)
    - balance_cash  = pemasukan - pengeluaran - paid_all_time
    """
    mkey = month_key(now)
    total_income = float(wallet.get("income") or 0.0)

    total_expense = sum(
        tx["amount"] for tx in wallet.get("transactions", [])
        if isinstance(tx, dict) and tx.get("type") == "expense" and _is_num(tx.get("amount"))
    )
    total_expense += sum(
        e["amount"] for e in wallet.get("daily_expenses", [])
        if isinstance(e, dict) and _is_num(e.get("amount"))
    )

    total_bills = paid_bills = overdue_bills = unrecorded_paid = 0.0
    for b in wallet.get("monthly_bills", []):
        if not isinstance(b, dict) or not _is_num(b.get("amount")):
            continue
        amt = b["amount"]
        total_bills += amt
        if b.get("is_paid"):
            paid_bills += amt
            if b.get("paid_recorded_month") != mkey:
                unrecorded_paid += amt
        elif is_due_passed(b.get("due_day"), today_day):
            overdue_bills += amt
    unpaid_bills = total_bills - paid_bills
    pending_bills = unpaid_bills - overdue_bills

    ledger_total = sum(
        p["amount"] for p in wallet.get("bill_payments", [])
        if isinstance(p, dict) and _is_num(p.get("amount"))
    )
    paid_all_time = ledger_total + unrecorded_paid

    balance_cash = total_income - total_expense - paid_all_time

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "total_bills": total_bills,
        "paid_bills": paid_bills,
        "unpaid_bills": unpaid_bills,
        "overdue_bills": overdue_bills,
        "pending_bills": pending_bills,
        "paid_all_time": paid_all_time,
        "balance_cash": balance_cash,
        "remaining_after_bills": balance_cash - unpaid_bills,
    }


def compute_balance(wallet, now=None):
    """Fitur 6: Hitung Saldo Akun (untuk ditampilkan di main.py)."""
    t = get_totals(wallet, now=now)
    return {
        "saldo_kas": t["balance_cash"],
        "total_pengeluaran": t["total_expense"],
        "komitmen_tagihan_total": t["total_bills"],
        "komitmen_lunas": t["paid_bills"],
        "komitmen_belum_lunas": t["unpaid_bills"],
        "komitmen_terlambat": t["overdue_bills"],
        "komitmen_menunggu": t["pending_bills"],
        "total_tagihan_dibayar": t["paid_all_time"],
        "total_pemasukan": t["total_income"],
        "saldo_setelah_komitmen": t["remaining_after_bills"],
    }


def compute_budget(wallet, now=None):
    """
    Fitur 7: Engine Kesehatan Anggaran (HIJAU / KUNING / MERAH) - PER BULAN
    - Pemasukan & pengeluaran dihitung hanya untuk bulan berjalan (tanggal tak
      terbaca dihitung masuk bulan berjalan); tagihan = seluruh komitmen bulan ini.
    - Sisa anggaran = pemasukan bulan ini - pengeluaran bulan ini - total tagihan.
    - HIJAU >= 30% pemasukan, KUNING > 0, MERAH <= 0 atau pemasukan nihil.
    """
    mkey = month_key(now)
    t = get_totals(wallet, now=now)

    inc_txs = [tx for _, tx in list_incomes(wallet) if _is_num(tx.get("amount"))]
    if inc_txs:
        income = sum(tx["amount"] for tx in inc_txs
                     if parse_date_any(tx.get("date")) is not None and _in_month(tx.get("date"), mkey))
    else:
        income = float(wallet.get("income") or 0.0)  # wallet lama tanpa riwayat

    expense = sum(
        tx["amount"] for tx in wallet.get("transactions", [])
        if isinstance(tx, dict) and tx.get("type") == "expense"
        and _is_num(tx.get("amount")) and _in_month(tx.get("date"), mkey)
    )
    expense += sum(
        e["amount"] for e in wallet.get("daily_expenses", [])
        if isinstance(e, dict) and _is_num(e.get("amount")) and _in_month(e.get("date"), mkey)
    )

    total_obligation = expense + t["total_bills"]
    remaining = income - total_obligation

    if income <= 0:
        ratio, health = 0.0, "MERAH"
        reason = "Belum ada pemasukan tercatat bulan ini."
    else:
        ratio = (remaining / income) * 100
        if remaining >= income * 0.30:
            health, reason = "HIJAU", "Sisa anggaran masih di atas 30% dari pemasukan."
        elif remaining > 0:
            health, reason = "KUNING", "Sisa anggaran tersisa tetapi kurang dari 30% dari pemasukan."
        else:
            health, reason = "MERAH", "Anggaran defisit: pemasukan tidak menutupi pengeluaran & tagihan."

    return {
        "periode": mkey,
        "total_pemasukan": income,
        "total_pengeluaran": expense,
        "total_tagihan": t["total_bills"],
        "total_kewajiban": total_obligation,
        "sisa_anggaran": remaining,
        "rasio_kesehatan_persen": ratio,
        "status": health,
        "alasan": reason,
    }


def display_budget_report(report, nama=""):
    """Fitur 8: Cetak Laporan Kesehatan Anggaran ke Layar."""
    status_icon = {"HIJAU": "[HIJAU] AMAN", "KUNING": "[KUNING] WASPADA", "MERAH": "[MERAH] DEFISIT"}
    print("\n=============== LAPORAN KESEHATAN ANGGARAN ===============")
    if nama:
        print(f"  Profil                 : {nama}")
    if report.get("periode"):
        print(f"  Periode                : {report['periode']}")
    print(f"  Total Pemasukan       : Rp {report['total_pemasukan']:,.2f}")
    if "total_pengeluaran" in report:
        print(f"  Pengeluaran Harian    : Rp {report['total_pengeluaran']:,.2f}")
        print(f"  Tagihan Bulanan       : Rp {report['total_tagihan']:,.2f}")
    print(f"  Total Kewajiban       : Rp {report['total_kewajiban']:,.2f}")
    print(f"  Sisa Anggaran         : Rp {report['sisa_anggaran']:,.2f}")
    print(f"  Rasio Kesehatan       : {report['rasio_kesehatan_persen']:.1f}%")
    print(f"  Status                : {status_icon.get(report['status'], report['status'])}")
    print(f"  Keterangan            : {report['alasan']}")
    print("===========================================================")


# ==============================================================================
# ALERT SIKLUS BERIKUTNYA (LINTAS BULAN)
# ==============================================================================

def check_next_cycle_alerts(wallet, now=None):
    """
    Pelengkap Smart Alert H-3 untuk tagihan yang SUDAH LUNAS bulan ini tetapi
    jatuh temponya jatuh dalam 1-3 hari ke depan di bulan berikutnya
    (mis. hari ini tgl 30, tagihan jatuh tempo tgl 2 -> H-3). Tagihan belum
    lunas sudah ditangani check_due_date_alerts di bills_analytics.
    """
    today = (now or datetime.now()).date()
    ny, nm = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    dim = calendar.monthrange(ny, nm)[1]
    alerts = []
    for b in wallet.get("monthly_bills", []):
        if not isinstance(b, dict) or not b.get("is_paid"):
            continue
        due = b.get("due_day")
        if not isinstance(due, int) or not _is_num(b.get("amount")):
            continue
        nd = date(ny, nm, min(due, dim))
        left = (nd - today).days
        if 1 <= left <= 3:
            alerts.append(
                f"!!! [WARNING BULAN DEPAN] Tagihan '{b['bill_name']}' Rp {b['amount']:,.2f} "
                f"jatuh tempo {left} hari lagi (Tanggal {nd.day}, bulan depan) !!!"
            )
    return alerts


# ==============================================================================
# TES MANDIRI (SELF-CHECK) - Jalan: py finance_core.py
# ==============================================================================

if __name__ == "__main__":
    import contextlib
    import io
    import tempfile
    from datetime import timedelta

    print("[SELF-CHECK] finance_core.py")
    NOW = datetime.now()
    TODAY = NOW.strftime("%Y-%m-%d")
    PAST = "2020-01-05"  # pasti di luar bulan berjalan

    # 1) Inisialisasi skema
    w = init_wallet()
    assert w == {"transactions": [], "daily_expenses": [], "monthly_bills": [], "bill_payments": [],
                 "income": 0.0, "last_reset_month": None,
                 "profile": {"nama": "", "pemasukan_bulanan": 0.0}}

    # 2) Konsolidasi pemasukan
    ok, msg = add_income(w, 5000000, "Gaji", now=NOW)
    assert ok and w["income"] == 5000000.0

    # 3) Pengeluaran (format Adriel) + 4) tagihan (format Darell)
    w["transactions"].append({"type": "expense", "amount": 500000})
    w["daily_expenses"].append({"exp_id": 1, "date": f"Senin, {TODAY}", "category": "Makan",
                                "item_name": "Nasi", "amount": 250000})
    w["monthly_bills"] = [
        {"bill_id": 1, "bill_name": "Listrik", "amount": 300000, "due_day": 5, "is_paid": True},
        {"bill_id": 2, "bill_name": "Internet", "amount": 400000, "due_day": 20, "is_paid": False},
    ]

    # 5) Totals & balance
    t = get_totals(w, now=NOW)
    assert t["total_income"] == 5000000.0
    assert t["total_expense"] == 750000.0
    assert t["paid_bills"] == 300000.0 and t["unpaid_bills"] == 400000.0
    assert t["balance_cash"] == 3950000.0 and t["remaining_after_bills"] == 3550000.0
    b = compute_balance(w, now=NOW)
    assert b["saldo_kas"] == 3950000.0 and b["saldo_setelah_komitmen"] == 3550000.0

    # 6) Health HIJAU (sisa 3.55jt = 71%)
    r = compute_budget(w, now=NOW)
    assert r["status"] == "HIJAU" and r["sisa_anggaran"] == 3550000.0 and r["periode"] == month_key(NOW)

    # 7) Defisit -> MERAH; 8) tanpa pemasukan -> MERAH
    w2 = init_wallet()
    add_income(w2, 1000000, "Gaji", now=NOW)
    w2["transactions"].append({"type": "expense", "amount": 1200000})
    assert compute_budget(w2, now=NOW)["status"] == "MERAH"
    assert compute_budget(init_wallet(), now=NOW)["status"] == "MERAH"

    # 9) Round-trip persistence
    with tempfile.TemporaryDirectory() as td:
        tmp = os.path.join(td, "dk.json")
        save_data(w2, tmp)
        w3 = load_data(tmp)
        assert w3["income"] == 1000000.0 and len(w3["transactions"]) == 2

        # 9b) JSON rusak -> backup .bak, wallet baru; file valid non-dict -> backup juga
        bad = os.path.join(td, "bad.json")
        with open(bad, "w") as f:
            f.write("{rusak")
        with contextlib.redirect_stderr(io.StringIO()):
            wb_ = load_data(bad)
        assert wb_["income"] == 0.0 and os.path.exists(bad + ".bak") and not os.path.exists(bad)
        lst = os.path.join(td, "list.json")
        with open(lst, "w") as f:
            f.write("[1,2]")
        with contextlib.redirect_stderr(io.StringIO()):
            assert load_data(lst)["transactions"] == []
        assert os.path.exists(lst + ".bak")
        empty = os.path.join(td, "empty.json")
        open(empty, "w").close()
        assert load_data(empty)["income"] == 0.0 and not os.path.exists(empty + ".bak")

    # 10) Helper parsing (termasuk format Indonesia)
    assert parse_money(float("inf"))[0] is False and parse_money(float("nan"))[0] is False
    assert parse_money("0")[0] is False and parse_money(MAX_AMOUNT + 1)[0] is False
    assert parse_money("abc")[0] is False and parse_money("inf")[0] is False
    assert parse_money("1e5")[0] is False and parse_money(True)[0] is False
    assert parse_money("")[0] is False and parse_money(None)[0] is False
    for raw, exp in [("125000.5", 125000.5), ("5000000", 5e6), ("5.000.000", 5e6),
                     ("Rp 5.000.000", 5e6), ("rp. 1.250.000,50", 1250000.5), ("1,5", 1.5),
                     ("1.5", 1.5), ("5,000,000", 5e6), ("1,234.56", 1234.56), ("1.500", 1500.0),
                     (250000, 250000.0)]:
        ok, val = parse_money(raw)
        assert ok and val == exp, f"parse_money({raw!r}) -> {val!r}, harapan {exp!r}"
    assert parse_day("0")[0] is False and parse_day("32")[0] is False and parse_day("abc")[0] is False
    ok, d = parse_day("15")
    assert ok and d == 15

    # 11) Sanitizer data korup (termasuk belanja dengan field hilang)
    corrupt = {
        "income": "bukan_angka",
        "transactions": [{"type": "expense", "amount": 1000}, {"type": "expense", "amount": "rusak"}, "bukan_dict"],
        "daily_expenses": [
            {"amount": 5000},                                              # semua field hilang
            {"exp_id": 7, "date": "2026-01-01", "category": "A", "item_name": "B", "amount": 1},
            {"exp_id": 7, "date": "2026-01-02", "category": "A", "item_name": "C", "amount": 2},  # ID ganda
            {"amount": "x"},
        ],
        "monthly_bills": [
            {"bill_id": 1, "bill_name": "Listrik", "amount": 100000, "due_day": 5, "is_paid": False},
            {"bill_id": "rusak", "bill_name": "X", "amount": 10, "due_day": 1, "is_paid": True},
            {"bill_id": 3, "bill_name": "Y", "amount": float("nan"), "due_day": 1, "is_paid": False},
        ],
    }
    with contextlib.redirect_stderr(io.StringIO()):
        clean = sanitize_wallet(corrupt)
    assert clean["income"] == 0.0 and len(clean["transactions"]) == 1 and len(clean["monthly_bills"]) == 1
    assert clean["bill_payments"] == []
    de = clean["daily_expenses"]
    assert len(de) == 3
    ids = [e["exp_id"] for e in de]
    assert len(set(ids)) == 3 and all(isinstance(i, int) for i in ids)
    for e in de:  # semua field wajib terisi -> view_daily_expenses tidak KeyError
        assert e["item_name"] and e["category"] and e["date"] and isinstance(e["amount"], float)

    # 12) Pending vs overdue (injeksi today_day)
    wb = init_wallet()
    wb["income"] = 1000000.0
    wb["monthly_bills"] = [
        {"bill_id": 1, "bill_name": "Due 1", "amount": 100000, "due_day": 1, "is_paid": False},
        {"bill_id": 2, "bill_name": "Due 31", "amount": 200000, "due_day": 31, "is_paid": False},
        {"bill_id": 3, "bill_name": "Lunas", "amount": 300000, "due_day": 1, "is_paid": True},
    ]
    tb = get_totals(wb, today_day=15)
    assert tb["paid_bills"] == 300000.0 and tb["unpaid_bills"] == 300000.0
    assert tb["overdue_bills"] == 100000.0 and tb["pending_bills"] == 200000.0
    cb = compute_balance(wb)
    assert cb["komitmen_terlambat"] + cb["komitmen_menunggu"] == cb["komitmen_belum_lunas"]

    # 13) Reset bulanan: ganti bulan -> is_paid False; bulan sama -> skip; run pertama -> False
    wr = init_wallet()
    wr["monthly_bills"] = [{"bill_id": 1, "bill_name": "Listrik", "amount": 100000, "due_day": 5, "is_paid": True}]
    wr["last_reset_month"] = "2026-08"
    assert reset_monthly_bills_if_needed(wr, datetime(2026, 9, 1)) is True
    assert wr["monthly_bills"][0]["is_paid"] is False and wr["last_reset_month"] == "2026-09"
    assert reset_monthly_bills_if_needed(wr, datetime(2026, 9, 20)) is False
    wf = init_wallet()
    wf["monthly_bills"] = [{"bill_id": 1, "bill_name": "L", "amount": 1, "due_day": 5, "is_paid": True}]
    assert reset_monthly_bills_if_needed(wf, datetime(2026, 9, 1)) is False  # run pertama
    assert wf["monthly_bills"][0]["is_paid"] is True and wf["last_reset_month"] == "2026-09"

    # 14) MAX_AMOUNT ditolak di add_income
    wm = init_wallet()
    assert add_income(wm, MAX_AMOUNT + 1)[0] is False and add_income(wm, float("inf"))[0] is False

    # 15) Profile: migrasi, validasi
    old = {"income": 1000.0, "transactions": [], "daily_expenses": [], "monthly_bills": []}
    assert sanitize_wallet(old)["profile"] == {"nama": "", "pemasukan_bulanan": 0.0}
    with contextlib.redirect_stderr(io.StringIO()):
        bp = sanitize_wallet({"income": 0.0, "profile": {"nama": 123, "pemasukan_bulanan": -5}})
    assert bp["profile"] == {"nama": "", "pemasukan_bulanan": 0.0}
    gp = sanitize_wallet({"income": 0.0, "profile": {"nama": "  Budi  ", "pemasukan_bulanan": "7500000"}})["profile"]
    assert gp["nama"] == "Budi" and gp["pemasukan_bulanan"] == 7500000.0
    with contextlib.redirect_stderr(io.StringIO()):
        hp = sanitize_wallet({"income": 0.0, "profile": {"nama": "X", "pemasukan_bulanan": MAX_AMOUNT + 1}})
    assert hp["profile"]["pemasukan_bulanan"] == 0.0

    # 16) Source default
    wp = init_wallet()
    wp["profile"]["nama"] = "Siti"
    ok, _ = add_income(wp, 2000000, now=NOW)
    assert ok and wp["transactions"][-1]["source"] == "Gaji bulanan Siti" and wp["transactions"][-1]["date"] == TODAY
    w0 = init_wallet()
    add_income(w0, 1000)
    assert w0["transactions"][-1]["source"] == "Gaji bulanan"
    add_income(w0, 1000, "THR")
    assert w0["transactions"][-1]["source"] == "THR"

    # 17) Report
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        display_budget_report(compute_budget(init_wallet(), now=NOW), nama="Budi")
    assert "Budi" in buf.getvalue() and "Profil" in buf.getvalue() and "Periode" in buf.getvalue()
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        display_budget_report(compute_budget(init_wallet(), now=NOW), nama="")
    assert "Profil" not in buf2.getvalue()

    # 18) LEDGER: saldo kas tidak melompat saat ganti bulan / hapus tagihan
    wl = init_wallet()
    wl["income"] = 1000000.0
    wl["monthly_bills"] = [{"bill_id": 1, "bill_name": "Listrik", "amount": 100000, "due_day": 5, "is_paid": True}]
    wl["last_reset_month"] = "2026-09"
    sep = datetime(2026, 9, 10)
    before = get_totals(wl, now=sep)["balance_cash"]
    assert before == 900000.0
    assert sync_bill_payments(wl, now=sep) == 1 and sync_bill_payments(wl, now=sep) == 0  # idempoten
    assert get_totals(wl, now=sep)["balance_cash"] == 900000.0              # tidak dobel hitung
    assert reset_monthly_bills_if_needed(wl, datetime(2026, 10, 1)) is True
    t_oct = get_totals(wl, now=datetime(2026, 10, 1))
    assert t_oct["balance_cash"] == 900000.0, "saldo tidak boleh naik saat reset bulan"
    assert t_oct["paid_bills"] == 0.0 and t_oct["unpaid_bills"] == 100000.0
    assert t_oct["remaining_after_bills"] == 800000.0
    wl["monthly_bills"][0]["is_paid"] = True                                   # bayar lagi bulan baru
    assert get_totals(wl, now=datetime(2026, 10, 2))["balance_cash"] == 800000.0
    sync_bill_payments(wl, now=datetime(2026, 10, 2))
    wl["monthly_bills"].clear()                                                # hapus tagihan lunas
    assert get_totals(wl, now=datetime(2026, 10, 3))["balance_cash"] == 800000.0
    # bill_id yang dipakai ulang tetap tercatat sebagai pembayaran baru
    wl["monthly_bills"] = [{"bill_id": 1, "bill_name": "Baru", "amount": 50000, "due_day": 9, "is_paid": True}]
    assert sync_bill_payments(wl, now=datetime(2026, 10, 4)) == 1
    assert get_totals(wl, now=datetime(2026, 10, 4))["balance_cash"] == 750000.0

    # 19) Anggaran PER BULAN: data bulan lalu tidak ikut
    wm2 = init_wallet()
    add_income(wm2, 5000000, "Gaji lama", now=datetime(2026, 8, 25))
    add_income(wm2, 2000000, "Gaji baru", now=datetime(2026, 9, 25))
    wm2["daily_expenses"] = [
        {"exp_id": 1, "date": "Senin, 2026-08-10", "category": "A", "item_name": "x", "amount": 4000000},
        {"exp_id": 2, "date": "Selasa, 2026-09-10", "category": "A", "item_name": "y", "amount": 500000},
        {"exp_id": 3, "date": "tanggal ngawur", "category": "A", "item_name": "z", "amount": 100000},
    ]
    rm = compute_budget(wm2, now=datetime(2026, 9, 28))
    assert rm["total_pemasukan"] == 2000000.0 and rm["total_pengeluaran"] == 600000.0
    assert rm["status"] == "HIJAU" and rm["periode"] == "2026-09"
    assert get_totals(wm2, now=datetime(2026, 9, 28))["total_expense"] == 4600000.0  # saldo kas: all-time
    wlegacy = init_wallet()
    wlegacy["income"] = 1000.0
    assert compute_budget(wlegacy, now=NOW)["total_pemasukan"] == 1000.0

    # 20) CRUD pemasukan
    wi = init_wallet()
    add_income(wi, 1000000, "A", now=NOW)
    add_income(wi, 2000000, "B", now=NOW)
    with contextlib.redirect_stdout(io.StringIO()):
        assert view_incomes(wi) is True and view_incomes(init_wallet()) is False
    assert update_income(wi, 2, 2500000, "B2")[0] and wi["income"] == 3500000.0
    assert wi["transactions"][1]["source"] == "B2"
    assert update_income(wi, 9, 1)[0] is False and update_income(wi, 1, "abc")[0] is False
    assert delete_income(wi, 1)[0] and wi["income"] == 2500000.0 and len(wi["transactions"]) == 1
    assert delete_income(wi, 5)[0] is False
    assert has_income_this_month(wi, NOW) is True and has_income_this_month(init_wallet(), NOW) is False

    # 21) Alert siklus berikutnya (lintas bulan)
    wa = init_wallet()
    wa["monthly_bills"] = [
        {"bill_id": 1, "bill_name": "Wifi", "amount": 300000, "due_day": 2, "is_paid": True},
        {"bill_id": 2, "bill_name": "Belum", "amount": 100000, "due_day": 2, "is_paid": False},
        {"bill_id": 3, "bill_name": "Jauh", "amount": 100000, "due_day": 20, "is_paid": True},
    ]
    a = check_next_cycle_alerts(wa, datetime(2026, 9, 30))  # due tgl 2 Okt -> 2 hari lagi
    assert len(a) == 1 and "Wifi" in a[0] and "2 hari" in a[0]
    assert check_next_cycle_alerts(wa, datetime(2026, 9, 20)) == []
    # 22) Pembatalan pelunasan tagihan (unmark_bill_payment)
    wu = init_wallet()
    wu["income"] = 1000000.0
    wu["monthly_bills"] = [{"bill_id": 1, "bill_name": "PLN", "amount": 200000.0, "due_day": 5, "is_paid": True}]
    sync_bill_payments(wu, now=NOW)
    assert get_totals(wu, now=NOW)["balance_cash"] == 800000.0
    ok_unm, _ = unmark_bill_payment(wu, 1, now=NOW)
    assert ok_unm and wu["monthly_bills"][0]["is_paid"] is False
    assert len(wu["bill_payments"]) == 0
    assert get_totals(wu, now=NOW)["balance_cash"] == 1000000.0
    assert unmark_bill_payment(wu, 1, now=NOW)[0] is False  # sudah belum lunas
    assert unmark_bill_payment(wu, 99, now=NOW)[0] is False # ID tidak ada

    # 23) Format koma 3 digit dibaca ribuan (5,000 -> 5000)
    assert parse_money("5,000")[1] == 5000.0

    print("[PASS] Semua assertion finance_core lolos.")