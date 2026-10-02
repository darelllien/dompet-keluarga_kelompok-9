def filter_transaksi(wallet):
    """
    Fitur Filter Transaksi
    1. Hari Ini
    2. Minggu Ini
    3. Bulan Ini
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

        # Menentukan periode
        hari_ini = datetime.now().date()

        if pilihan == "1":
            tanggal_awal = hari_ini
            nama_periode = "HARI INI"

        elif pilihan == "2":
            tanggal_awal = hari_ini - timedelta(days=hari_ini.weekday())
            nama_periode = "MINGGU INI"

        elif pilihan == "3":
            tanggal_awal = hari_ini.replace(day=1)
            nama_periode = "BULAN INI"

        else:
            print("[ERROR] Pilihan tidak valid.")
            continue

        transaksi = wallet.get("daily_expenses", [])
        hasil_filter = []

        # Filter transaksi berdasarkan tanggal
        for data in transaksi:
            try:
                tanggal = str(data.get("date", ""))

                # Mengambil bagian YYYY-MM-DD
                tanggal_transaksi = datetime.strptime(
                    tanggal[-10:],
                    "%Y-%m-%d"
                ).date()

                if tanggal_awal <= tanggal_transaksi <= hari_ini:
                    hasil_filter.append(data)

            except (ValueError, TypeError):
                continue

        # Menampilkan hasil
        print(f"\n=== TRANSAKSI {nama_periode} ===")
        print(
            f"Periode: {tanggal_awal.strftime('%d-%m-%Y')} "
            f"sampai {hari_ini.strftime('%d-%m-%Y')}"
        )
        print("-" * 80)

        if not hasil_filter:
            print("[INFO] Tidak ada transaksi pada periode ini.")
            print("-" * 80)
            continue

        print(
            f"{'ID':<5}"
            f"{'Tanggal':<25}"
            f"{'Kategori':<15}"
            f"{'Item':<20}"
            f"{'Nominal':>15}"
        )

        print("-" * 80)

        total = 0

        for data in hasil_filter:
            nominal = float(data.get("amount", 0))
            total += nominal

            print(
                f"{str(data.get('exp_id', '-')):<5}"
                f"{str(data.get('date', '-')):<25}"
                f"{str(data.get('category', '-')):<15}"
                f"{str(data.get('item_name', '-')):<20}"
                f"Rp {nominal:>12,.2f}"
            )

        print("-" * 80)
        print(f"{'TOTAL PENGELUARAN':<65} Rp {total:>12,.2f}")
        print("-" * 80)



              
