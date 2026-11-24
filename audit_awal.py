"""Audit awal otomatis: memeriksa SPJ terhadap aturan penatausahaan dan ketaatan (kriteria dari JDIH).
Hasil berupa DRAF temuan (tabel praaudit) yang wajib direviu auditor sebelum menjadi temuan resmi.
tingkat: 'temuan' = bukti cukup dari data; 'cek' = indikasi, perlu dicek auditor (mis. data OCR meragukan)."""
import json, re, collections
import tarif_shs2026 as T

def migrasi(c):
    c.execute("""CREATE TABLE IF NOT EXISTS praaudit(id INTEGER PRIMARY KEY, spj_id TEXT, opd TEXT, aturan TEXT, kategori TEXT, tingkat TEXT,
        judul TEXT, kondisi TEXT, kriteria TEXT, jdih_id INTEGER, akibat TEXT, rekomendasi TEXT, nilai INTEGER DEFAULT 0, bukti TEXT,
        status TEXT DEFAULT 'baru', temuan_id INTEGER, reviu_oleh TEXT, reviu_tgl TEXT, catatan TEXT, dibuat TEXT)""")
    # pegawai: nama & jabatan pelaksana dari Surat Tugas (untuk tingkatan tarif penginapan/representasi)
    c.execute("CREATE TABLE IF NOT EXISTS pegawai(kunci TEXT PRIMARY KEY, nama TEXT, jabatan TEXT, sumber TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS dpa(id INTEGER PRIMARY KEY, opd TEXT, tahun INTEGER, kode TEXT, kunci TEXT, uraian TEXT, pagu INTEGER, halaman INTEGER)")

# ------------------------------------------------------------------ bantu
def rp(v): return "Rp" + f"{int(v or 0):,}".replace(",", ".")
def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())
def kode_rek(s):
    """Normalkan kode rekening hasil OCR: 5.1.02.02.01.0004 -> 5.1.02.02.001.00004."""
    seg = [x for x in re.split(r"\.", re.sub(r"[^\d.]", "", s or "")) if x]
    if len(seg) != 6: return re.sub(r"\s", "", s or "")
    return ".".join(x.zfill(w)[-w:] for x, w in zip(seg, (1, 1, 2, 2, 3, 5)))
def spasi_nama(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s or ""); s = re.sub(r"(/)(\S)", r"\1 \2", s)
    return re.sub(r"\s+", " ", s).strip()
def ref(c, jenis, nomor, tahun):
    r = c.execute("SELECT id, jenis, nomor, tahun, judul FROM jdih WHERE jenis=? AND nomor=? AND tahun=?", (jenis, str(nomor), int(tahun))).fetchone()
    return (r["id"], f"{r['jenis']} Nomor {r['nomor']} Tahun {r['tahun']} tentang {r['judul']}") if r else (None, f"{jenis} Nomor {nomor} Tahun {tahun}")

PERMENDAGRI77 = ("Peraturan Menteri Dalam Negeri", "77", 2020)
PP12 = ("Peraturan Pemerintah", "12", 2019)
SHS2026 = ("Peraturan Bupati", "57", 2025)
WAJIB = {"PDGU": ["Tanda Bukti Kas", "Surat Tugas", "SPPD", "Laporan Hasil Perjalanan", "Rincian Biaya Perjalanan"], "BLGU": ["Tanda Bukti Kas"]}

def hasil(spj, aturan, kategori, tingkat, judul, kondisi, kriteria_ref, kriteria_isi, akibat, rekomendasi, nilai=0, bukti=""):
    return {"spj_id": spj["id"], "opd": spj["opd"], "aturan": aturan, "kategori": kategori, "tingkat": tingkat, "judul": judul, "kondisi": kondisi,
            "jdih_id": kriteria_ref[0], "kriteria": f"{kriteria_ref[1]}: {kriteria_isi}", "akibat": akibat, "rekomendasi": rekomendasi, "nilai": int(nilai or 0), "bukti": bukti}

def hlm(d, nama):
    for k, x in enumerate(d.get("docs", [])):
        if x.get("n") == nama:
            f = (d.get("files") or {}).get(str(k))
            if f and f.get("page"): return f"{f.get('src', '').split('/')[-1]} hlm {f['page']}"
    return ""

# ------------------------------------------------------------------ aturan
BUKAN_PD = re.compile(r"^\s*(belanja|makan|minum|bahan|cetak|alat|pembelian|honor|jasa|sewa|bbm|bahan bakar)", re.I)
def jenis_efektif(s):
    """Jenis belanja yang dipakai aturan: hasil OCR bisa salah mengelompokkan (mis. makan-minum dianggap perjalanan dinas
    karena ada surat undangan). Perjalanan dinas = rekening 5.1.02.04, atau jenis PDGU yang uraiannya bukan belanja barang/jasa."""
    k = (s["kode"] or "").replace(" ", "")
    if k.startswith("5.1.02.04"): return "PDGU"
    if s["jenis"] == "PDGU" and not BUKAN_PD.search(s["uraian"] or ""): return "PDGU"
    return "BLGU"

def a_kelengkapan(c, s, d, ctx):
    """P1: dokumen wajib SPJ tidak tersedia."""
    docs = d.get("docs", []); files = d.get("files") or {}
    ada = {x.get("n") for k, x in enumerate(docs) if x.get("s") != "kosong" and str(k) in files}
    kurang = [n for n in WAJIB.get(jenis_efektif(s), []) if n not in ada]
    if not kurang: return []
    # halaman yang belum dikenali OCR bisa jadi dokumen yang "hilang" -> perlu dicek, bukan temuan
    lain = [f"{files[str(k)].get('src', '').split('/')[-1]} hlm {files[str(k)].get('page')}" for k, x in enumerate(docs) if x.get("n") == "Dokumen pendukung lain" and str(k) in files]
    tk = "cek" if lain else "temuan"
    return [hasil(s, "P1", "Penatausahaan", tk, f"Bukti pertanggungjawaban {jenis_efektif(s) == 'PDGU' and 'perjalanan dinas' or 'belanja'} tidak lengkap",
                  f"SPJ {s['id']} ({s['uraian'][:90]}) senilai {rp(s['nilai'])} tidak dilengkapi: {', '.join(kurang)}." + (f" Periksa {', '.join(lain)} yang belum dikenali sistem; kemungkinan dokumen tersebut." if lain else ""),
                  ref(c, *PERMENDAGRI77), "pertanggungjawaban penggunaan uang persediaan/ganti uang harus didukung bukti pengeluaran yang lengkap dan sah.",
                  "Pengeluaran belum dapat diyakini kewajaran dan keabsahannya.",
                  f"Bendahara pengeluaran agar melengkapi {', '.join(kurang)} dan PPK-SKPD meneliti kelengkapan SPJ sebelum disahkan.", s["nilai"], hlm(d, "Tanda Bukti Kas"))]

def a_data_tbk(c, s, d, ctx):
    """P2: unsur Tanda Bukti Kas tidak terbaca/kosong (tanggal, penerima, kode rekening)."""
    kosong = [n for n, v in (("tanggal", s["tgl"]), ("penerima", s["penerima"]), ("kode rekening", s["kode"])) if not v]
    if not kosong: return []
    return [hasil(s, "P2", "Penatausahaan", "cek", "Unsur Tanda Bukti Kas tidak lengkap",
                  f"Tanda Bukti Kas SPJ {s['id']} tidak memuat/terbaca {', '.join(kosong)}.", ref(c, *PERMENDAGRI77),
                  "bukti pengeluaran memuat tanggal, uraian, kode rekening, jumlah, dan tanda tangan penerima.", "Bukti kas berpotensi tidak sah.",
                  "Bendahara pengeluaran agar melengkapi unsur Tanda Bukti Kas.", 0, hlm(d, "Tanda Bukti Kas"))]

COCOK_REK = [  # (kata pada uraian, kata yang harus ada pada nama rekening, label rekening yang sesuai)
    (("bahanbakar", "bbm", "pertalite", "solar", "pertamax"), ("bahanbakar",), "Belanja Bahan Bakar dan Pelumas"),
    (("makanminum", "makanandanminuman", "konsumsi", "snack", "nasikotak"), ("makanan",), "Belanja Makanan dan Minuman"),
    (("alattulis", "atk"), ("alattulis",), "Belanja Alat Tulis Kantor"),
    (("bahancetak", "penggandaan", "fotokopi", "cetak"), ("cetak", "penggandaan"), "Belanja Bahan Cetak/Penggandaan"),
    (("sukucadang", "servis", "service"), ("sukucadang", "pemeliharaan"), "Belanja Suku Cadang/Pemeliharaan"),
]

def a_rekening(c, s, d, ctx):
    """P4: kode rekening tidak sesuai jenis belanja (perjalanan dinas harus 5.1.02.04; DPA bila tersedia)."""
    k = kode_rek(s["kode"])
    out = []
    dpa = ctx["dpa"].get(s["opd"])
    nm = dpa.get(k) if dpa else None
    asli = (s["kode"] or "").strip(); tulis = asli + (f" (dibaca {k})" if asli.replace(" ", "") != k else "")
    p4 = jenis_efektif(s) == "PDGU" and k and not k.startswith("5.1.02.04")
    if dpa and k and not nm and not p4:
        # saran rekening DPA yang sesuai uraian
        saran = next((f"{kk} ({u})" for kata, harus, _ in COCOK_REK if any(x in norm(s["uraian"]) for x in kata)
                      for kk, u in dpa.items() if any(h in norm(u) for h in harus)), None)
        out.append(hasil(s, "P4a", "Penatausahaan", "cek", "Kode rekening tidak tercantum dalam DPA",
                         f"Kode rekening {tulis} pada Tanda Bukti Kas SPJ {s['id']} ({s['uraian'][:70]}, {rp(s['nilai'])}) tidak tercantum dalam DPA SKPD Tahun {T.TAHUN}." + (f" Rekening DPA yang sesuai uraian: {saran}." if saran else ""),
                         ref(c, *PERMENDAGRI77), "belanja dibebankan pada kode rekening yang tercantum dalam DPA SKPD.",
                         "Realisasi belanja per rekening tidak akurat dan berpotensi melampaui pagu.", "Bendahara pengeluaran agar menyesuaikan kode rekening dengan DPA; PPK-SKPD menguji kode rekening sebelum SPJ disahkan.", s["nilai"], hlm(d, "Tanda Bukti Kas")))
    # uraian belanja tidak sesuai nama rekening DPA (mis. BBM dibebankan ke rekening makan-minum)
    ur = norm(s["uraian"])
    if nm and jenis_efektif(s) == "BLGU":
        for kata, harus, label in COCOK_REK:
            if any(x in ur for x in kata) and not any(h in norm(nm) for h in harus):
                out.append(hasil(s, "P4c", "Penatausahaan", "cek", "Uraian belanja tidak sesuai nama rekening",
                                 f"SPJ {s['id']}: belanja \"{s['uraian'][:80]}\" senilai {rp(s['nilai'])} dibebankan pada {k} ({nm}), bukan rekening {label}.",
                                 ref(c, *PERMENDAGRI77), "belanja direalisasikan pada rekening DPA yang sesuai dengan jenis belanjanya.",
                                 "Realisasi anggaran per rekening tidak menggambarkan keadaan sebenarnya; pengeluaran berpotensi dibebankan ganda pada rekening lain.",
                                 "PPK-SKPD agar menguji kesesuaian uraian belanja dengan rekening DPA sebelum SPJ disahkan.", s["nilai"], hlm(d, "Tanda Bukti Kas")))
                break
    # perjalanan ke kecamatan (dalam kota) dibebankan ke rekening "luar kota", atau sebaliknya
    e = d.get("ekstrak") or {}; lok = T.lokasi(next((i["tujuan"] for i in e.get("rincian") or [] if i.get("tujuan")), None))
    if nm and lok and jenis_efektif(s) == "PDGU":
        dalam = T.wilayah_harian(lok) == "dalamkota"; nmk = norm(nm)
        if (dalam and "luarkota" in nmk) or (not dalam and "dalamkota" in nmk):
            out.append(hasil(s, "P4b", "Penatausahaan", "cek", "Rekening perjalanan dinas tidak sesuai jenis perjalanan",
                             f"SPJ {s['id']}: perjalanan dinas ke {lok.title()} ({'dalam kota / dalam wilayah Kabupaten' if dalam else 'luar kota'}) dibebankan pada {k} ({nm}).",
                             ref(c, *PERMENDAGRI77), "belanja direalisasikan pada rekening DPA yang sesuai dengan jenis belanjanya.",
                             "Realisasi belanja perjalanan dinas dalam kota dan luar kota tidak menggambarkan keadaan sebenarnya.",
                             "PPK-SKPD agar meneliti kesesuaian rekening dengan jenis perjalanan dinas sebelum SPJ disahkan.", s["nilai"], hlm(d, "Tanda Bukti Kas")))
    if p4:
        pd = [f"{kk} ({u})" for kk, u in (dpa or {}).items() if kk.startswith("5.1.02.04")]
        out.append(hasil(s, "P4", "Penatausahaan", "cek", "Belanja perjalanan dinas dibebankan pada rekening selain Belanja Perjalanan Dinas",
                         f"SPJ {s['id']} berupa perjalanan dinas senilai {rp(s['nilai'])} dibebankan pada kode rekening {tulis}" + (f" ({nm})" if nm else (" yang tidak tercantum dalam DPA" if dpa else "")) + ", bukan kelompok 5.1.02.04 (Belanja Perjalanan Dinas)."
                         + (f" Rekening perjalanan dinas dalam DPA: {'; '.join(pd)}." if pd else ""),
                         ref(c, *PERMENDAGRI77), "belanja dianggarkan dan direalisasikan sesuai klasifikasi, kodefikasi, dan nomenklatur rekening dalam DPA.",
                         "Realisasi belanja perjalanan dinas dan belanja barang/jasa tidak menggambarkan keadaan sebenarnya.",
                         "PPK-SKPD agar meneliti kesesuaian kode rekening dengan jenis belanja sebelum SPJ disahkan.", s["nilai"], hlm(d, "Tanda Bukti Kas")))
    return out

def a_ganda_tbk(c, s, d, ctx):
    """P5: indikasi pembayaran ganda antar-SPJ (penerima, nilai, dan uraian sama)."""
    kunci = (s["opd"], norm(s["penerima"]), s["nilai"], norm(s["uraian"])[:60])
    kembar = [x for x in ctx["kunci"][kunci] if x != s["id"]]
    if not kembar or not s["penerima"]: return []
    inf = ctx["info"]; det = lambda i: f"{i} (tgl {inf[i]['tgl'] or '-'}, rek. {inf[i]['kode'] or '-'})"
    return [hasil(s, "P5", "Penatausahaan", "cek", "Indikasi pembayaran ganda",
                  f"SPJ {det(s['id'])} memiliki penerima ({s['penerima']}), nilai ({rp(s['nilai'])}), dan uraian yang sama dengan SPJ {', '.join(det(k) for k in kembar)}.",
                  ref(c, *PP12), "setiap pengeluaran harus didukung bukti yang lengkap dan sah; pengeluaran yang sama tidak dapat dibayar lebih dari satu kali.",
                  "Berpotensi terjadi kelebihan pembayaran.", "Bendahara pengeluaran agar menjelaskan; bila terbukti ganda, menyetorkan kelebihan pembayaran ke Kas Daerah.", s["nilai"], hlm(d, "Tanda Bukti Kas"))]

def kunci_nama(s): return norm(s)[:10]

def pelaku(c, ctx, nama):
    """Jabatan & tingkat pelaksana dari tabel pegawai (hasil Surat Tugas), dicocokkan dengan 10 huruf awal nama."""
    p = ctx["pegawai"].get(kunci_nama(nama))
    return (p["jabatan"], T.tingkat(p["jabatan"]), p["sumber"]) if p else (None, None, None)

def k1(c, s, d, judul, kondisi, isi, v, lebih, yakin=True):
    """Draf ketaatan tarif SHS. 'temuan' hanya bila tarif sudah dicocokkan dengan gambar pindaian, rincian sama dengan TBK, dan tidak ada keraguan."""
    e = d.get("ekstrak") or {}
    cocok = e.get("total") and abs(e["total"] - s["nilai"]) < 1000
    tk = "temuan" if (v and cocok and yakin) else "cek"
    return hasil(s, "K1", "Ketaatan", tk, judul, kondisi, (ref(c, *SHS2026)[0], ref(c, *SHS2026)[1]),
                 isi + ("" if v else " [angka tarif hasil OCR, belum dicocokkan dengan naskah]"), "Kelebihan pembayaran belanja perjalanan dinas.",
                 "Pelaksana perjalanan dinas agar menyetorkan kelebihan pembayaran ke Rekening Kas Umum Daerah; Bendahara Pengeluaran agar menguji rincian biaya terhadap SHS sebelum membayar.",
                 lebih, hlm(d, "Rincian Biaya Perjalanan"))

def a_rincian(c, s, d, ctx):
    """P6/P7/K1 dari ekstraksi rincian biaya (OCR): selisih total, transport ganda dalam rincian, tarif di atas SHS 2026."""
    e = d.get("ekstrak") or {}; out = []
    items = e.get("rincian") or []
    if not items: return out
    if e.get("total") and abs(e["total"] - s["nilai"]) >= 1000:
        out.append(hasil(s, "P6", "Penatausahaan", "cek", "Jumlah rincian biaya berbeda dengan nilai Tanda Bukti Kas",
                         f"Total rincian biaya perjalanan SPJ {s['id']} {rp(e['total'])}, sedangkan Tanda Bukti Kas {rp(s['nilai'])} (selisih {rp(abs(e['total'] - s['nilai']))}).",
                         ref(c, *PERMENDAGRI77), "jumlah yang dibayarkan sesuai dengan rincian biaya yang dipertanggungjawabkan.",
                         "Berpotensi kelebihan/kekurangan pembayaran.", "Bendahara pengeluaran agar menyesuaikan Tanda Bukti Kas dengan rincian biaya.",
                         abs(e["total"] - s["nilai"]), hlm(d, "Rincian Biaya Perjalanan")))
    trans = [i for i in items if i.get("pos") == "transport" and "tiket" not in i["uraian"].lower()]
    if len(trans) > 1:
        lebih = sum(i["jumlah"] for i in trans) - max(i["jumlah"] for i in trans)
        out.append(hasil(s, "P7", "Penatausahaan", "cek", "Indikasi biaya transport dibayar ganda",
                         f"Rincian biaya SPJ {s['id']} memuat {len(trans)} komponen transport ({'; '.join(i['uraian'] + ' ' + rp(i['jumlah']) for i in trans)}). Pastikan bukan pembayaran ganda atas rute yang sama; potensi kelebihan {rp(lebih)}.",
                         ref(c, *PERMENDAGRI77), "biaya transport perjalanan dinas dibayarkan sesuai perjalanan yang benar-benar dilaksanakan.",
                         "Kelebihan pembayaran biaya transport.", "Bendahara pengeluaran agar menyetorkan kelebihan pembayaran ke Kas Daerah.", lebih, hlm(d, "Rincian Biaya Perjalanan")))
    # ---------- K1: tarif SHS 2026
    tuj = next((i["tujuan"] for i in items if i.get("tujuan")), None); lok = T.lokasi(tuj)
    hari = next((i["vol"] for i in items if i.get("pos") == "harian" and i.get("vol")), None)
    nama = e.get("nama") or s["penerima"]; jab, tg, sumber_jab = pelaku(c, ctx, nama)
    ket_jab = f"{nama} ({jab}; sumber: {sumber_jab})" if jab else f"{nama} (jabatan tidak ditemukan di Surat Tugas yang terbaca)"
    if not lok: return out
    for i in items:
        p = i.get("pos")
        if p == "transport" and "tiket" not in i["uraian"].lower() and lok in T.TRANSPORT and len(trans) == 1:
            n, h, v, ur = T.TRANSPORT[lok]
            if i["jumlah"] > n:
                out.append(k1(c, s, d, "Biaya transport melebihi Standar Harga Satuan", f"SPJ {s['id']}: transport ke {tuj} dibayar {rp(i['jumlah'])} kepada {nama}, melebihi SHS {rp(n)}; kelebihan {rp(i['jumlah'] - n)}.",
                              f"{ur}: paling tinggi {rp(n)} (Lampiran II hlm {h}).", v, i["jumlah"] - n))
        if p == "harian" and hari:
            w = T.wilayah_harian(lok)
            if w in T.HARIAN:
                n, h, v, ur = T.HARIAN[w]; per = i["jumlah"] // hari
                if per > n:
                    out.append(k1(c, s, d, "Uang harian melebihi Standar Harga Satuan", f"SPJ {s['id']}: uang harian {nama} ke {tuj} {rp(per)}/hari x {hari} hari, melebihi SHS {rp(n)}/hari; kelebihan {rp((per - n) * hari)}.",
                                  f"{ur}: paling tinggi {rp(n)} per orang per hari (Lampiran II hlm {h}).", v, (per - n) * hari))
        if p == "penginapan" and i.get("persen") and lok in T.PENGINAPAN and hari:
            malam = max(1, hari - 1); kol, h, v = T.PENGINAPAN[lok]; tarif = dict(zip(T.KOLOM, kol)); per = i["jumlah"] // malam; pr = i["persen"]
            if tg == "pelaksana" and tarif["es4"] == tarif["gol12"]: tg = "es4"  # golongan III dan I-II bertarif sama di kota ini
            if tg in tarif:
                batas = tarif[tg] * pr // 100
                if per > batas:
                    out.append(k1(c, s, d, "Biaya penginapan melebihi Standar Harga Satuan",
                                  f"SPJ {s['id']}: penginapan {pr}% untuk {ket_jab} di {tuj} dibayar {rp(per)}/malam x {malam} malam, sedangkan {pr}% x tarif {T.NAMA_KOLOM[tg]} {rp(tarif[tg])} = {rp(batas)}; kelebihan {rp((per - batas) * malam)}.",
                                  f"tanpa bukti hotel, biaya penginapan dibayar {pr}% dari tarif hotel kota tujuan sesuai tingkatan perjalanan dinas (Lampiran II hlm 26 butir 6 dan tarif hlm {h}).",
                                  v, (per - batas) * malam, yakin=True))
            else:  # tingkatan pelaksana tidak pasti: bandingkan dengan kolom tertinggi yang wajar (Eselon III) dan terendah (Eselon IV)
                b3, b4 = tarif["es3"] * pr // 100, tarif["es4"] * pr // 100
                if per > b4:
                    out.append(k1(c, s, d, "Biaya penginapan perlu diuji terhadap tingkatan pelaksana",
                                  f"SPJ {s['id']}: penginapan {pr}% untuk {ket_jab} di {tuj} dibayar {rp(per)}/malam x {malam} malam. Batas SHS: {rp(b4)} (Eselon IV/Gol III ke bawah) atau {rp(b3)} (Eselon III/Gol IV)."
                                  + (f" Melebihi kedua batas; kelebihan minimal {rp((per - b3) * malam)}." if per > b3 else " Kelebihan bila pelaksana Eselon IV/Gol III ke bawah: " + rp((per - b4) * malam) + "."),
                                  f"tanpa bukti hotel, biaya penginapan dibayar {pr}% dari tarif hotel kota tujuan sesuai tingkatan perjalanan dinas (Lampiran II hlm 26 butir 6 dan tarif hlm {h}).",
                                  v, (per - (b3 if per > b3 else b4)) * malam, yakin=False))
        if p == "representasi" and hari:
            w = "dalamkota" if T.wilayah_harian(lok) == "dalamkota" else "luarkota"; n, h, v, ur = T.REPRESENTASI[w]; per = i["jumlah"] // hari
            if tg and tg not in ("es1", "es2"):
                out.append(k1(c, s, d, "Uang representasi dibayarkan kepada pelaksana yang tidak berhak",
                              f"SPJ {s['id']}: uang representasi {rp(i['jumlah'])} dibayarkan kepada {ket_jab}.",
                              "uang representasi hanya diberikan kepada pejabat negara, pejabat daerah, pejabat eselon I, dan pejabat eselon II (Lampiran II hlm 27–28).", 0, i["jumlah"], yakin=False))
            elif per > n:
                out.append(k1(c, s, d, "Uang representasi melebihi Standar Harga Satuan", f"SPJ {s['id']}: uang representasi {nama} {rp(per)}/hari, melebihi SHS {rp(n)}/hari; kelebihan {rp((per - n) * hari)}.",
                              f"{ur}: paling tinggi {rp(n)} per hari (Lampiran II hlm {h}).", v, (per - n) * hari))
    return out

def a_konsisten(c, s, d, ctx):
    """P9: biaya transport ke tujuan yang sama dibayar berbeda antar-SPJ (mis. perjalanan 2 hari dibayar 2x transport)."""
    e = d.get("ekstrak") or {}; items = e.get("rincian") or []
    tr = [i for i in items if i.get("pos") == "transport" and "tiket" not in i["uraian"].lower()]
    lok = T.lokasi(next((i["tujuan"] for i in items if i.get("tujuan")), None))
    if len(tr) != 1 or not lok: return []
    lain = ctx["transport"].get(lok, {})
    murah = min(lain) if lain else None
    if not murah or tr[0]["jumlah"] <= murah: return []
    contoh = ", ".join(sorted(lain[murah])[:4])
    n, h, v, ur = T.TRANSPORT.get(lok, (None, None, 0, ""))
    return [hasil(s, "P9", "Ketaatan", "cek", "Biaya transport ke tujuan yang sama dibayar berbeda",
                  f"SPJ {s['id']}: transport {e.get('nama') or s['penerima']} ke {lok.title()} dibayar {rp(tr[0]['jumlah'])}, sedangkan pada SPJ {contoh} ke tujuan yang sama dibayar {rp(murah)}. Bila hanya satu kali perjalanan pergi-pulang, selisih {rp(tr[0]['jumlah'] - murah)} merupakan kelebihan pembayaran.",
                  ref(c, *PP12), "setiap pengeluaran harus didukung bukti yang lengkap dan sah mengenai hak yang diperoleh oleh pihak yang menagih" + (f"; SHS 2026 Lampiran II hlm {h}: {ur}." if ur else "."),
                  "Berpotensi kelebihan pembayaran biaya transport.", "Bendahara pengeluaran agar menguji jumlah perjalanan pergi-pulang pada SPPD; bila hanya satu kali, pelaksana menyetorkan selisihnya ke Kas Daerah.",
                  tr[0]["jumlah"] - murah, hlm(d, "Rincian Biaya Perjalanan"))]

def rentang(e):
    """Rentang tanggal perjalanan dari ekstrak rincian: tgl_akhir bila terbaca, bila tidak tgl_awal + (hari uang harian - 1)."""
    import datetime as dt
    if not e.get("tgl_awal"): return None
    a = dt.date.fromisoformat(e["tgl_awal"])
    if e.get("tgl_akhir"): b = dt.date.fromisoformat(e["tgl_akhir"])
    else: b = a + dt.timedelta(days=max(1, next((i["vol"] for i in e.get("rincian", []) if i.get("pos") == "harian" and i.get("vol")), 1)) - 1)
    return (a, b) if b >= a and (b - a).days < 60 else None

def a_tumpang(c, s, d, ctx):
    """P8: orang yang sama dibayar perjalanan dinas pada tanggal yang beririsan di SPJ lain."""
    e = d.get("ekstrak") or {}; r = rentang(e); nm = kunci_nama(e.get("nama") or s["penerima"])
    if not r or len(nm) < 6: return []
    lain = [(i, rr) for i, n2, rr in ctx["perjalanan"] if i != s["id"] and n2 == nm and rr[0] <= r[1] and r[0] <= rr[1]]
    if not lain: return []
    fm = lambda x: f"{x[0]:%d/%m/%Y}–{x[1]:%d/%m/%Y}"
    return [hasil(s, "P8", "Penatausahaan", "cek", "Perjalanan dinas pada tanggal yang beririsan",
                  f"{e.get('nama') or s['penerima']} dibayar perjalanan dinas SPJ {s['id']} ({fm(r)}) dan juga SPJ {', '.join(f'{i} ({fm(rr)})' for i, rr in lain)} pada tanggal yang beririsan.",
                  ref(c, *PERMENDAGRI77), "biaya perjalanan dinas hanya dibayarkan untuk perjalanan yang benar-benar dilaksanakan; seseorang tidak dapat melaksanakan dua perjalanan dinas pada waktu yang sama.",
                  "Berpotensi kelebihan pembayaran uang harian/transport.", "Bendahara pengeluaran agar menjelaskan; bila terbukti, menyetorkan kelebihan pembayaran ke Kas Daerah.", 0, hlm(d, "Rincian Biaya Perjalanan"))]

ATURAN = [a_kelengkapan, a_data_tbk, a_rekening, a_ganda_tbk, a_rincian, a_konsisten, a_tumpang]
DAFTAR = {"P1": "Kelengkapan dokumen wajib SPJ", "P2": "Unsur Tanda Bukti Kas", "P4": "Kesesuaian kode rekening dengan jenis belanja", "P4a": "Kode rekening tercantum dalam DPA", "P4b": "Rekening sesuai jenis perjalanan (dalam/luar kota)", "P4c": "Uraian belanja sesuai nama rekening DPA",
          "P5": "Pembayaran ganda antar-SPJ", "P6": "Kesesuaian rincian biaya dengan Tanda Bukti Kas", "P7": "Transport ganda dalam rincian biaya",
          "P8": "Perjalanan dinas tumpang tindih (orang & tanggal sama)", "P9": "Konsistensi biaya transport ke tujuan yang sama",
          "K1": "Transport, uang harian, penginapan, dan representasi sesuai SHS 2026 (Perbup 57/2025)"}

def periksa(c, spj_rows):
    """Jalankan semua aturan atas daftar baris SPJ; kembalikan daftar draf temuan."""
    semua = c.execute("SELECT id, opd, penerima, nilai, uraian, tgl, kode, data FROM spj").fetchall()
    kunci = collections.defaultdict(list)
    for x in semua: kunci[(x["opd"], norm(x["penerima"]), x["nilai"], norm(x["uraian"])[:60])].append(x["id"])
    dpa = collections.defaultdict(dict)
    for r in c.execute("SELECT opd, kunci, uraian FROM dpa"): dpa[r["opd"]][r["kunci"]] = r["uraian"]
    perj, transport = [], collections.defaultdict(lambda: collections.defaultdict(list))
    for x in semua:
        e = json.loads(x["data"] or "{}").get("ekstrak") or {}; r = rentang(e)
        if r: perj.append((x["id"], kunci_nama(e.get("nama") or x["penerima"]), r))
        it = e.get("rincian") or []; tr = [i for i in it if i.get("pos") == "transport" and "tiket" not in i["uraian"].lower()]
        lok = T.lokasi(next((i["tujuan"] for i in it if i.get("tujuan")), None))
        if lok and len(tr) == 1: transport[lok][tr[0]["jumlah"]].append(x["id"])
    pegawai = {r["kunci"]: dict(r) for r in c.execute("SELECT * FROM pegawai")}
    ctx = {"kunci": kunci, "dpa": dpa, "info": {x["id"]: x for x in semua}, "perjalanan": perj, "transport": transport, "pegawai": pegawai}
    out = []
    for s in spj_rows:
        d = json.loads(s["data"] or "{}")
        for f in ATURAN: out += f(c, s, d, ctx)
    return out
