"""
==============================================================================
SKRIP SIMULASI SESI END-TO-END (CLI TEST RUNNER)
File: simulate_session.py
Deskripsi:
  Menguji alur menu utama dan submenu interaktif secara otomatis tanpa input
  manual manusia. Memvalidasi bahwa alur onboarding, penambahan pemasukan,
  pencatatan belanja harian, penambahan dan pelunasan tagihan, pembatalan pelunasan,
  filter transaksi, serta ringkasan keuangan berjalan tanpa crash.
Jalankan:
  py simulate_session.py
==============================================================================
"""

import builtins
import contextlib
import io
import os
import sys

import finance_core
import main

TEST_DATA = "data_test_simulation.json"


def run_simulation():
    print("[SIMULASI] Menjalankan uji alur sesi interaktif...")

    # Bersihkan file test jika ada sebelumnya
    for f in (TEST_DATA, TEST_DATA + ".bak", TEST_DATA + ".tmp"):
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass

    # Arahkan DATA_FILE main ke test data
    main.DATA_FILE = TEST_DATA

    # Skenario input pengguna:
    # 1. Onboarding: Nama "Keluarga Cemara", Pemasukan "10000000"
    # 2. Catat pemasukan awal bulan (offer): Y
    # 3. Menu 1 (Pemasukan) -> 2 (Lihat) -> 0 (Kembali)
    # 4. Menu 4 (Tagihan) -> 2 (Tambah "Internet", "350000", "10") -> 1 (Lihat "")
    #    -> 3 (Lunasi ID 1) -> 4 (Batal Lunasi ID 1, Y) -> 3 (Lunasi lagi ID 1)
    #    -> 0 (Kembali)
    # 5. Menu 5 (Belanja) -> 1 (Tambah "Beras", "Bahan Pokok", "75000", "")
    #    -> 2 (Lihat) -> 0 (Kembali)
    # 6. Menu 6 (Filter) -> 1 (Hari ini) -> 3 (Bulan ini) -> 0 (Kembali)
    # 7. Menu 2 (Ringkasan Keuangan)
    # 8. Menu 3 (Kesehatan Anggaran)
    # 9. Menu 0 (Keluar)
    inputs = [
        # Onboarding
        "Keluarga Cemara",
        "10000000",
        # Offer bulanan
        "y",
        # Menu 1: Pemasukan
        "1",
        "2",
        "0",
        # Menu 4: Tagihan
        "4",
        "2", "Internet", "350000", "10",
        "1", "",
        "3", "1",
        "4", "1", "y",
        "3", "1",
        "0",
        # Menu 5: Belanja
        "5",
        "1", "Beras", "Bahan Pokok", "75000", "",
        "2",
        "0",
        # Menu 6: Filter
        "6",
        "1",
        "3",
        "0",
        # Menu 2: Ringkasan
        "2",
        # Menu 3: Kesehatan
        "3",
        # Menu 0: Keluar
        "0",
    ]

    input_iter = iter(inputs)

    def mock_input(prompt=""):
        try:
            val = next(input_iter)
            return val
        except StopIteration:
            return "0"

    original_input = builtins.input
    builtins.input = mock_input

    output_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_buffer):
            main.main()
    finally:
        builtins.input = original_input

    captured = output_buffer.getvalue()

    # Validasi output
    assert "Keluarga Cemara" in captured, "Gagal onboarding nama"
    assert "Internet" in captured, "Gagal mencatat tagihan"
    assert "Beras" in captured, "Gagal mencatat belanja"
    assert "TOTAL PEMASUKAN" in captured, "Gagal filter transaksi"
    assert "RINGKASAN KEUANGAN" in captured, "Gagal tampilkan ringkasan keuangan"
    assert "Terima kasih telah menggunakan DompetKeluarga" in captured, "Gagal keluar dengan rapi"

    # Verifikasi data tersimpan di file persistence
    assert os.path.exists(TEST_DATA), "File persistensi tidak dibuat"
    w = finance_core.load_data(TEST_DATA)
    assert w["profile"]["nama"] == "Keluarga Cemara"
    assert w["income"] == 10000000.0
    assert len(w["monthly_bills"]) == 1
    assert w["monthly_bills"][0]["is_paid"] is True
    assert len(w["daily_expenses"]) == 1
    assert len(w["bill_payments"]) == 1

    # Cleanup test files
    for f in (TEST_DATA, TEST_DATA + ".bak", TEST_DATA + ".tmp"):
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass

    print("[PASS] Simulasi sesi interaktif end-to-end berhasil tanpa error!")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_simulation())
