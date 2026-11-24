"""Asisten AI e-Audit: OCR offline (RapidOCR) untuk mengenali jenis dokumen SPJ dan membaca Tanda Bukti Kas."""
import os, re, sys, time, threading
AI = False; AIERR = ""; OCR = None
LOCK = threading.Lock()
def _muat():
    global AI, AIERR, OCR, np, pymupdf
    try:
        try:
            import rapidocr_onnxruntime  # noqa
        except ImportError:
            for sp in (os.environ.get("EAUDIT_OCR_SITE", ""), "D:/ocr-kerja/venv/Lib/site-packages"):
                if sp and os.path.isdir(sp) and sp not in sys.path: sys.path.insert(0, sp)
        import numpy as np, pymupdf
        from rapidocr_onnxruntime import RapidOCR
        OCR = RapidOCR(); AI = True
    except Exception as e:
        AI = False; AIERR = str(e)
_muat()

K = lambda h: re.sub(r"[^a-z]", "", h.lower())
NAMA = {"TBK": "Tanda Bukti Kas", "ST": "Surat Tugas", "SPPD": "SPPD", "LAPORAN": "Laporan Hasil Perjalanan",
        "RINCIAN": "Rincian Biaya Perjalanan", "BUKTI": "Bukti transportasi/penginapan", "NOTA": "Nota/kuitansi pembelian",
        "UNDANGAN": "Undangan", "HADIR": "Daftar hadir", "LAIN": "Dokumen pendukung lain"}
BLN = ["januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember"]

def tipe(h):
    k = K(h)
    if "buktikas" in k: return "TBK"
    if "rincianbiaya" in k: return "RINCIAN"
    if "laporanhasil" in k or "laporanperjalanan" in k: return "LAPORAN"
    if "lembarke" in k or "kodenomor" in k or "suratperjalanan" in k or "berangkatdar" in k or "tibadi" in k: return "SPPD"
    if "surattugas" in k or "suratperintahtug" in k or ("sekretariatdaerah" in k and "alamat" in k): return "ST"
    if "boardingpass" in k or "invoice" in k or "tiket" in k or "hotel" in k: return "BUKTI"
    if "kuitansi" in k or "kwitansi" in k or "nota" in k or "faktur" in k: return "NOTA"
    if "daftarhadir" in k: return "HADIR"
    if "undangan" in k: return "UNDANGAN"
    return "LAIN"

def run(page, frac, dpi):
    r = page.rect
    pm = page.get_pixmap(dpi=dpi, clip=pymupdf.Rect(0, 0, r.width, r.height * frac), colorspace=pymupdf.csGRAY)
    im = np.frombuffer(pm.samples, np.uint8).reshape(pm.height, pm.width)
    res, _ = OCR(np.stack([im] * 3, -1))
    return [[t[1], [round(float(v)) for v in t[0][0]]] for t in (res or [])]

def spasi(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s); s = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", s)
    return re.sub(r"\s+", " ", s).strip(' :："“”')

def uang(toks):
    v = [int(re.sub(r"\D", "", t)) for t in toks if re.fullmatch(r"(Rp\.?)?\s*\d{1,3}([.,]\d{3})+(,-|,00)?", t.replace(" ", ""))]
    return [x for x in v if 1000 <= x < 10**11]

def urai_tbk(full):
    toks = [t[0] for t in full]; j = " ".join(toks)
    no = next((int(m.group(1)) for t in toks for m in [re.match(r"^No\.?(\d{1,4})$", t.replace(" ", ""))] if m), None)
    kode = next((t.replace(" ", "") for t in toks if re.fullmatch(r"\d\.\d\.\d{2}\.\d{2}\.\d{2,3}\.\d{4,5}", t.replace(" ", ""))), None)
    u = uang(toks); nilai = u[0] if u else None
    ur = ""
    for k, t in enumerate(toks):
        if "untukpembayaran" in K(t):
            ur = toks[k + 1] if k + 1 < len(toks) else ""
            for x in toks[k + 2:k + 8]:
                if re.search(r'["”]$', x.strip()) and "surat" not in x.lower(): ur += " " + x
            break
    tgl = None
    m = re.search(r"Andoolo\s*,?\s*(\d{1,2})\s*([A-Za-z]+)\s*(\d{4})", j)
    if m:
        bn = next((i for i, b in enumerate(BLN) if m.group(2).lower().startswith(b[:3])), None)
        if bn is not None: tgl = f"{int(m.group(1))} {BLN[bn].capitalize()} {m.group(3)}"
    yk = next((t[1][1] for t in full if "menerima" in K(t[0])), None); pen = None
    if yk is not None:
        cand = [t for t in full if t[1][1] > yk and re.search(r"[A-Z]{4}", t[0]) and not re.search(r"NIP|\d{5}|Anggaran|Pengeluaran|WESEL", t[0])]
        if cand: pen = re.sub(r"\.{2,}", ".", max(cand, key=lambda t: t[1][0])[0]).strip(" ,.")
    return {"bku": no, "kode": kode, "nilai": nilai, "uraian": spasi(ur) or None, "tgl": tgl, "penerima": pen}

def baca(path, page):
    d = pymupdf.open(path); p = d[max(0, min(page - 1, d.page_count - 1))]
    t0 = time.time()
    with LOCK:
        head = run(p, 0.22, 75)
        tp = tipe(" ".join(t[0] for t in head))
        full = run(p, 0.55, 120) if tp == "TBK" else run(p, 1.0, 90) if tp in ("RINCIAN", "ST", "SPPD", "LAPORAN", "NOTA", "BUKTI") else head
    teks = " ".join(t[0] for t in full)
    out = {"tipe": tp, "dok": NAMA[tp], "teks": teks[:3000], "detik": round(time.time() - t0, 1), "halaman": d.page_count}
    if tp == "TBK": out["fields"] = urai_tbk(full)
    if tp in ("RINCIAN", "NOTA"):
        u = uang([t[0] for t in full]); out["total"] = max(u) if u else None
    return out

