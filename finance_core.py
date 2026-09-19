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
#   - wallet["transactions"]   : list dict pengeluaran harian (modul Adriel)
#   - wallet["monthly_bills"]  : list dict tagihan bulanan (modul Darell)
#   - wallet["income"]         : float total pemasukan terkonsolidasi
# ==============================================================================

import json
import os

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
        "transactions": [],   # list dict   -> pengeluaran harian (Dev 1: Adriel)
        "monthly_bills": [],  # list dict   -> tagihan bulanan (Dev 2: Darell)
        "income": 0.0         # float       -> total pemasukan terkonsolidasi (Lead)
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
    wallet.setdefault("monthly_bills", [])
    wallet.setdefault("income", 0.0)
    return wallet


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
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return False, "Error: Nominal pemasukan harus berupa angka."

    if amount <= 0:
        return False, "Error: Nominal pemasukan harus lebih dari 0."

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
    total_income = wallet["income"]

    # Konsolidasi pengeluaran harian: hanya transaksi bertipe "expense"
    total_expense = sum(
        tx["amount"] for tx in wallet["transactions"]
        if tx.get("type") == "expense"
    )

    # Konsolidasi komitmen tagihan bulanan (dari modul Darell)
    total_bills = sum(b["amount"] for b in wallet["monthly_bills"])
    paid_bills = sum(b["amount"] for b in wallet["monthly_bills"] if b.get("is_paid"))
    unpaid_bills = total_bills - paid_bills

    # Saldo kas = pemasukan dikurangi yang sudah benar-benar terpakai
    balance_cash = total_income - total_expense

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "total_bills": total_bills,
        "paid_bills": paid_bills,
        "unpaid_bills": unpaid_bills,
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
    assert w == {"transactions": [], "monthly_bills": [], "income": 0.0}

    # 2) Konsolidasi pemasukan
    ok, msg = add_income(w, 5000000, "Gaji")
    assert ok and w["income"] == 5000000.0

    # 3) Simulasi pengeluaran (format transaksi modul Adriel)
    w["transactions"].append({"type": "expense", "amount": 500000})
    # 4) Simulasi tagihan (modul Darell): 1 lunas, 1 belum
    w["monthly_bills"] = [
        {"bill_id": 1, "bill_name": "Listrik", "amount": 300000, "due_day": 5, "is_paid": True},
        {"bill_id": 2, "bill_name": "Internet", "amount": 400000, "due_day": 20, "is_paid": False},
    ]

    # 5) Verifikasi totals & balance
    t = get_totals(w)
    assert t["total_income"] == 5000000.0
    assert t["total_expense"] == 500000.0
    assert t["paid_bills"] == 300000.0 and t["unpaid_bills"] == 400000.0
    assert t["balance_cash"] == 4500000.0
    assert t["remaining_after_bills"] == 4100000.0

    b = compute_balance(w)
    assert b["saldo_kas"] == 4500000.0
    assert b["saldo_setelah_komitmen"] == 4100000.0

    # 6) Verifikasi health: kewajiban = expense 500rb + tagihan 700rb -> sisa 3.8jt (76% -> HIJAU)
    r = compute_budget(w)
    assert r["status"] == "HIJAU" and r["sisa_anggaran"] == 3800000.0

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

    print("[PASS] Semua assertion finance_core lolos.")