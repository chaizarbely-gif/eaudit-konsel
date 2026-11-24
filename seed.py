"""Data awal e-Audit Konawe Selatan: akun, OPD, paket MONALISA, SPJ contoh, GU I (data nyata hasil OCR),
hasil pemeriksaan, temuan & tindak lanjut, PKPT 2026, agenda & surat tugas."""
import json, os, datetime

import secrets
SANDI_AWAL = "".join(secrets.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(10))  # acak per instalasi; tampil di konsol & riwayat
OPD = [("PUPR", "Dinas Pekerjaan Umum dan Penataan Ruang"), ("DINKES", "Dinas Kesehatan"), ("DIKBUD", "Dinas Pendidikan dan Kebudayaan"),
       ("DINSOS", "Dinas Sosial"), ("BKAD", "Badan Keuangan dan Aset Daerah"), ("BAPPEDA", "Bappeda"), ("KOMINFO", "Dinas Kominfo dan Persandian"),
       ("SETDA", "Sekretariat Daerah"), ("PK", "Bag. Perencanaan & Keuangan Setda")]
KEG = {
    "PUPR": [["Rehabilitasi jalan kabupaten ruas A", "KON"], ["Pembangunan saluran drainase", "KON"], ["Rapat koordinasi penataan ruang", "MMR"], ["Pengadaan alat ukur topografi", "BRG"], ["Monitoring jalan kabupaten", "SPPD"]],
    "DINKES": [["Bimtek tenaga kesehatan puskesmas", "HON"], ["Pengadaan alat kesehatan puskesmas", "BRG"], ["Supervisi imunisasi kecamatan", "SPPD"], ["Rehabilitasi gedung puskesmas", "KON"], ["Rapat evaluasi program stunting", "MMR"]],
    "DIKBUD": [["Workshop kurikulum guru SD", "HON"], ["Pengadaan buku perpustakaan sekolah", "BRG"], ["Rehabilitasi ruang kelas SD", "KON"], ["Monitoring dana BOSP sekolah", "SPPD"]],
    "DINSOS": [["Sosialisasi program bantuan sosial", "HON"], ["Verifikasi data DTKS kecamatan", "SPPD"], ["Pengadaan paket bantuan lansia", "BRG"], ["Rapat koordinasi PKH", "MMR"]],
    "BKAD": [["Bimtek penatausahaan keuangan", "HON"], ["Rekonsiliasi aset perangkat daerah", "SPPD"], ["Rapat penyusunan LKPD", "MMR"], ["Pengadaan server arsip keuangan", "BRG"]],
    "BAPPEDA": [["Musrenbang tingkat kabupaten", "MMR"], ["FGD penyusunan RKPD", "HON"], ["Monev pembangunan kecamatan", "SPPD"]],
    "KOMINFO": [["Pengadaan perangkat jaringan", "BRG"], ["Pelatihan admin aplikasi OPD", "HON"], ["Pemeliharaan jaringan kecamatan", "SPPD"]],
    "SETDA": [["Rapat koordinasi pimpinan", "MMR"], ["Kunjungan kerja studi banding", "SPPD"], ["Bimtek pengadaan barang/jasa", "HON"], ["Pengadaan kendaraan operasional", "BRG"]]}
RENTANG = {"HON": (3e6, 15e6), "SPPD": (4e6, 35e6), "BRG": (15e6, 180e6), "KON": (150e6, 1.6e9), "MMR": (2e6, 12e6)}
KODE = {"HON": "5.1.02.02.001.00003", "SPPD": "5.1.02.04.001.00001", "BRG": "5.1.02.01.001.00024", "KON": "5.2.03.01.001.00001", "MMR": "5.1.02.01.001.00052"}
CEKN = {"HON": 4, "SPPD": 3, "BRG": 3, "KON": 3, "MMR": 3, "PDGU": 4, "BLGU": 3}
MP_PK = ["Koordinasi dan konsultasi perencanaan dan keuangan (perjalanan dinas, swakelola)", "Operasional Bagian Perencanaan dan Keuangan (swakelola)"]
PKPT = [
    ["Audit kinerja 10 OPD", "Audit Kinerja", "10 OPD", 5, 6, 860, 198000000, "Irban 1–4", "Tinggi"],
    ["Audit pengelolaan dana BOSP", "Audit Ketaatan", "Sekolah SD/SMP 25 kecamatan", 8, 9, 72, 353530000, "Irban 1–4", "Tinggi"],
    ["Audit pengelolaan keuangan OPD", "Audit Ketaatan", "36 OPD", 8, 9, 42, 269250000, "Irban 1–4, Irves", "Tinggi"],
    ["Audit pengelolaan dana BOK/JKN", "Audit Ketaatan", "25 Puskesmas", 8, 9, 62, 280920000, "Irban 1–4", "Sedang"],
    ["Audit DAPODIK", "Audit Ketaatan", "Sekolah SD/SMP 25 kecamatan", 8, 9, 62, 75350000, "Irban 1–4", "Tinggi"],
    ["Asistensi APBDes", "Asistensi", "25 kecamatan", 11, 12, 26, 115330000, "Irban 1–4", "Sedang"],
    ["Audit dana reses DPRD", "Audit Ketaatan", "6 dapil", 11, 12, 72, 195290000, "Irban 1–4", "Sedang"],
    ["Reviu perencanaan dan kinerja (15 reviu)", "Reviu", "Bappeda, BKAD, BKPSDM, OPD", 1, 12, 405, 62992200, "Irban 1–4, Irves", "Sedang"],
    ["Reviu laporan keuangan dan anggaran (8 reviu)", "Reviu", "BKAD, Bapenda, 36 OPD", 2, 10, 97, 29617144, "Irban 1–4, Irves", "Sedang"],
    ["Audit Dana Desa dan ADD", "Audit Ketaatan", "25 kecamatan", 7, 8, 106, 578030000, "Irban 1–4", "Tinggi"],
    ["Pendampingan tim eksternal (BPK)", "Pendampingan", "OPD", 1, 5, 8, 194280000, "Sekretariat", "Sedang"],
    ["Monev tindak lanjut temuan", "Monitoring", "Pemerintah daerah", 1, 12, 62, 390449800, "Sekretariat", "Sedang"],
    ["Perhitungan kerugian keuangan daerah", "PKKN", "Pemerintah daerah", 1, 12, 210, 24330000, "Irves", "Sedang"],
    ["Probity audit 5 proyek strategis", "Probity Audit", "5 proyek strategis", 1, 12, 650, 517099600, "Irban 1–4, Irves", "Sedang"],
    ["Audit investigasi", "Audit Investigasi", "Pemerintah daerah", 1, 12, 2310, 42290000, "Irves", "Tinggi"],
    ["Audit tematik", "Audit Tematik", "Pemerintah daerah", 1, 12, 650, 63750000, "Irban 1–4, Irves", "Tinggi"],
    ["Evaluasi SPIP", "Evaluasi", "Sekretariat Daerah", 6, 6, 34, 77550000, "Irban 3", "Sedang"],
    ["Penilaian kapabilitas APIP", "Evaluasi", "Inspektorat", 4, 6, 34, 377710000, "Seluruh unit", "Sedang"],
    ["Asistensi pelaporan LHKPN/LHKASN", "Asistensi", "36 OPD, 25 kecamatan, 336 kades", 3, 3, 25, 9020000, "Irban 1", "Sedang"],
    ["MCP Korsupgah KPK", "Monitoring", "8 area", 3, 12, 25, 6237200, "Irban 2", "Sedang"],
    ["Monev Survei Penilaian Integritas", "Monitoring", "Sekretariat Daerah", 7, 10, 20, 10375000, "Irban 2", "Sedang"],
    ["Monitoring pengendalian inflasi", "Monitoring", "Masyarakat", 3, 12, 10, 14720000, "Irban 3", "Sedang"],
    ["Monev P3DN", "Monitoring", "OPD", 1, 12, 17, 32640000, "Irban 2", "Sedang"],
    ["Sosialisasi pencegahan korupsi", "Sosialisasi", "Masyarakat", 3, 10, 25, 124940000, "Irves", "Sedang"]]

def rng(seed):
    st = [seed & 0xFFFFFFFF]
    def imul(a, b): return (a * b) & 0xFFFFFFFF
    def r():
        s = (st[0] + 0x6D2B79F5) & 0xFFFFFFFF; st[0] = s
        t = imul(s ^ (s >> 15), 1 | s)
        t = ((t + imul(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return r

def isi(c, hash_pw, JENIS_DOCS, BLN, sekarang):
    now = sekarang(); tahun = 2026; bulan_ini = min(datetime.date.today().month, 12)
    c.executemany("INSERT INTO opd VALUES(?,?)", OPD)
    on = dict(OPD)
    # ---------- akun
    akun = [("admin", "Administrator Sistem", "admin", None, "Administrator"), ("inspektur", "Inspektur Daerah", "inspektur", None, "Inspektur"),
            ("irban1", "Inspektur Pembantu Wilayah I", "irban", None, "Inspektur Pembantu"), ("irban2", "Inspektur Pembantu Wilayah II", "irban", None, "Inspektur Pembantu"),
            ("auditor1", "Auditor Ahli Muda 1", "auditor", None, "Auditor Ahli Muda"), ("auditor2", "Auditor Ahli Pertama 2", "auditor", None, "Auditor Ahli Pertama")]
    for k, n in OPD:
        akun += [(f"bendahara.{k.lower()}", f"Bendahara Pengeluaran {n}", "bendahara", k, "Bendahara Pengeluaran"),
                 (f"ppk.{k.lower()}", f"PPK {n}", "ppk", k, "Pejabat Pembuat Komitmen"),
                 (f"pa.{k.lower()}", f"PA/KPA {n}", "pakpa", k, "Pengguna Anggaran")]
    for un, nama, peran, opd, jab in akun:
        s, h = hash_pw(SANDI_AWAL)
        c.execute("INSERT INTO users(username,nama,nip,jabatan,peran,opd,salt,hash,aktif,dibuat) VALUES(?,?,?,?,?,?,?,?,1,?)", (un, nama, "", jab, peran, opd, s, h, now))
    # ---------- paket MONALISA + SPJ contoh
    R = rng(2026); R2 = rng(77)
    CAT = ["Tanda tangan penerima tidak lengkap", "Tanggal dokumen tidak sesuai tanggal kegiatan", "Nilai berbeda dengan kuitansi", "Foto tidak menunjukkan objek kegiatan"]
    for k, _ in OPD:
        if k not in KEG: continue
        no = 0
        for nm, j in KEG[k]:
            fisik = int(30 + R() * 65) if j == "KON" else None
            keu = int(min(100, fisik + (R() * 40 - 12))) if j == "KON" else None
            c.execute("INSERT INTO monalisa(opd,nama,nilai,fisik,keu,sumber) VALUES(?,?,?,?,?,'contoh')", (k, nm, 0, fisik, keu))
            mp = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            n = 2 if R() < 0.7 else 1; tot = 0
            for t in range(n):
                lo, hi = RENTANG[j]; m = 1 + int(R() * min(11, bulan_ini)); nilai = int(round((lo + R() * (hi - lo)) / 1e5) * 1e5); tot += nilai
                docs = [{"n": d, "s": "ok"} for d in JENIS_DOCS[j]]; r = R()
                if r < 0.17:
                    st = "draf"; up = int(R() * (len(docs) - 1))
                    for i in range(up, len(docs)): docs[i]["s"] = "kosong"
                elif r < 0.26:
                    st = "kembali"; docs[int(R() * len(docs))]["s"] = "ditolak"
                else:
                    q = R()
                    if m <= bulan_ini - 3: st = "dibayar" if q < .72 else "bendahara" if q < .86 else "ppk" if q < .95 else "diajukan"
                    elif m <= bulan_ini - 1: st = "dibayar" if q < .35 else "bendahara" if q < .6 else "ppk" if q < .82 else "diajukan"
                    else: st = "diajukan" if q < .5 else "ppk"
                no += 1; sid = f"{k}-{no:03d}"
                files = {str(i): {"name": d["n"].lower().replace(" / ", "_").replace(" ", "_") + f"_{sid}.pdf", "size": 180000 + (i * 97 + m * 31) % 9 * 95000, "type": "application/pdf", "fake": True}
                         for i, d in enumerate(docs) if d["s"] == "ok"}
                data = {"pptk": "PPTK " + ["Bidang Program", "Bidang Teknis", "Bidang Pelayanan", "Subbagian Umum"][no % 4], "docs": docs,
                        "cek": [st not in ("draf", "kembali")] * CEKN[j], "nk": "", "files": files}
                tgl = f"{3 + int(R() * 24)} {BLN[m - 1]} {tahun}"
                aju = f"{tahun}-{m:02d}-{min(28, 5 + no):02d}T10:00:00" if st not in ("draf", "kembali") else None
                c.execute("INSERT INTO spj(id,opd,mp_id,jenis,bulan,nilai,uraian,bku,tgl,kode,penerima,status,catatan,tgl_aju,no_sp2d,sumber,data,dibuat,diubah) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'contoh',?,?,?)",
                          (sid, k, mp, j, m, nilai, nm + (f" (tahap {'I' if t == 0 else 'II'})" if n > 1 else ""), str(no), tgl, KODE[j], "Penerima/penyedia contoh",
                           st, "Dokumen tidak terbaca jelas, mohon unggah ulang." if st == "kembali" else None, aju,
                           f"0{no}{m:02d}/SP2D/{k}/{tahun}" if st == "dibayar" else None, json.dumps(data, ensure_ascii=False), now, now))
                # hasil pemeriksaan contoh
                if st not in ("draf", "kembali") and (k in ("BKAD", "BAPPEDA", "KOMINFO") or R2() < 0.45):
                    cek = {str(i): "s" for i in range(len(docs))}; cat = {}
                    if R2() < 0.3:
                        i = int(R2() * len(docs)); cek[str(i)] = "t"; cat[str(i)] = CAT[int(R2() * len(CAT))]
                    tg = f"{tahun}-{bulan_ini:02d}-{3 + int(R2() * 14):02d}T09:00:00"
                    c.execute("INSERT INTO audit VALUES(?,?,?,?,?)", (sid, json.dumps({"cek": cek, "cat": cat}), "selesai", "Auditor Ahli Muda 1", tg))
                    for i, v in cek.items():
                        if v == "t":
                            dok = docs[int(i)]["n"]; pilih = R2()
                            stt = "tuntas" if pilih < 0.35 else "menunggu" if pilih < 0.6 else "belum"
                            tl = "Dokumen telah diperbaiki dan diunggah ulang oleh bendahara." if stt != "belum" else None
                            c.execute("INSERT INTO temuan(spj_id,opd,dok,uraian,rekomendasi,nilai,status,tl_uraian,tl_files,tl_oleh,tl_tgl,verif_oleh,verif_tgl,verif_catatan,dibuat) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                      (sid, k, dok, cat[i], f"Kepala {on[k]} agar memerintahkan bendahara pengeluaran memperbaiki dan mengunggah ulang \"{dok}\" yang sah.", nilai, stt,
                                       tl, json.dumps([{"name": "bukti_tindak_lanjut.pdf", "fake": True}]) if tl else "[]", f"Bendahara Pengeluaran {on[k]}" if tl else None,
                                       tg if tl else None, "Auditor Ahli Muda 1" if stt == "tuntas" else None, tg if stt == "tuntas" else None, "Bukti sesuai." if stt == "tuntas" else None, tg))
            c.execute("UPDATE monalisa SET nilai=? WHERE id=?", (tot, mp))
    # ---------- pastikan setiap OPD punya SPJ di tahap verifikasi PPK dan pengesahan PA/KPA (untuk latihan semua peran)
    for k, _ in OPD:
        if k not in KEG: continue
        for tahap in ("diajukan", "ppk"):
            if c.execute("SELECT 1 FROM spj WHERE opd=? AND status=?", (k, tahap)).fetchone(): continue
            r = c.execute("SELECT id FROM spj WHERE opd=? AND status IN ('dibayar','bendahara') ORDER BY (id IN (SELECT spj_id FROM audit)), bulan DESC, id DESC LIMIT 1", (k,)).fetchone()
            if r:
                c.execute("DELETE FROM temuan WHERE spj_id=?", (r["id"],)); c.execute("DELETE FROM audit WHERE spj_id=?", (r["id"],))
                c.execute("UPDATE spj SET status=?, no_sp2d=NULL, tgl_aju=? WHERE id=?", (tahap, f"{tahun}-{bulan_ini:02d}-{10 if tahap == 'ppk' else 15}T10:00:00", r["id"]))
    # ---------- data nyata: SPJ GU I Bag. Perencanaan & Keuangan (hasil OCR) sebagai draf bendahara
    mpk = []
    for nm in MP_PK:
        c.execute("INSERT INTO monalisa(opd,nama,nilai,fisik,keu,sumber) VALUES('PK',?,0,NULL,NULL,'contoh')", (nm,)); mpk.append(c.execute("SELECT last_insert_rowid()").fetchone()[0])
    gu = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "gu1.json")
    if os.path.exists(gu):
        tr = json.load(open(gu, encoding="utf-8"))["transaksi"]
        for t in tr:
            sid = f"GUI-{t['no']:03d}"
            docs = [{"n": d["n"], "s": "ok" if d["hal"] else "kosong"} for d in t["docs"]]
            files = {str(i): {"name": f"{t['gu']}.pdf · hlm {d['hal'][0]}" + (f"–{d['hal'][1]}" if d["hal"][1] > d["hal"][0] else ""), "size": 0, "type": "application/pdf",
                              "src": f"dokumen/GU/{t['gu']}.pdf", "page": d["hal"][0]} for i, d in enumerate(t["docs"]) if d["hal"]}
            data = {"pptk": "Bendahara Pengeluaran Pembantu", "docs": docs, "cek": [False] * CEKN[t["j"]], "nk": "", "files": files}
            c.execute("INSERT INTO spj(id,opd,mp_id,jenis,bulan,nilai,uraian,bku,tgl,kode,penerima,status,sumber,gu,data,dibuat,diubah) VALUES(?,?,?,?,?,?,?,?,?,?,?,'draf','gu',?,?,?,?)",
                      (sid, "PK", mpk[0 if t["j"] == "PDGU" else 1], t["j"], t.get("bulan") or 1, t.get("nilai") or 0, t.get("uraian") or "Uraian tidak terbaca",
                       str(t.get("bku") or ""), t.get("tgl") or "", t.get("kode") or "", t.get("penerima") or "", t["gu"], json.dumps(data, ensure_ascii=False), now, now))
        for mid in mpk:
            c.execute("UPDATE monalisa SET nilai=(SELECT COALESCE(SUM(nilai),0) FROM spj WHERE mp_id=?) WHERE id=?", (mid, mid))
    # ---------- PKPT 2026
    for r in PKPT:
        real = 100 if r[4] < bulan_ini else int((bulan_ini - r[3] + 0.5) / (r[4] - r[3] + 1) * 100) if r[3] <= bulan_ini else 0
        c.execute("INSERT INTO pkpt(kegiatan,jenis,objek,m1,m2,hari,anggaran,pelaksana,risiko,realisasi,catatan) VALUES(?,?,?,?,?,?,?,?,?,?,?)", r + [max(0, min(100, real)), ""])
    # ---------- agenda & surat tugas (7 hari ke depan)
    AG = [["Pengawasan bulanan SPJ melalui e-Audit", "Kantor Inspektorat (daring)", "Dinas PUPR", "Inspektur Pembantu Wilayah I", "Tim Irban I"],
          ["Probity audit paket rehabilitasi jalan kabupaten", "Lokasi pekerjaan, Kec. Andoolo", "Dinas PUPR", "Inspektur Pembantu Wilayah II", "Tim Irban II"],
          ["Reviu RKA Tahun Anggaran 2027", "Ruang rapat BKAD", "BKAD", "Inspektur Pembantu Wilayah II", "Tim Irban II"],
          ["Asistensi APBDes (pemeriksaan hasil asistensi kecamatan)", "Kantor Inspektorat (melalui SIMPEL DESA)", "Kecamatan Konda", "Inspektur Pembantu Wilayah I", "Tim Irban I"],
          ["Entry meeting audit kinerja", "Aula Dinas Kesehatan", "Dinas Kesehatan", "Inspektur Pembantu Wilayah I", "Tim Irban I"],
          ["Rapat koordinasi pemenuhan indikator MCP KPK", "Ruang rapat Inspektorat", "Seluruh OPD", "Inspektur Daerah", "Sekretariat"],
          ["Uji petik SPJ GU Bagian Perencanaan dan Keuangan", "Sekretariat Daerah", "Bag. Perencanaan & Keuangan Setda", "Inspektur Pembantu Wilayah II", "Tim Irban II"]]
    base = datetime.date.today(); nst = 600
    for d in range(10):
        hari = base + datetime.timedelta(days=d)
        if hari.weekday() == 6: continue
        for k, jam in ((d, "09.00"), (d + 3, "13.30")) if d % 2 == 0 else ((d, "09.00"),):
            a = AG[k % len(AG)]; nst += 1
            c.execute("INSERT INTO agenda(tgl,jam,acara,tempat,objek,pj,pic,no_st,dasar,tim,lama) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      (hari.isoformat(), jam, a[0], a[1], a[2], a[3], a[4], f"700.1/{nst}/INSP/{tahun}",
                       "Keputusan Bupati Konawe Selatan Nomor 700.1/549/2026 tentang PKPT Berbasis Risiko Tahun Anggaran 2026",
                       json.dumps([{"nama": a[3], "peran": "Penanggung Jawab"}, {"nama": "Auditor Ahli Muda 1", "peran": "Ketua Tim"}, {"nama": "Auditor Ahli Pertama 2", "peran": "Anggota"}]), 1))
    c.execute("INSERT INTO log(waktu,user,peran,aksi,objek,detail) VALUES(?,?,?,?,?,?)", (now, "Sistem", "", "Data awal dibuat", "Sistem", "Akun uji coba: kata sandi " + SANDI_AWAL))
