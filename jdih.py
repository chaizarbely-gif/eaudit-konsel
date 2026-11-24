"""JDIH Pengawasan Pemerintah Daerah Konawe Selatan: tabel peraturan + isi awal.
Isi awal berkas PDF diverifikasi dari halaman pertama dokumen aslinya (bukan dari nama berkas).
Status '' berarti belum dicek keberlakuannya; jangan diisi 'berlaku' tanpa sumber resmi."""

KOLOM = ["jenis", "nomor", "tahun", "judul", "tingkat", "bidang", "status", "tgl", "ket", "berkas"]
STATUS = {"", "berlaku", "diubah", "dicabut"}

D = "dokumen/JDIH/"
# jenis, nomor, tahun, judul, tingkat, bidang, status, ket, berkas
ISI = [
    ("Keputusan Bupati", "700.1/549", 2026, "Program Kerja Pengawasan Tahunan Berbasis Risiko Inspektorat Daerah Kabupaten Konawe Selatan Tahun Anggaran 2026", "Daerah", "Pengawasan & SPIP", "", "", D + "Kepbup-700.1-549-2026-PKPT-Berbasis-Risiko.pdf"),
    ("Peraturan BPKP", "5", 2021, "Penilaian Maturitas Penyelenggaraan Sistem Pengendalian Intern Pemerintah Terintegrasi pada Kementerian/Lembaga/Pemerintah Daerah", "Pusat", "Pengawasan & SPIP", "", "", D + "Per-BPKP-5-2021-Maturitas-SPIP-Terintegrasi.pdf"),
    ("Peraturan Menteri Dalam Negeri", "20", 2018, "Pengelolaan Keuangan Desa", "Pusat", "Keuangan Desa", "", "", D + "Permendagri-20-2018-Pengelolaan-Keuangan-Desa.pdf"),
    ("Peraturan Daerah", "3", 2025, "Pengelolaan Barang Milik Daerah", "Daerah", "Barang Milik Daerah", "", "", D + "Perda-3-2025-Pengelolaan-BMD.pdf"),
    ("Peraturan Daerah", "4", 2021, "Pengelolaan Barang Milik Daerah", "Daerah", "Barang Milik Daerah", "", "Perlu dicek apakah telah dicabut/diganti Perda Nomor 3 Tahun 2025 (judul sama).", D + "Perda-4-2021-Pengelolaan-BMD.pdf"),
    ("Peraturan Bupati", "118", 2022, "Perubahan Ketiga atas Peraturan Bupati Konawe Selatan Nomor 18 Tahun 2011 tentang Kebijakan Akuntansi Pemerintah Kabupaten Konawe Selatan", "Daerah", "Keuangan Daerah", "", "", D + "Perbup-118-2022-Kebijakan-Akuntansi.pdf"),
    ("Peraturan Bupati", "57", 2025, "Standar Harga Satuan (SHS) Anggaran Pendapatan dan Belanja Daerah Kabupaten Konawe Selatan Tahun Anggaran 2026", "Daerah", "Standar Biaya", "", "", D + "Perbup-57-2025-SHS-APBD-2026.pdf"),
    ("Peraturan Bupati", "75", 2024, "Standar Satuan Harga Barang dan Jasa Kebutuhan Pemerintah Kabupaten Konawe Selatan Tahun Anggaran 2025", "Daerah", "Standar Biaya", "", "", D + "Perbup-75-2024-SSH-2025.pdf"),
    ("Peraturan Bupati", "93", 2024, "Standar Biaya Umum Anggaran Pendapatan dan Belanja Daerah Kabupaten Konawe Selatan Tahun Anggaran 2025", "Daerah", "Standar Biaya", "diubah", "Diubah dengan Peraturan Bupati Nomor 53 Tahun 2025.", D + "Perbup-93-2024-SBU-APBD-2025.pdf"),
    ("Peraturan Bupati", "53", 2025, "Perubahan atas Peraturan Bupati Konawe Selatan Nomor 93 Tahun 2024 tentang Standar Biaya Umum Anggaran Pendapatan dan Belanja Daerah Kabupaten Konawe Selatan Tahun Anggaran 2025", "Daerah", "Standar Biaya", "", "", D + "Perbup-53-2025-Perubahan-SBU-APBD-2025.pdf"),
    ("Peraturan Bupati", "5", 2023, "Standarisasi Biaya Umum (SBU) Anggaran Pendapatan dan Belanja Desa (APBDesa) Se-Kabupaten Konawe Selatan", "Daerah", "Keuangan Desa", "", "", D + "Perbup-5-2023-SBU-APBDesa.pdf"),
    ("Peraturan Bupati", "6", 2024, "Standarisasi Biaya Umum (SBU) Anggaran Pendapatan dan Belanja Desa (APBDesa) di Kabupaten Konawe Selatan Tahun Anggaran 2024", "Daerah", "Keuangan Desa", "", "", D + "Perbup-6-2024-SBU-APBDesa-2024.pdf"),
    ("Peraturan Bupati", "7", 2024, "Petunjuk Teknis Penggunaan Alokasi Dana Desa (ADD) di Kabupaten Konawe Selatan Tahun Anggaran 2024", "Daerah", "Keuangan Desa", "", "", D + "Perbup-7-2024-Juknis-ADD-2024.pdf"),
    ("Peraturan Bupati", "8", 2024, "Petunjuk Teknis Penggunaan Dana Desa (DD) di Kabupaten Konawe Selatan Tahun Anggaran 2024", "Daerah", "Keuangan Desa", "", "", D + "Perbup-8-2024-Juknis-DD-2024.pdf"),
    # peraturan nasional pokok — berkas PDF diunggah kemudian
    ("Undang-Undang", "17", 2003, "Keuangan Negara", "Pusat", "Keuangan Daerah", "", "", ""),
    ("Undang-Undang", "1", 2004, "Perbendaharaan Negara", "Pusat", "Keuangan Daerah", "", "", ""),
    ("Undang-Undang", "15", 2004, "Pemeriksaan Pengelolaan dan Tanggung Jawab Keuangan Negara", "Pusat", "Pengawasan & SPIP", "", "", ""),
    ("Undang-Undang", "23", 2014, "Pemerintahan Daerah", "Pusat", "Pemerintahan Daerah", "", "", ""),
    ("Undang-Undang", "30", 2014, "Administrasi Pemerintahan", "Pusat", "Pemerintahan Daerah", "", "", ""),
    ("Undang-Undang", "31", 1999, "Pemberantasan Tindak Pidana Korupsi", "Pusat", "Antikorupsi", "", "Diubah dengan Undang-Undang Nomor 20 Tahun 2001.", ""),
    ("Peraturan Pemerintah", "60", 2008, "Sistem Pengendalian Intern Pemerintah", "Pusat", "Pengawasan & SPIP", "", "", ""),
    ("Peraturan Pemerintah", "12", 2017, "Pembinaan dan Pengawasan Penyelenggaraan Pemerintahan Daerah", "Pusat", "Pengawasan & SPIP", "", "", ""),
    ("Peraturan Pemerintah", "48", 2016, "Tata Cara Pengenaan Sanksi Administratif kepada Pejabat Pemerintahan", "Pusat", "Pemerintahan Daerah", "", "", ""),
    ("Peraturan Pemerintah", "12", 2019, "Pengelolaan Keuangan Daerah", "Pusat", "Keuangan Daerah", "", "", ""),
    ("Peraturan Pemerintah", "94", 2021, "Disiplin Pegawai Negeri Sipil", "Pusat", "Kepegawaian", "", "", ""),
    ("Peraturan Presiden", "16", 2018, "Pengadaan Barang/Jasa Pemerintah", "Pusat", "Pengadaan Barang/Jasa", "", "Diubah dengan Peraturan Presiden Nomor 12 Tahun 2021.", ""),
    ("Peraturan Presiden", "72", 2025, "Standar Harga Satuan Regional", "Pusat", "Standar Biaya", "", "", ""),
    ("Peraturan Menteri Dalam Negeri", "77", 2020, "Pedoman Teknis Pengelolaan Keuangan Daerah", "Pusat", "Keuangan Daerah", "", "", ""),
    ("Peraturan Menteri Dalam Negeri", "19", 2016, "Pedoman Pengelolaan Barang Milik Daerah", "Pusat", "Barang Milik Daerah", "", "", ""),
    ("Peraturan Menteri Dalam Negeri", "47", 2021, "Tata Cara Pelaksanaan Pembukuan, Inventarisasi, dan Pelaporan Barang Milik Daerah", "Pusat", "Barang Milik Daerah", "", "", ""),
]


def migrasi(c):
    c.execute("CREATE TABLE IF NOT EXISTS jdih(id INTEGER PRIMARY KEY, jenis TEXT NOT NULL, nomor TEXT NOT NULL, tahun INTEGER, judul TEXT NOT NULL, "
              "tingkat TEXT, bidang TEXT, status TEXT DEFAULT '', tgl TEXT, ket TEXT, berkas TEXT)")
    if not c.execute("SELECT 1 FROM jdih LIMIT 1").fetchone():
        c.executemany("INSERT INTO jdih(jenis,nomor,tahun,judul,tingkat,bidang,status,ket,berkas) VALUES(?,?,?,?,?,?,?,?,?)", ISI)
    # tambahan isi setelah rilis awal: dimasukkan sekali saja (tanda di tabel meta), agar yang dihapus admin tidak muncul lagi
    c.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
    if not c.execute("SELECT 1 FROM meta WHERE k='jdih_perbup57_2025'").fetchone():
        if not c.execute("SELECT 1 FROM jdih WHERE jenis='Peraturan Bupati' AND nomor='57' AND tahun=2025").fetchone():
            c.execute("INSERT INTO jdih(jenis,nomor,tahun,judul,tingkat,bidang,status,ket,berkas) VALUES(?,?,?,?,?,?,?,?,?)", next(x for x in ISI if x[1] == "57" and x[2] == 2025))
        c.execute("INSERT INTO meta VALUES('jdih_perbup57_2025', '1')")
