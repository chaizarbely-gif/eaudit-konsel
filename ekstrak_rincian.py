"""Uraikan token OCR halaman "Rincian Biaya Perjalanan Dinas" menjadi data terstruktur untuk audit awal.
Masukan: daftar token [teks, [x, y]] (format ocr.run). Keluaran: {rincian: [...], total, nama, tgl_awal, tgl_akhir}."""
import re

BLN = ["januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember"]
K = lambda s: re.sub(r"[^a-z]", "", (s or "").lower())

def spasi(s):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s or ""); s = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", s); s = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", s)
    return re.sub(r"\s+", " ", s).strip()

def angka(t):
    m = re.fullmatch(r"(?:Rp\.?)?(\d{1,3}(?:[.,]\d{3})+)(?:,-|,00|\.-)?", t.replace(" ", ""))
    return int(re.sub(r"\D", "", m.group(1))) if m else None

def pos(ur):
    k = K(ur)
    if "harian" in k: return "harian"
    if "penginapan" in k or "hotel" in k: return "penginapan"
    if "representasi" in k: return "representasi"
    if any(x in k for x in ("transport", "tiket", "taksi", "pesawat", "kapal", "bbm")): return "transport"
    if "jumlah" in k or "total" in k: return "jumlah"
    return "lain"

def tanggal(s):
    out = []
    for m in re.finditer(r"(\d{1,2})\s*([A-Za-z]{3,})\s*(20\d{2})", s):
        b = next((i for i, x in enumerate(BLN) if m.group(2).lower().startswith(x[:3])), None)
        if b is not None: out.append(f"{m.group(3)}-{b + 1:02d}-{int(m.group(1)):02d}")
    return out

def urai(full):
    if not full: return {}
    toks = sorted(full, key=lambda t: (t[1][1], t[1][0]))
    baris = []
    for t in toks:
        if baris and abs(t[1][1] - baris[-1][0]) <= 14: baris[-1][1].append(t)
        else: baris.append([t[1][1], [t]])
    rinci = []; total = None; x_nilai = None
    for _, bt in baris:
        bt.sort(key=lambda t: t[1][0])
        nil = [(angka(t[0]), t) for t in bt]; nil = [(v, t) for v, t in nil if v and v >= 1000]
        if not nil:
            # baris lanjutan uraian (mis. "hari)") di bawah baris rincian sebelumnya
            sisa = " ".join(t[0] for t in bt if x_nilai is None or t[1][0] < x_nilai)
            if rinci and sisa and len(sisa) < 40 and not re.search(r"menerima|jumlah", sisa, re.I): rinci[-1]["uraian"] += " " + sisa
            continue
        v, tv = nil[0]; x_nilai = tv[1][0]
        ur = " ".join(t[0] for t in bt if t[1][0] < x_nilai and not re.fullmatch(r"\d{1,2}\.?", t[0].strip())).strip()
        if pos(ur) == "jumlah": total = v; continue
        rinci.append({"uraian": ur, "jumlah": v})
    for i in rinci:
        ur = spasi(i["uraian"]); i["uraian"] = ur; i["pos"] = pos(ur)
        h = re.search(r"\(?\s*(\d{1,2})\s*\)?\s*(hari|malam|org|orang|kali)", ur, re.I)
        i["vol"] = int(h.group(1)) if h else None
        i["satuan_nilai"] = i["jumlah"] // i["vol"] if i["vol"] else None
        tj = re.search(r"di\s+([A-Z][A-Za-z ]+?)\s*(?:\(|$)", ur); i["tujuan"] = tj.group(1).strip() if tj else None
        i["persen"] = int(re.search(r"(\d{1,3})\s*%", ur).group(1)) if re.search(r"(\d{1,3})\s*%", ur) else None
    tg = tanggal(" ".join(t[0] for t in toks[:12]))
    nama = None
    ym = next((n for n, (_, bt) in enumerate(baris) if any("menerima" in K(t[0]) for t in bt)), None)
    if ym is not None:
        for _, bt in baris[ym + 1:ym + 6]:
            cand = [t[0] for t in bt if re.search(r"[A-Z]{3}", t[0]) and not re.search(r"NIP|\d{5}", t[0])]
            if cand: nama = max(cand, key=len).strip(" .,"); break
    return {"rincian": rinci, "total": total, "nama": nama, "tgl_awal": tg[0] if tg else None, "tgl_akhir": tg[1] if len(tg) > 1 else None}
