"""Satuan biaya perjalanan dinas dari Peraturan Bupati Konawe Selatan Nomor 57 Tahun 2025 tentang SHS TA 2026 (Lampiran II).
v = 1: angka dicocokkan dengan gambar pindaian halaman tersebut; v = 0: hasil OCR, belum dicocokkan (draf hanya 'perlu dicek').
Penginapan: kolom (es1, es2, es3, es4, gol12) = KDH/Pejabat Eselon I, Pejabat Eselon II, Eselon III/Gol IV, Eselon IV/Gol III, Gol I-II & non-ASN.
Ketentuan (hlm 26 butir 6): tanpa bukti hotel, penginapan dibayar 30% dari tarif hotel kota tujuan sesuai tingkatan perjalanan dinas, lumpsum."""
import re

TAHUN = 2026
# transport pergi-pulang (OK = orang kali). Kendari: SHS hanya memuat "Provinsi ke Kabupaten/Kota dalam provinsi yang sama (One Way)" Rp305.000.
TRANSPORT = {  # lokasi: (nilai, halaman, v, uraian)
    **{k: (n, 27, 1, f"Transport Andoolo–{nm} (sebaliknya)") for k, nm, n in [
        ("laonti", "Laonti", 250000), ("moramoutara", "Moramo Utara", 170000), ("ranomeeto", "Ranomeeto", 150000), ("kolono", "Kolono", 150000),
        ("basala", "Basala", 150000), ("kolonotimur", "Kolono Timur", 150000), ("sabulakoa", "Sabulakoa", 150000), ("lainea", "Lainea", 140000),
        ("moramo", "Moramo", 140000), ("konda", "Konda", 120000), ("landono", "Landono", 120000), ("angata", "Angata", 120000), ("mowila", "Mowila", 120000),
        ("benua", "Benua", 120000), ("ranomeetobarat", "Ranomeeto Barat", 120000), ("palanggaselatan", "Palangga Selatan", 100000), ("wolasi", "Wolasi", 100000),
        ("tinanggea", "Tinanggea", 100000), ("lalembuu", "Lalembuu", 100000), ("baito", "Baito", 95000), ("buke", "Buke", 95000), ("palangga", "Palangga", 85000),
        ("laeya", "Laeya", 85000), ("andoolobarat", "Andoolo Barat", 65000), ("andoolo", "Andoolo", 40000)]},
    **{k: (n, 33, 1, f"Transport Kab. Konawe Selatan ke {nm} (pergi-pulang)") for k, nm, n in [
        ("bombana", "Kab. Bombana", 270000), ("kolaka", "Kab. Kolaka", 450000), ("kolakatimur", "Kab. Kolaka Timur", 380000), ("kolakautara", "Kab. Kolaka Utara", 500000),
        ("konawe", "Kab. Konawe", 355000), ("konaweutara", "Kab. Konawe Utara", 400000), ("baubau", "Kota Bau-Bau", 700000), ("butontengah", "Kab. Buton Tengah", 720000),
        ("butonutara", "Kab. Buton Utara", 690000), ("buton", "Kab. Buton", 760000), ("butonselatan", "Kab. Buton Selatan", 780000), ("muna", "Kab. Muna", 600000),
        ("munabarat", "Kab. Muna Barat", 670000), ("wakatobi", "Kab. Wakatobi", 740000), ("konawekepulauan", "Kab. Konawe Kepulauan", 500000)]},
    "kendari": (610000, 33, 1, "Transport Provinsi ke Kabupaten/Kota dalam provinsi yang sama Rp305.000 sekali jalan (one way), pergi-pulang = 2 x Rp305.000"),
}
KECAMATAN = {k for k, v in TRANSPORT.items() if v[1] == 27}
KAB_SULTRA = {k for k, v in TRANSPORT.items() if v[1] == 33}
HARIAN = {  # wilayah: (nilai per hari, halaman, v, uraian)
    "dalamkota": (150000, 27, 1, "Uang harian perjalanan dinas dalam kota (lebih dari 8 jam)"),
    "sultra": (380000, 29, 0, "Uang harian perjalanan dinas luar kota tujuan Sulawesi Tenggara"),
    "kepulauanriau": (370000, 29, 0, "Uang harian perjalanan dinas luar kota tujuan Kepulauan Riau"),
}
PENGINAPAN = {  # kota: ((es1, es2, es3, es4, gol12), halaman, v)
    "kendari": ((3500000, 2000000, 1200000, 600000, 600000), 34, 1),
    **{k: ((2500000, 1500000, 800000, 600000, 600000), 34, 1) for k in ("bombana", "kolaka", "kolakatimur")},
    **{k: ((2500000, 1500000, 800000, 600000, 600000), 34, 0) for k in ("kolakautara", "konawe", "konaweutara", "baubau", "buton")},
}
KOLOM = ["es1", "es2", "es3", "es4", "gol12"]
NAMA_KOLOM = {"es1": "Kepala Daerah/Pejabat Eselon I", "es2": "Pejabat Eselon II", "es3": "Pejabat Eselon III/Golongan IV", "es4": "Pejabat Eselon IV/Golongan III", "gol12": "ASN Golongan I, II & non-ASN"}
REPRESENTASI = {"luarkota": (150000, 32, 0, "Uang representasi perjalanan dinas luar kota Pejabat Eselon II"),
                "dalamkota": (75000, 27, 1, "Uang representasi perjalanan dinas dalam kota Pejabat Eselon II")}

def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def lokasi(teks):
    """Nama tempat tujuan (bebas) -> kunci lokasi tarif."""
    k = norm(teks)
    if not k: return None
    if "sultra" in k or "sulawesitenggara" in k or "kendari" in k: return "kendari"
    if "kepulauanriau" in k or "batam" in k: return "kepulauanriau"
    k = re.sub(r"^(kabupaten|kab|kota|kecamatan|kec|provinsi|prov)", "", k)
    for daftar in (sorted(KAB_SULTRA | KECAMATAN, key=len, reverse=True),):
        for x in daftar:
            if k.startswith(x): return x
    return k

def wilayah_harian(lok):
    if lok in KECAMATAN: return "dalamkota"
    if lok in KAB_SULTRA or lok == "kendari": return "sultra"
    return lok

def tingkat(jabatan):
    """Jabatan (dari Surat Tugas) -> kolom tarif penginapan; None bila tidak dapat dipastikan."""
    j = (jabatan or "").lower()
    if not j: return None
    if re.search(r"bupati|ketua dprd", j): return "es1"
    if re.search(r"asisten|staf ahli|sekretaris daerah|kepala dinas|kepala badan|inspektur daerah|sekretaris dprd", j): return "es2"
    if re.search(r"kepala bagian|kabag|camat|sekretaris dinas|sekretaris badan|inspektur pembantu", j): return "es3"
    if re.search(r"kepala sub|kasubbag|kasubag|kepala seksi|kasi|lurah", j): return "es4"
    return "pelaksana"  # fungsional/pelaksana: golongan III atau I-II, tidak terbaca dari jabatan
