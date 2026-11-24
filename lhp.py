"""Modul Laporan Hasil Audit (LHA/LHP) e-Audit Konawe Selatan.
Bentuk mengikuti LHA Inspektorat Daerah Kab. Konawe Selatan: surat pengantar, Bab I Simpulan & Rekomendasi,
Bab II Uraian Hasil Audit (A–H), Bab III Penutup, lampiran. Alur: draf -> reviu (Irban) -> persetujuan (Inspektur) -> terbit."""
import json, os, datetime

KOLOM_TEMUAN = [("judul", "TEXT"), ("kriteria", "TEXT"), ("sebab", "TEXT"), ("akibat", "TEXT"), ("tanggapan", "TEXT"), ("nilai_temuan", "INTEGER"), ("lhp_id", "INTEGER")]
SKEMA = """CREATE TABLE IF NOT EXISTS lhp(id INTEGER PRIMARY KEY, nomor TEXT, tgl TEXT, opd TEXT, judul TEXT, periode TEXT, status TEXT, data TEXT,
  catatan TEXT, dibuat_oleh TEXT, dibuat TEXT, diubah TEXT, reviu_oleh TEXT, reviu_tgl TEXT, terbit_oleh TEXT, terbit_tgl TEXT);"""
ROMAWI = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
# penandatangan LHA dibaca dari data/pengaturan.json (tidak disimpan di kode/repositori)
def _ttd():
    f = os.path.join(os.environ.get("EAUDIT_DATA") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), "pengaturan.json")
    try: return json.load(open(f, encoding="utf-8"))["ttd_inspektur"]
    except Exception: return {"nama": "........................", "pangkat": "", "nip": "........................", "jabatan": "INSPEKTUR DAERAH"}
DASAR = ["Undang-Undang Nomor 17 Tahun 2003 tentang Keuangan Negara;", "Undang-Undang Nomor 1 Tahun 2004 tentang Perbendaharaan Negara;",
         "Undang-Undang Nomor 23 Tahun 2014 tentang Pemerintahan Daerah sebagaimana telah diubah beberapa kali;",
         "Peraturan Pemerintah Nomor 60 Tahun 2008 tentang Sistem Pengendalian Intern Pemerintah;",
         "Peraturan Pemerintah Nomor 12 Tahun 2017 tentang Pembinaan dan Pengawasan Penyelenggaraan Pemerintahan Daerah;",
         "Peraturan Pemerintah Nomor 12 Tahun 2019 tentang Pengelolaan Keuangan Daerah;",
         "Peraturan Menteri Dalam Negeri Nomor 77 Tahun 2020 tentang Pedoman Teknis Pengelolaan Keuangan Daerah;",
         "Keputusan Bupati Konawe Selatan Nomor 700.1/549/2026 tentang Program Kerja Pengawasan Tahunan Berbasis Risiko Inspektorat Daerah Tahun Anggaran 2026;"]
PENUTUP = ["Pelaksanaan audit ini dilaksanakan secara objektif, profesional, dan akuntabel berdasarkan Standar Audit Intern Pemerintah Indonesia (SAIPI) yang ditetapkan dengan Peraturan AAIPI Nomor PER-01/AAIPI/DPN/2021.",
           "Demikian Laporan Hasil Audit ini disampaikan untuk menjadi bahan evaluasi dan tindak lanjut."]

def migrasi(c):
    c.executescript(SKEMA)
    ada = {r[1] for r in c.execute("PRAGMA table_info(temuan)")}
    for k, t in KOLOM_TEMUAN:
        if k not in ada: c.execute(f"ALTER TABLE temuan ADD COLUMN {k} {t}")

def rp(v): return "Rp" + f"{int(v or 0):,}".replace(",", ".") + ",00"

def templat(c, opd, opd_nama, periode, no_st, oleh):
    tem = c.execute("SELECT * FROM temuan WHERE opd=? AND lhp_id IS NULL ORDER BY id", (opd,)).fetchall()
    spj = c.execute("SELECT COUNT(*) n, COALESCE(SUM(s.nilai),0) v FROM audit a JOIN spj s ON s.id=a.spj_id WHERE s.opd=? AND a.status='selesai'", (opd,)).fetchone()
    judul = f"Audit Ketaatan atas Pengelolaan dan Pertanggungjawaban Belanja {periode} pada {opd_nama}"
    n = len(tem)
    data = {
        "kepada": "Bupati Konawe Selatan",
        "perihal": f"Laporan Hasil Audit (LHA) Ketaatan {periode} {opd_nama}",
        "pengantar": [f"Berdasarkan Peraturan Pemerintah Nomor 12 Tahun 2017 tentang Pembinaan dan Pengawasan Penyelenggaraan Pemerintahan Daerah, Program Kerja Pengawasan Tahunan (PKPT) Inspektorat Daerah Kabupaten Konawe Selatan Tahun Anggaran {datetime.date.today().year} dan Surat Tugas Inspektur Nomor {no_st or '…'}, Tim Audit telah melaksanakan {judul}.",
                      "Sehubungan dengan perihal tersebut di atas, bersama ini disampaikan Laporan Hasil Audit sebagaimana terlampir untuk bahan tindak lanjut."],
        "tembusan": ["Wakil Bupati Konawe Selatan;", "Sekretaris Daerah Kabupaten Konawe Selatan;", f"Kepala {opd_nama}."],
        "ttd": dict(_ttd()),
        "simpulan": [f"Berdasarkan hasil {judul} sesuai Surat Tugas Inspektur Nomor {no_st or '…'}, Tim Audit telah menguji {spj['n']} SPJ senilai {rp(spj['v'])} yang diajukan bendahara melalui aplikasi e-Audit.",
                     (f"Pengelolaan administrasi pertanggungjawaban belanja pada {opd_nama} belum sepenuhnya tertib dan taat pada ketentuan peraturan perundang-undangan, dengan {n} permasalahan sebagaimana diuraikan pada Bab II huruf D." if n else
                      f"Pengelolaan administrasi pertanggungjawaban belanja pada {opd_nama} telah tertib dan taat pada ketentuan peraturan perundang-undangan; tidak terdapat temuan.")],
        "rekomendasi_pengantar": f"Berdasarkan temuan hasil audit, Tim Audit merekomendasikan kepada Kepala {opd_nama} selaku Pengguna Anggaran agar:",
        "rekomendasi_umum": [],
        "dasar": list(DASAR) + [f"Surat Tugas Inspektur Daerah Kabupaten Konawe Selatan Nomor {no_st or '…'}."],
        "tujuan_pengantar": f"Pemeriksaan atas pertanggungjawaban pengelolaan keuangan pada {opd_nama} {periode} bertujuan untuk:",
        "tujuan": [f"Memberikan keyakinan yang memadai atas ketaatan dan kepatuhan terhadap peraturan perundang-undangan yang berlaku dalam pengelolaan belanja pada {opd_nama};",
                   f"Meminimalkan terjadinya penyimpangan atas pertanggungjawaban belanja {opd_nama};",
                   f"Memberikan saran perbaikan atas ketidaktaatan dan ketidakpatuhan yang ditemukan dalam pengelolaan belanja pada {opd_nama}."],
        "ruang_lingkup": [f"Ruang lingkup audit adalah dokumen pertanggungjawaban belanja {periode} pada {opd_nama} yang diajukan bendahara melalui aplikasi e-Audit beserta dokumen pendukungnya."],
        "metodologi": ["Metode audit yang digunakan meliputi telaah dokumen pertanggungjawaban belanja yang diunggah bendahara pada aplikasi e-Audit, pengujian kelengkapan dan keabsahan bukti, penyandingan dengan data MONALISA, serta konfirmasi kepada pengelola keuangan."],
        "waktu": ["Audit dilaksanakan selama … hari kerja, mulai tanggal … s.d. … ."],
        "tim": [{"nama": "Narlian, SE., M.M., CGCAE.", "kedudukan": "Penanggung Jawab"}, {"nama": oleh, "kedudukan": "Ketua Tim"}],
        "gambaran": [], "pejabat": [], "anggaran_teks": [], "anggaran": [], "cash_opname": [],
        "hasil_pengantar": [f"Berdasarkan pengujian atas {spj['n']} SPJ senilai {rp(spj['v'])}, Tim Audit menemukan {n} permasalahan sebagai berikut:" if n else "Berdasarkan pengujian, Tim Audit tidak menemukan permasalahan."],
        "tanggapan": [], "apresiasi": [f"Inspektorat Daerah Kabupaten Konawe Selatan memberikan apresiasi atas bantuan dan kerja sama seluruh pejabat dan pengelola keuangan {opd_nama} atas kesediaannya memberikan data dan dokumen yang diperlukan selama pelaksanaan audit."],
        "hal_lain_pengantar": "", "hal_lain": [], "tindak_lanjut": [], "penutup": list(PENUTUP), "lampiran_dokumen": [],
        "footer": f"LHA-KETAATAN {periode.upper()} {opd_nama.upper()}"}
    return judul, data, [t["id"] for t in tem]

def isi_contoh(c, sekarang):
    """LHP contoh: LHA asli Bag. Perencanaan & Keuangan (vers 4) menunggu persetujuan Inspektur."""
    if c.execute("SELECT COUNT(*) FROM lhp").fetchone()[0]: return
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "lha_pk.json")
    if not os.path.exists(f): return
    j = json.load(open(f, encoding="utf-8")); now = sekarang()
    data = {k: v for k, v in j.items() if k not in ("temuan", "tl_rekap")}
    data["rekomendasi_umum"] = j["rekomendasi_umum"]
    c.execute("INSERT INTO lhp(nomor,tgl,opd,judul,periode,status,data,catatan,dibuat_oleh,dibuat,diubah,reviu_oleh,reviu_tgl) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (None, None, "PK", "Audit Ketaatan atas Pengelolaan dan Pertanggungjawaban Belanja Semester I Tahun Anggaran 2026 pada Bagian Perencanaan dan Keuangan Sekretariat Daerah",
               "Semester I Tahun Anggaran 2026", "persetujuan", json.dumps(data, ensure_ascii=False), None, "Tim Audit Irban Wilayah IV", now, now, "Inspektur Pembantu Wilayah IV", now))
    lid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    status = ["tuntas", "belum"]
    tl = ["Kelebihan pembayaran biaya transportasi telah disetor kembali oleh keempat pelaksana perjalanan dinas ke Rekening Kas Umum Daerah pada tanggal 8 September 2026 (STS dan bukti setoran Bank Sultra).",
          "Sisa UP/GU yang belum di-SPJ-kan sebesar Rp6.745.235,00 telah dipertanggungjawabkan dengan 5 Tanda Bukti Kas; PPN Rp772.180,00 dan PPh Pasal 22 Rp105.297,00 belum disajikan bukti setornya."]
    nilai = [1220000, 7678112]
    for k, t in enumerate(j["temuan"]):
        c.execute("""INSERT INTO temuan(spj_id,opd,dok,uraian,rekomendasi,nilai,status,tl_uraian,tl_files,tl_oleh,tl_tgl,verif_oleh,verif_tgl,verif_catatan,dibuat,
                     judul,kriteria,sebab,akibat,tanggapan,nilai_temuan,lhp_id) VALUES(NULL,'PK',?,?,?,?,?,?,'[]',?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  ("Pertanggungjawaban UP/GU", "\n".join(t["kondisi"]), "\n".join(t["rekomendasi"]), nilai[k], status[k], tl[k], "Bendahara Pengeluaran Pembantu", "2026-09-08T10:00:00",
                   "Tim Audit" if status[k] == "tuntas" else None, "2026-10-16T10:00:00" if status[k] == "tuntas" else None,
                   None if status[k] == "tuntas" else "Rekomendasi penyetoran PPN dan PPh Pasal 22 belum ditindaklanjuti.", now,
                   t["judul"], "\n".join(t["kriteria"]), "\n".join(t["sebab"]), "\n".join(t["akibat"]), "\n".join(t["tanggapan"]), nilai[k], lid))
