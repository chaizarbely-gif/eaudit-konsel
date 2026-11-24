"""Audit awal otomatis: memeriksa SPJ terhadap aturan penatausahaan dan ketaatan (kriteria dari JDIH).
Hasil berupa DRAF temuan (tabel praaudit) yang wajib direviu auditor sebelum menjadi temuan resmi.
tingkat: 'temuan' = bukti cukup dari data; 'cek' = indikasi, perlu dicek auditor (mis. data OCR meragukan)."""
import json, re, collections

def migrasi(c):
    c.execute("""CREATE TABLE IF NOT EXISTS praaudit(id INTEGER PRIMARY KEY, spj_id TEXT, opd TEXT, aturan TEXT, kategori TEXT, tingkat TEXT,
        judul TEXT, kondisi TEXT, kriteria TEXT, jdih_id INTEGER, akibat TEXT, rekomendasi TEXT, nilai INTEGER DEFAULT 0, bukti TEXT,
        status TEXT DEFAULT 'baru', temuan_id INTEGER, reviu_oleh TEXT, reviu_tgl TEXT, catatan TEXT, dibuat TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS tarif(id INTEGER PRIMARY KEY, kelompok TEXT, uraian TEXT, satuan TEXT, nilai INTEGER,
        jdih_id INTEGER, halaman INTEGER, terverifikasi INTEGER DEFAULT 0, kunci TEXT)""")
    c.execute("CREATE TABLE IF NOT EXISTS dpa(id INTEGER PRIMARY KEY, opd TEXT, tahun INTEGER, kode TEXT, kunci TEXT, uraian TEXT, pagu INTEGER, halaman INTEGER)")

# ------------------------------------------------------------------ bantu
def rp(v): return "Rp" + f"{int(v or 0):,}".replace(",", ".")
def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())
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

def a_rekening(c, s, d, ctx):
    """P4: kode rekening tidak sesuai jenis belanja (perjalanan dinas harus 5.1.02.04; DPA bila tersedia)."""
    k = (s["kode"] or "").replace(" ", "")
    out = []
    dpa = ctx["dpa"].get(s["opd"])
    if dpa and k and norm(k) not in dpa:
        out.append(hasil(s, "P4a", "Penatausahaan", "cek", "Kode rekening tidak tercantum dalam DPA",
                         f"Kode rekening {k} pada SPJ {s['id']} tidak ditemukan dalam DPA SKPD (kemungkinan salah tulis atau salah baca OCR).",
                         ref(c, *PERMENDAGRI77), "belanja dibebankan pada kode rekening yang tercantum dalam DPA SKPD.",
                         "Realisasi belanja per rekening berpotensi tidak akurat.", "Bendahara pengeluaran agar menyesuaikan kode rekening dengan DPA.", 0, hlm(d, "Tanda Bukti Kas")))
    if jenis_efektif(s) == "PDGU" and k and not k.startswith("5.1.02.04"):
        nm = dpa.get(norm(k)) if dpa else None
        out.append(hasil(s, "P4", "Penatausahaan", "cek", "Belanja perjalanan dinas dibebankan pada rekening selain Belanja Perjalanan Dinas",
                         f"SPJ {s['id']} berupa perjalanan dinas senilai {rp(s['nilai'])} dibebankan pada kode rekening {k}" + (f" ({nm})" if nm else "") + ", bukan kelompok 5.1.02.04 (Belanja Perjalanan Dinas).",
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

def a_rincian(c, s, d, ctx):
    """P6/P7/K1: dari hasil ekstraksi rincian biaya (OCR): selisih total, transport ganda dalam rincian, tarif di atas SHS."""
    e = d.get("ekstrak") or {}; out = []
    items = e.get("rincian") or []
    if not items: return out
    tot = sum(i["jumlah"] for i in items)
    if e.get("total") and abs(e["total"] - s["nilai"]) >= 1000:
        out.append(hasil(s, "P6", "Penatausahaan", "cek", "Jumlah rincian biaya berbeda dengan nilai Tanda Bukti Kas",
                         f"Total rincian biaya perjalanan SPJ {s['id']} {rp(e['total'])}, sedangkan Tanda Bukti Kas {rp(s['nilai'])} (selisih {rp(abs(e['total'] - s['nilai']))}).",
                         ref(c, *PERMENDAGRI77), "jumlah yang dibayarkan sesuai dengan rincian biaya yang dipertanggungjawabkan.",
                         "Berpotensi kelebihan/kekurangan pembayaran.", "Bendahara pengeluaran agar menyesuaikan Tanda Bukti Kas dengan rincian biaya.",
                         abs(e["total"] - s["nilai"]), hlm(d, "Rincian Biaya Perjalanan")))
    trans = [i for i in items if i.get("pos") == "transport"]
    if len(trans) > 1:
        lebih = sum(i["jumlah"] for i in trans) - max(i["jumlah"] for i in trans)
        out.append(hasil(s, "P7", "Penatausahaan", "cek", "Indikasi biaya transport dibayar ganda",
                         f"Rincian biaya SPJ {s['id']} memuat {len(trans)} komponen transport ({'; '.join(i['uraian'] + ' ' + rp(i['jumlah']) for i in trans)}). Pastikan bukan pembayaran ganda atas rute yang sama; potensi kelebihan {rp(lebih)}.",
                         ref(c, *PERMENDAGRI77), "biaya transport perjalanan dinas dibayarkan sesuai perjalanan yang benar-benar dilaksanakan.",
                         "Kelebihan pembayaran biaya transport.", "Bendahara pengeluaran agar menyetorkan kelebihan pembayaran ke Kas Daerah.", lebih, hlm(d, "Rincian Biaya Perjalanan")))
    tujuan = next((i["tujuan"] for i in items if i.get("tujuan")), None)
    for i in items:
        t = ctx["tarif"].get(f"{i.get('pos')}|{norm(i.get('tujuan') or tujuan)}")
        if not t: continue
        if i.get("pos") == "penginapan" and i.get("persen"):  # penginapan tanpa bukti hotel: persentase x tarif x malam
            batas = t["nilai"] * i["persen"] // 100
            malam = round(i["jumlah"] / batas) if batas else 0
            if malam and i["jumlah"] > batas * malam: i["satuan_nilai"], i["vol"] = i["jumlah"] // malam, malam
            else: continue
            t = dict(t, nilai=batas, uraian=f"{i['persen']}% x {t['uraian']}")
        if i.get("satuan_nilai") and i["satuan_nilai"] > t["nilai"]:
            n_lebih = (i["satuan_nilai"] - t["nilai"]) * (i.get("vol") or 1)
            out.append(hasil(s, "K1", "Ketaatan", "temuan" if t["terverifikasi"] else "cek", f"{i.get('pos', 'Biaya').capitalize()} melebihi Standar Harga Satuan",
                             f"SPJ {s['id']}: {i.get('uraian') or i.get('pos')} dibayar {rp(i['satuan_nilai'])}/{t['satuan']}, melebihi SHS {rp(t['nilai'])} ({t['uraian']}), kelebihan {rp(n_lebih)}.",
                             (t["jdih_id"], ref(c, *SHS2026)[1]), f"{t['uraian']} paling tinggi {rp(t['nilai'])} per {t['satuan']} (lampiran hlm {t['halaman']})." + ("" if t["terverifikasi"] else " [tarif hasil OCR, belum diverifikasi]"),
                             "Kelebihan pembayaran.", "Bendahara pengeluaran agar menyetorkan kelebihan pembayaran ke Kas Daerah.", n_lebih, hlm(d, "Rincian Biaya Perjalanan")))
    return out

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
    e = d.get("ekstrak") or {}; r = rentang(e); nm = norm(e.get("nama") or s["penerima"])
    if not r or len(nm) < 6: return []
    lain = [(i, rr) for i, n2, rr in ctx["perjalanan"] if i != s["id"] and n2 == nm and rr[0] <= r[1] and r[0] <= rr[1]]
    if not lain: return []
    fm = lambda x: f"{x[0]:%d/%m/%Y}–{x[1]:%d/%m/%Y}"
    return [hasil(s, "P8", "Penatausahaan", "cek", "Perjalanan dinas pada tanggal yang beririsan",
                  f"{e.get('nama') or s['penerima']} dibayar perjalanan dinas SPJ {s['id']} ({fm(r)}) dan juga SPJ {', '.join(f'{i} ({fm(rr)})' for i, rr in lain)} pada tanggal yang beririsan.",
                  ref(c, *PERMENDAGRI77), "biaya perjalanan dinas hanya dibayarkan untuk perjalanan yang benar-benar dilaksanakan; seseorang tidak dapat melaksanakan dua perjalanan dinas pada waktu yang sama.",
                  "Berpotensi kelebihan pembayaran uang harian/transport.", "Bendahara pengeluaran agar menjelaskan; bila terbukti, menyetorkan kelebihan pembayaran ke Kas Daerah.", 0, hlm(d, "Rincian Biaya Perjalanan"))]

ATURAN = [a_kelengkapan, a_data_tbk, a_rekening, a_ganda_tbk, a_rincian, a_tumpang]
DAFTAR = {"P1": "Kelengkapan dokumen wajib SPJ", "P2": "Unsur Tanda Bukti Kas", "P4": "Kesesuaian kode rekening dengan jenis belanja", "P4a": "Kode rekening tercantum dalam DPA",
          "P5": "Pembayaran ganda antar-SPJ", "P6": "Kesesuaian rincian biaya dengan Tanda Bukti Kas", "P7": "Transport ganda dalam rincian biaya", "P8": "Perjalanan dinas tumpang tindih (orang & tanggal sama)", "K1": "Tarif tidak melebihi Standar Harga Satuan"}

def periksa(c, spj_rows):
    """Jalankan semua aturan atas daftar baris SPJ; kembalikan daftar draf temuan."""
    semua = c.execute("SELECT id, opd, penerima, nilai, uraian, tgl, kode FROM spj").fetchall()
    kunci = collections.defaultdict(list)
    for x in semua: kunci[(x["opd"], norm(x["penerima"]), x["nilai"], norm(x["uraian"])[:60])].append(x["id"])
    dpa = collections.defaultdict(dict)
    for r in c.execute("SELECT opd, kunci, uraian FROM dpa"): dpa[r["opd"]][r["kunci"]] = r["uraian"]
    tarif = {r["kunci"]: dict(r) for r in c.execute("SELECT * FROM tarif WHERE kunci IS NOT NULL")}
    perj = []
    for x in c.execute("SELECT id, opd, penerima, data FROM spj"):
        e = json.loads(x["data"] or "{}").get("ekstrak") or {}; r = rentang(e)
        if r: perj.append((x["id"], norm(e.get("nama") or x["penerima"]), r))
    ctx = {"kunci": kunci, "dpa": dpa, "tarif": tarif, "info": {x["id"]: x for x in semua}, "perjalanan": perj}
    out = []
    for s in spj_rows:
        d = json.loads(s["data"] or "{}")
        for f in ATURAN: out += f(c, s, d, ctx)
    return out
