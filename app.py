"""e-Audit Kabupaten Konawe Selatan — server lokal (Python + SQLite).
Jalankan:  python app.py   lalu buka http://localhost:8080
Data      :  data/eaudit.db (SQLite) dan data/unggahan/ (scan SPJ)
"""
import http.server, socketserver, json, os, re, sys, time, sqlite3, hashlib, secrets, threading, urllib.parse, mimetypes, shutil, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web"); DATA = os.environ.get("EAUDIT_DATA") or os.path.join(ROOT, "data"); UP = os.path.join(DATA, "unggahan"); DOK = os.path.join(ROOT, "dokumen")
DBF = os.path.join(DATA, "eaudit.db")
PORT = int(os.environ.get("EAUDIT_PORT", "8080"))
os.makedirs(UP, exist_ok=True)
sys.path.insert(0, ROOT)
import ocr  # noqa: E402
import lhp  # noqa: E402
import akses  # noqa: E402
import jdih  # noqa: E402
import audit_awal  # noqa: E402

INSP = {"auditor", "ketua", "irban", "inspektur", "admin"}
OPDR = {"bendahara", "ppk", "pakpa"}
PENGELOLA = {"irban", "inspektur", "admin"}
RANK = {"draf": 0, "kembali": 0, "diajukan": 1, "ppk": 2, "bendahara": 3, "dibayar": 4}
JENIS_DOCS = {
    "HON": ["Undangan", "Daftar hadir", "Daftar penerima honor", "Resume kegiatan", "Kuitansi"],
    "SPPD": ["Surat tugas", "SPPD", "Bukti transportasi", "Bukti penginapan", "Laporan perjalanan"],
    "BRG": ["SPK / kontrak", "Faktur / kuitansi", "BAST", "Foto barang"],
    "KON": ["Kontrak", "Laporan progres fisik", "BA pemeriksaan", "Foto progres", "Kuitansi"],
    "MMR": ["Undangan", "Daftar hadir", "Kuitansi", "Foto kegiatan"],
    "PDGU": ["Tanda Bukti Kas", "Surat Tugas", "SPPD", "Laporan Hasil Perjalanan", "Rincian Biaya Perjalanan"],
    "BLGU": ["Tanda Bukti Kas"]}
MEK = {"GU": "UP/GU", "TU": "Tambahan Uang (TU)", "LS": "Langsung (LS)"}
BLN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
DBLOCK = threading.Lock()

# ------------------------------------------------------------------ basis data
def db():
    c = sqlite3.connect(DBF, timeout=15); c.row_factory = sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c

SKEMA = """
CREATE TABLE IF NOT EXISTS opd(kode TEXT PRIMARY KEY, nama TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, nama TEXT, nip TEXT, jabatan TEXT,
  peran TEXT NOT NULL, opd TEXT, salt TEXT, hash TEXT, aktif INTEGER DEFAULT 1, dibuat TEXT);
CREATE TABLE IF NOT EXISTS sesi(token TEXT PRIMARY KEY, user_id INTEGER, kadaluarsa REAL);
CREATE TABLE IF NOT EXISTS monalisa(id INTEGER PRIMARY KEY, opd TEXT, nama TEXT, nilai INTEGER, fisik INTEGER, keu INTEGER, sumber TEXT);
CREATE TABLE IF NOT EXISTS spj(id TEXT PRIMARY KEY, opd TEXT, mp_id INTEGER, jenis TEXT, bulan INTEGER, nilai INTEGER, uraian TEXT,
  bku TEXT, tgl TEXT, kode TEXT, penerima TEXT, status TEXT, catatan TEXT, tgl_aju TEXT, no_sp2d TEXT, aicek TEXT, sumber TEXT, gu TEXT,
  data TEXT, dibuat TEXT, diubah TEXT);
CREATE TABLE IF NOT EXISTS audit(spj_id TEXT PRIMARY KEY, data TEXT, status TEXT, auditor TEXT, tgl TEXT);
CREATE TABLE IF NOT EXISTS temuan(id INTEGER PRIMARY KEY, spj_id TEXT, opd TEXT, dok TEXT, uraian TEXT, rekomendasi TEXT, nilai INTEGER,
  status TEXT, tl_uraian TEXT, tl_files TEXT, tl_oleh TEXT, tl_tgl TEXT, verif_oleh TEXT, verif_tgl TEXT, verif_catatan TEXT, dibuat TEXT);
CREATE TABLE IF NOT EXISTS pkpt(id INTEGER PRIMARY KEY, kegiatan TEXT, jenis TEXT, objek TEXT, m1 INTEGER, m2 INTEGER, hari INTEGER,
  anggaran INTEGER, pelaksana TEXT, risiko TEXT, realisasi INTEGER DEFAULT 0, catatan TEXT);
CREATE TABLE IF NOT EXISTS agenda(id INTEGER PRIMARY KEY, tgl TEXT, jam TEXT, acara TEXT, tempat TEXT, objek TEXT, pj TEXT, pic TEXT,
  no_st TEXT, dasar TEXT, tim TEXT, lama INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS log(id INTEGER PRIMARY KEY, waktu TEXT, user TEXT, peran TEXT, aksi TEXT, objek TEXT, detail TEXT);
"""
def sekarang(): return datetime.datetime.now().isoformat(timespec="seconds")
def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt, hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()
def catat(c, u, aksi, objek, detail=""):
    c.execute("INSERT INTO log(waktu,user,peran,aksi,objek,detail) VALUES(?,?,?,?,?,?)",
              (sekarang(), u["nama"] if u else "Sistem", u["peran"] if u else "", aksi, objek, detail))

def siapkan():
    baru = not os.path.exists(DBF)
    c = db(); c.executescript(SKEMA)
    if baru:
        import seed
        seed.isi(c, hash_pw, JENIS_DOCS, BLN, sekarang)
        c.commit(); print("Database baru dibuat dan diisi data awal:", DBF); print("Kata sandi awal semua akun uji coba:", seed.SANDI_AWAL, "(segera ganti; reset per akun lewat menu Pengguna & Akses)")
    lhp.migrasi(c); lhp.isi_contoh(c, sekarang); akses.migrasi(c, hash_pw, sekarang); jdih.migrasi(c); audit_awal.migrasi(c)
    c.execute("CREATE TABLE IF NOT EXISTS gu(id INTEGER PRIMARY KEY, opd TEXT, nama TEXT, tgl TEXT, spj_ids TEXT, status TEXT, dibuat_oleh TEXT, dibuat TEXT, diubah TEXT)")
    # mekanisme pembayaran: UP/GU, TU, LS
    if "mekanisme" not in {r[1] for r in c.execute("PRAGMA table_info(spj)")}:
        c.execute("ALTER TABLE spj ADD COLUMN mekanisme TEXT")
        c.execute("UPDATE spj SET mekanisme = CASE WHEN jenis IN ('KON','BRG') THEN 'LS' ELSE 'GU' END")
        c.execute("UPDATE spj SET mekanisme='TU' WHERE opd='SETDA' AND uraian LIKE 'Kunjungan kerja studi banding%'")
    ada = {r[1] for r in c.execute("PRAGMA table_info(gu)")}
    for k, t in (("jenis", "TEXT DEFAULT 'GU'"), ("no_sp2d", "TEXT"), ("tgl_sp2d", "TEXT"), ("nilai_sp2d", "INTEGER DEFAULT 0"), ("setor", "INTEGER DEFAULT 0"), ("catatan", "TEXT")):
        if k not in ada: c.execute(f"ALTER TABLE gu ADD COLUMN {k} {t}")
    c.execute("UPDATE gu SET jenis='GU' WHERE jenis IS NULL")
    if "ganti" not in {r[1] for r in c.execute("PRAGMA table_info(users)")}: c.execute("ALTER TABLE users ADD COLUMN ganti INTEGER DEFAULT 0")  # wajib ganti sandi
    c.commit()
    c.close()

# ------------------------------------------------------------------ bentuk JSON
def spj_json(r, mp=None):
    d = json.loads(r["data"] or "{}")
    return {"id": r["id"], "opd": r["opd"], "mp_id": r["mp_id"], "mp": mp["nama"] if mp else None, "j": r["jenis"], "m": r["bulan"],
            "nilai": r["nilai"], "nama": r["uraian"], "bku": r["bku"] or "", "tgl": r["tgl"] or "", "kode": r["kode"] or "", "penerima": r["penerima"] or "",
            "mek": r["mekanisme"] or "GU", "st": r["status"], "catatan": r["catatan"], "tglAju": r["tgl_aju"], "no_sp2d": r["no_sp2d"], "aicek": json.loads(r["aicek"]) if r["aicek"] else None,
            "gu": r["gu"], "nyata": r["sumber"] == "gu", "input": r["sumber"] == "input", "pptk": d.get("pptk", "Bendahara Pengeluaran"),
            "fisik": mp["fisik"] if mp and mp["fisik"] is not None and r["jenis"] == "KON" else None, "keu": mp["keu"] if mp and r["jenis"] == "KON" else None,
            "docs": d.get("docs", []), "cek": d.get("cek", []), "nk": d.get("nk", ""), "aiSaran": d.get("aiSaran"), "files": d.get("files", {})}

def ambil_spj(c, where="1=1", args=()):
    mps = {m["id"]: m for m in c.execute("SELECT * FROM monalisa")}
    return [spj_json(r, mps.get(r["mp_id"])) for r in c.execute(f"SELECT * FROM spj WHERE {where} ORDER BY opd, id", args)]

def boleh_lihat_spj(u, s, lk=None):
    if u["peran"] in INSP: return RANK.get(s["status"] if isinstance(s, sqlite3.Row) else s["st"], 0) >= 1 and akses.boleh(lk, s["opd"])
    return u["opd"] == s["opd"]

# ------------------------------------------------------------------ hak akses berkas
def opd_berkas(c, rel):
    """rel = 'berkas/...' atau 'dokumen/...'; kembalikan himpunan kode OPD pemilik berkas."""
    seg = rel.split("/")
    if seg[0] == "berkas" and len(seg) >= 3:
        f = seg[1]
        if f == "INSP" or c.execute("SELECT 1 FROM opd WHERE kode=?", (f,)).fetchone(): return {f}
        r = c.execute("SELECT opd FROM spj WHERE id=?", (f,)).fetchone()  # jalur lama: berkas/<id SPJ>/...
        if r: return {r["opd"]}
        mt = re.fullmatch(r"TL-(\d+)", f)
        if mt:
            r = c.execute("SELECT opd FROM temuan WHERE id=?", (int(mt.group(1)),)).fetchone()
            return {r["opd"]} if r else set()
        return set()
    if seg[0] == "dokumen" and len(seg) >= 2:
        pola = json.dumps(rel, ensure_ascii=False).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return {r["opd"] for r in c.execute("SELECT DISTINCT opd FROM spj WHERE data LIKE ? ESCAPE '\\'", ("%" + pola + "%",))}
    return set()

def boleh_berkas(c, u, rel):
    if re.fullmatch(r"(berkas|dokumen)/JDIH/[A-Za-z0-9_-][A-Za-z0-9._-]*\.pdf", rel): return True  # JDIH: terbuka bagi semua pengguna yang masuk
    ow = opd_berkas(c, rel)
    if u["peran"] in INSP:
        lk = akses.lingkup(c, u)
        return lk is None or "INSP" in ow or any(o in lk for o in ow)
    return u["opd"] in ow

def berkas_nyata(c, opd, f):
    """True bila entri berkas SPJ menunjuk ke berkas yang benar-benar ada di server dan milik OPD tersebut."""
    if not isinstance(f, dict): return False
    for x in (f.get("parts") or []) + [f]:
        if not isinstance(x, dict): continue
        rel = str(x.get("path") or x.get("src") or "").replace("\\", "/").lstrip("/")
        if not rel.startswith(("berkas/", "dokumen/")): continue
        try: full = jalur_aman(UP if rel.startswith("berkas/") else DOK, rel.split("/", 1)[1])
        except Galat: continue
        if os.path.isfile(full) and opd in opd_berkas(c, rel): return True
    return False

# ------------------------------------------------------------------ handler HTTP
# penguncian login: 5 gagal per akun atau 20 gagal per alamat IP dalam 15 menit
GAGAL = {}; GAGAL_LOCK = threading.Lock(); JEDA = 15 * 60
def _gagal_bersih(k, t):
    GAGAL[k] = [x for x in GAGAL.get(k, []) if t - x < JEDA]
    if not GAGAL[k]: GAGAL.pop(k)
def sisa_kunci(akun, ip):
    t = time.time()
    with GAGAL_LOCK:
        for k, batas in ((("u", akun), 5), (("ip", ip), 20)):
            _gagal_bersih(k, t); L = GAGAL.get(k, [])
            if len(L) >= batas: return int(JEDA - (t - L[0])) + 1
    return 0
def catat_gagal(akun, ip):
    with GAGAL_LOCK:
        for k in (("u", akun), ("ip", ip)): GAGAL.setdefault(k, []).append(time.time())

class Galat(Exception):
    def __init__(self, kode, pesan, **ext): self.kode = kode; self.pesan = pesan; self.ext = ext

def jalur_aman(base, rel):
    """Gabungkan base + rel ('a/b/c'); tolak backslash, huruf drive, '..' dan apa pun yang keluar dari base."""
    seg = rel.split("/")
    if "\\" in rel or ":" in rel or "\x00" in rel or any(x in ("..", ".") for x in seg): raise Galat(400, "Alamat tidak valid.")
    b = os.path.abspath(base); full = os.path.abspath(os.path.join(b, *seg))
    if not full.startswith(b + os.sep): raise Galat(400, "Alamat tidak valid.")
    return full

HURUF = "abcdefghjkmnpqrstuvwxyz23456789"  # tanpa huruf/angka yang mirip (l, 1, o, 0, i)
def sandi_awal(): return "".join(secrets.choice(HURUF) for _ in range(4)) + "-" + "".join(secrets.choice(HURUF) for _ in range(4))
def kartu(c, uid):
    """Buat sandi awal baru (wajib diganti saat masuk) dan kembalikan data kartu akun."""
    r = c.execute("SELECT u.*, o.nama AS opd_nama FROM users u LEFT JOIN opd o ON o.kode=u.opd WHERE u.id=?", (uid,)).fetchone()
    if not r: raise Galat(404, "Pengguna tidak ditemukan.")
    pw = sandi_awal(); s, h = hash_pw(pw)
    c.execute("UPDATE users SET salt=?, hash=?, ganti=1 WHERE id=?", (s, h, uid)); c.execute("DELETE FROM sesi WHERE user_id=?", (uid,))
    return {"id": r["id"], "username": r["username"], "nama": r["nama"], "nip": r["nip"], "jabatan": r["jabatan"], "peran": r["peran"], "opd": r["opd"], "opd_nama": r["opd_nama"], "password": pw}

class H(http.server.BaseHTTPRequestHandler):
    server_version = "eAudit/1.0"
    def log_message(self, *a): pass
    # --- di belakang Cloudflare Tunnel: semua koneksi datang dari 127.0.0.1
    def lokal(self): return self.client_address[0] in ("127.0.0.1", "::1")
    def ip_asal(self):
        return (self.headers.get("Cf-Connecting-IP") or self.client_address[0]).strip()[:64] if self.lokal() else self.client_address[0]
    def https(self):
        return self.lokal() and (self.headers.get("X-Forwarded-Proto") == "https" or '"https"' in self.headers.get("Cf-Visitor", ""))
    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff"); self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "same-origin")
        if self.https(): self.send_header("Strict-Transport-Security", "max-age=31536000")
        super().end_headers()

    # --- utilitas
    def kirim(self, obj, code=200, cookie=None):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(b)))
        if cookie is not None: self.send_header("Set-Cookie", cookie + ("; Secure" if self.https() else ""))
        self.end_headers(); self.wfile.write(b)
    def berkas(self, path, unduh=False):
        if not os.path.isfile(path): return self.kirim({"error": "Berkas tidak ditemukan."}, 404)
        ct = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if path.endswith(".js"): ct = "text/javascript; charset=utf-8"
        if path.endswith(".html"): ct = "text/html; charset=utf-8"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(os.path.getsize(path)))
        self.send_header("Cache-Control", "no-store"); self.end_headers()
        with open(path, "rb") as f: shutil.copyfileobj(f, self.wfile, 1 << 20)
    def body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n > 20 * 1024 * 1024: raise Galat(413, "Data terlalu besar.")
        raw = self.rfile.read(n) if n else b""
        return raw
    def jbody(self):
        raw = self.body()
        try: return json.loads(raw or b"{}")
        except Exception: raise Galat(400, "Format data tidak valid.")
    def pengguna(self):
        ck = self.headers.get("Cookie", ""); m = re.search(r"sid=([A-Za-z0-9_-]+)", ck)
        if not m: return None
        c = db()
        r = c.execute("SELECT u.* FROM sesi s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.kadaluarsa>? AND u.aktif=1", (m.group(1), time.time())).fetchone()
        c.close(); return dict(r) if r else None
    def wajib(self, *peran):
        u = self.pengguna()
        if not u: raise Galat(401, "Silakan masuk terlebih dahulu.")
        if peran and u["peran"] not in peran: raise Galat(403, "Anda tidak berwenang untuk tindakan ini.")
        return u

    # --- routing
    def do_GET(self): self.jalan("GET")
    def do_POST(self): self.jalan("POST")
    def do_PUT(self): self.jalan("PUT")
    def do_DELETE(self): self.jalan("DELETE")
    def jalan(self, metode):
        u = urllib.parse.urlparse(self.path); p = urllib.parse.unquote(u.path); q = urllib.parse.parse_qs(u.query)
        try:
            if p.startswith("/api/"): return self.api(metode, p[5:].strip("/").split("/"), q)
            if metode != "GET": raise Galat(405, "Metode tidak didukung.")
            if p in ("/", ""):
                us = self.pengguna()
                tujuan = "/login.html" if not us else "/bendahara.html" if us["peran"] == "bendahara" else "/verifikasi.html" if us["peran"] in ("ppk", "pakpa") else "/eaudit.html"
                self.send_response(302); self.send_header("Location", tujuan); self.end_headers(); return
            if p.startswith("/berkas/") or p.startswith("/dokumen/"):
                us = self.wajib()
                base, rel = (UP, p[8:]) if p.startswith("/berkas/") else (DOK, p[9:])
                full = jalur_aman(base, rel)
                c = db(); ok = boleh_berkas(c, us, p.lstrip("/")); c.close()
                if not ok: raise Galat(403, "Anda tidak berwenang membuka berkas ini.")
                return self.berkas(full)
            rel = p.lstrip("/")
            return self.berkas(jalur_aman(WEB, rel))
        except Galat as g:
            if p.startswith("/api/") or g.kode != 401: return self.kirim({"error": g.pesan} | g.ext, g.kode)
            self.send_response(302); self.send_header("Location", "/login.html"); self.end_headers()
        except BrokenPipeError:
            pass
        except Exception as e:
            try: self.kirim({"error": "Terjadi kesalahan: " + str(e)}, 500)
            except Exception: pass

    def api(self, m, seg, q):
        g = lambda k, d="": q.get(k, [d])[0]
        a = seg[0] if seg else ""
        # ---------- publik
        if a == "status": return self.kirim({"ai": ocr.AI, "upload": True, "pesan": "" if ocr.AI else ocr.AIERR})
        if a == "login" and m == "POST":
            b = self.jbody(); akun = str(b.get("username", "")).strip().lower()[:80]; ip = self.ip_asal()
            dt = sisa_kunci(akun, ip)
            if dt: return self.kirim({"error": f"Terlalu banyak percobaan masuk yang gagal. Coba lagi dalam {(dt + 59) // 60} menit."}, 429)
            c = db()
            r = c.execute("SELECT * FROM users WHERE username=? AND aktif=1", (akun,)).fetchone()
            if not r or hash_pw(str(b.get("password", "")), r["salt"])[1] != r["hash"]:
                c.close(); catat_gagal(akun, ip); time.sleep(0.5); return self.kirim({"error": "Nama pengguna atau kata sandi salah."}, 401)
            with GAGAL_LOCK: GAGAL.pop(("u", akun), None)
            tok = secrets.token_urlsafe(32)
            c.execute("DELETE FROM sesi WHERE kadaluarsa<?", (time.time(),))
            c.execute("INSERT INTO sesi VALUES(?,?,?)", (tok, r["id"], time.time() + 10 * 3600)); catat(c, dict(r), "Masuk", "Akun", r["username"]); c.commit(); c.close()
            return self.kirim({"ok": True, "peran": r["peran"], "ganti": bool(r["ganti"])}, cookie=f"sid={tok}; Path=/; HttpOnly; SameSite=Strict")
        if a == "uji-masuk" and os.environ.get("EAUDIT_UJI") == "1":  # hanya untuk pengujian otomatis
            c = db(); r = c.execute("SELECT * FROM users WHERE username=?", (q.get("u", [""])[0],)).fetchone()
            if not r: c.close(); raise Galat(404, "Akun tidak ada.")
            tok = secrets.token_urlsafe(32); c.execute("INSERT INTO sesi VALUES(?,?,?)", (tok, r["id"], time.time() + 3600)); c.commit(); c.close()
            self.send_response(302); self.send_header("Set-Cookie", f"sid={tok}; Path=/; HttpOnly; SameSite=Lax"); self.send_header("Location", q.get("ke", ["/"])[0]); self.end_headers(); return
        if a == "logout":
            ck = re.search(r"sid=([A-Za-z0-9_-]+)", self.headers.get("Cookie", ""))
            if ck: c = db(); c.execute("DELETE FROM sesi WHERE token=?", (ck.group(1),)); c.commit(); c.close()
            return self.kirim({"ok": True}, cookie="sid=; Path=/; Max-Age=0")
        # ---------- wajib login
        us = self.wajib()
        if us.get("ganti") and a not in ("me", "password"): raise Galat(403, "Anda wajib mengganti kata sandi awal sebelum memakai aplikasi.", ganti=True)
        if a == "me":
            c = db(); o = c.execute("SELECT nama FROM opd WHERE kode=?", (us["opd"],)).fetchone(); lk = akses.lingkup(c, us); c.close()
            return self.kirim({k: us[k] for k in ("id", "username", "nama", "nip", "jabatan", "peran", "opd")} | {"ganti": bool(us.get("ganti")), "opd_nama": o["nama"] if o else None, "lingkup": sorted(lk) if lk is not None else None})
        if a == "password" and m == "POST":
            b = self.jbody(); c = db()
            if hash_pw(str(b.get("lama", "")), us["salt"])[1] != us["hash"]: c.close(); raise Galat(400, "Kata sandi lama salah.")
            if len(str(b.get("baru", ""))) < 8: c.close(); raise Galat(400, "Kata sandi baru minimal 8 karakter.")
            if b["baru"] == b.get("lama"): c.close(); raise Galat(400, "Kata sandi baru harus berbeda dari kata sandi lama.")
            s, h = hash_pw(b["baru"]); c.execute("UPDATE users SET salt=?, hash=?, ganti=0 WHERE id=?", (s, h, us["id"])); catat(c, us, "Ganti kata sandi", "Akun"); c.commit(); c.close()
            return self.kirim({"ok": True})
        if a == "ref":
            c = db(); lk = akses.lingkup(c, us); opd = [dict(r) for r in c.execute("SELECT * FROM opd ORDER BY rowid") if (akses.boleh(lk, r["kode"]) if us["peran"] in INSP else r["kode"] == us["opd"])]
            ms = c.execute("SELECT * FROM monalisa" + ("" if us["peran"] in INSP else " WHERE opd=?"), () if us["peran"] in INSP else (us["opd"],))
            mon = [dict(r) for r in ms if akses.boleh(lk, r["opd"])]; c.close()
            return self.kirim({"opd": opd, "monalisa": mon, "jenis_docs": JENIS_DOCS, "now_m": datetime.date.today().month})
        if a == "upload" and m == "POST": return self.unggah(us, q)
        if a == "ocr" and m == "POST": return self.baca_ocr(us, q)
        if a == "spj": return self.api_spj(us, m, seg[1:], q)
        if a == "ringkas":
            c = db(); lk = akses.lingkup(c, us); rows = [dict(r) for r in c.execute("SELECT opd, sumber, status, COUNT(*) n, SUM(nilai) nilai FROM spj GROUP BY opd, sumber, status")]; c.close()
            return self.kirim([r for r in rows if akses.boleh(lk, r["opd"])] if us["peran"] in INSP else [r for r in rows if r["opd"] == us["opd"]])
        if a == "audit": return self.api_audit(us, m, seg[1:])
        if a == "lhp": return self.api_lhp(us, m, seg[1:])
        if a == "gu": return self.api_gu(us, m, seg[1:])
        if a == "temuan": return self.api_temuan(us, m, seg[1:])
        if a == "pkpt": return self.api_tabel(us, m, seg[1:], "pkpt", ["kegiatan", "jenis", "objek", "m1", "m2", "hari", "anggaran", "pelaksana", "risiko", "realisasi", "catatan"])
        if a == "agenda": return self.api_tabel(us, m, seg[1:], "agenda", ["tgl", "jam", "acara", "tempat", "objek", "pj", "pic", "no_st", "dasar", "tim", "lama"])
        if a == "users": return self.api_users(us, m, seg[1:])
        if a == "jdih": return self.api_jdih(us, m, seg[1:], q)
        if a == "praaudit": return self.api_praaudit(us, m, seg[1:])
        if a == "log":
            if us["peran"] not in INSP: raise Galat(403, "Tidak berwenang.")
            c = db(); obj = g("objek"); lk = akses.lingkup(c, us)
            if lk is not None:
                if not obj: c.close(); raise Galat(403, "Riwayat seluruh aktivitas hanya untuk Administrator, Inspektur, dan Irban.")
                if obj.startswith("lhp:"): r_ = c.execute("SELECT opd FROM lhp WHERE id=?", (obj[4:],)).fetchone()
                else: r_ = c.execute("SELECT opd FROM spj WHERE id=?", (obj,)).fetchone()
                if not r_ or r_["opd"] not in lk: c.close(); raise Galat(403, "Di luar obrik yang ditugaskan.")
            rows = [dict(r) for r in (c.execute("SELECT * FROM log WHERE objek=? ORDER BY id DESC", (obj,)) if obj else c.execute("SELECT * FROM log ORDER BY id DESC LIMIT ?", (int(g("limit", "100")),)))]
            c.close(); return self.kirim(rows)
        raise Galat(404, "Alamat API tidak dikenal.")

    # ---------- unggah & OCR
    def unggah(self, us, q):
        if us["peran"] not in OPDR | INSP: raise Galat(403, "Tidak berwenang.")
        data = self.body()
        if not data or len(data) > 15 * 1024 * 1024: raise Galat(400, "Ukuran berkas tidak valid (maks. 15 MB).")
        spj = re.sub(r"[^A-Za-z0-9_-]+", "_", q.get("spj", ["umum"])[0])[:40]
        nm = re.sub(r"[^A-Za-z0-9._-]+", "_", q.get("name", ["berkas"])[0])[-80:]
        if not re.search(r"\.(pdf|jpe?g|png)$", nm, re.I): raise Galat(400, "Hanya PDF, JPG, atau PNG.")
        pem = us["opd"] if us["peran"] in OPDR else "INSP"
        if not re.fullmatch(r"[A-Za-z0-9_-]+", pem or ""): raise Galat(403, "Akun tidak terhubung ke perangkat daerah.")
        c = db()
        try:
            r = c.execute("SELECT opd FROM spj WHERE id=?", (spj,)).fetchone()
            mt = re.fullmatch(r"TL-(\d+)", spj)
            if mt: r = c.execute("SELECT opd FROM temuan WHERE id=?", (int(mt.group(1)),)).fetchone() or {"opd": None}
            if r and us["peran"] in OPDR and r["opd"] != us["opd"]: raise Galat(403, "Tidak boleh mengunggah ke SPJ/temuan perangkat daerah lain.")
        finally: c.close()
        folder = os.path.join(UP, pem, spj); os.makedirs(folder, exist_ok=True); fn = f"{int(time.time() * 1000)}_{nm}"
        open(os.path.join(folder, fn), "wb").write(data)
        return self.kirim({"path": f"berkas/{pem}/{spj}/{fn}", "size": len(data)})
    def baca_ocr(self, us, q):
        if not ocr.AI: raise Galat(503, "Asisten AI tidak aktif. " + ocr.AIERR)
        rel = q.get("path", [""])[0].replace("\\", "/").lstrip("/")
        full = jalur_aman(UP, rel[7:]) if rel.startswith("berkas/") else jalur_aman(DOK, rel[8:]) if rel.startswith("dokumen/") else None
        if not full or not os.path.isfile(full): raise Galat(404, "Berkas tidak ditemukan.")
        c = db(); ok = boleh_berkas(c, us, rel); c.close()
        if not ok: raise Galat(403, "Anda tidak berwenang membaca berkas ini.")
        return self.kirim(ocr.baca(full, int(q.get("page", ["1"])[0] or 1)))

    # ---------- SPJ
    def api_spj(self, us, m, seg, q):
        c = db()
        try:
            if m == "GET" and not seg:
                if us["peran"] in INSP: lk = akses.lingkup(c, us); rows = [x for x in ambil_spj(c, "status IN ('diajukan','ppk','bendahara','dibayar')") if akses.boleh(lk, x["opd"])]
                else: rows = ambil_spj(c, "opd=?", (us["opd"],))
                return self.kirim(rows)
            if m == "POST" and not seg:
                if us["peran"] != "bendahara": raise Galat(403, "Hanya bendahara yang dapat menginput SPJ.")
                b = self.jbody(); j = b.get("j")
                if j not in JENIS_DOCS: raise Galat(400, "Jenis belanja tidak valid.")
                if not str(b.get("nama", "")).strip() or not int(b.get("nilai") or 0): raise Galat(400, "Uraian dan nilai wajib diisi.")
                idc = str(b.get("id", ""))
                if not re.fullmatch(re.escape(us["opd"]) + r"-SPJ-\d{3,4}", idc) or c.execute("SELECT 1 FROM spj WHERE id=?", (idc,)).fetchone():
                    n = c.execute("SELECT COUNT(*) FROM spj WHERE opd=? AND sumber='input'", (us["opd"],)).fetchone()[0] + 1
                    while c.execute("SELECT 1 FROM spj WHERE id=?", (f"{us['opd']}-SPJ-{n:03d}",)).fetchone(): n += 1
                    idc = f"{us['opd']}-SPJ-{n:03d}"
                mp = b.get("mp_id")
                if mp and not c.execute("SELECT 1 FROM monalisa WHERE id=? AND opd=?", (mp, us["opd"])).fetchone(): raise Galat(400, "Paket MONALISA tidak valid.")
                docs = [{"n": d, "s": "kosong"} for d in JENIS_DOCS[j]]
                files = b.get("files") or {}
                for k, f in files.items():
                    if k.isdigit() and int(k) < len(docs): docs[int(k)]["s"] = "ok"
                data = {"pptk": "Input bendahara", "docs": docs, "cek": [False] * len(b.get("cek") or []), "nk": "", "files": files, "aiSaran": b.get("aiSaran")}
                mek = b.get("mek") if b.get("mek") in MEK else ("LS" if j in ("KON", "BRG") else "GU")
                c.execute("INSERT INTO spj(id,opd,mp_id,jenis,bulan,nilai,uraian,bku,tgl,kode,penerima,status,sumber,data,dibuat,diubah,mekanisme) VALUES(?,?,?,?,?,?,?,?,?,?,?,'draf','input',?,?,?,?)",
                          (idc, us["opd"], mp, j, int(b.get("m") or datetime.date.today().month), int(b["nilai"]), str(b["nama"]).strip(), str(b.get("bku", "")), str(b.get("tgl", "")),
                           str(b.get("kode", "")), str(b.get("penerima", "")), json.dumps(data, ensure_ascii=False), sekarang(), sekarang(), mek))
                catat(c, us, "Input SPJ baru", idc, str(b["nama"])[:120]); c.commit()
                return self.kirim(ambil_spj(c, "id=?", (idc,))[0])
            sid = seg[0] if seg else ""
            r = c.execute("SELECT * FROM spj WHERE id=?", (sid,)).fetchone()
            if not r: raise Galat(404, "SPJ tidak ditemukan.")
            if not boleh_lihat_spj(us, r, akses.lingkup(c, us)): raise Galat(403, "Anda tidak berwenang atas SPJ ini (di luar obrik yang ditugaskan).")
            aksi = seg[1] if len(seg) > 1 else ""
            data = json.loads(r["data"] or "{}")
            if m == "GET" and aksi == "riwayat":
                return self.kirim([dict(x) for x in c.execute("SELECT waktu,user,peran,aksi,detail FROM log WHERE objek=? ORDER BY id", (sid,))])
            if m == "GET" and not aksi: return self.kirim(ambil_spj(c, "id=?", (sid,))[0])
            if m == "PUT" and not aksi:
                if us["peran"] != "bendahara" or us["opd"] != r["opd"]: raise Galat(403, "Hanya bendahara OPD ini yang dapat mengubah SPJ.")
                if r["status"] not in ("draf", "kembali"): raise Galat(409, "SPJ sudah diajukan dan terkunci.")
                b = self.jbody(); docs = b.get("docs", data.get("docs"))
                if len(docs) != len(JENIS_DOCS[r["jenis"]]) and r["sumber"] != "gu": raise Galat(400, "Susunan dokumen tidak valid.")
                for d in docs:
                    if d.get("s") not in ("ok", "kosong", "ditolak"): raise Galat(400, "Status dokumen tidak valid.")
                data.update({"docs": docs, "cek": [bool(x) for x in b.get("cek", data.get("cek", []))], "nk": str(b.get("nk", "")), "files": b.get("files", data.get("files", {})), "aiSaran": b.get("aiSaran")})
                bulan = int(b.get("m") or r["bulan"]); bulan = bulan if 1 <= bulan <= 12 else r["bulan"]
                mek = b.get("mek") if b.get("mek") in MEK else (r["mekanisme"] or "GU")
                c.execute("UPDATE spj SET uraian=?, nilai=?, bku=?, tgl=?, kode=?, penerima=?, bulan=?, data=?, diubah=?, mekanisme=? WHERE id=?",
                          (str(b.get("nama", r["uraian"]))[:500], int(b.get("nilai") or 0), str(b.get("bku", "")), str(b.get("tgl", "")), str(b.get("kode", "")),
                           str(b.get("penerima", "")), bulan, json.dumps(data, ensure_ascii=False), sekarang(), mek, sid))
                c.commit(); return self.kirim({"ok": True})
            if m == "POST" and aksi == "ajukan":
                if us["peran"] != "bendahara" or us["opd"] != r["opd"]: raise Galat(403, "Hanya bendahara OPD ini yang dapat mengajukan.")
                if r["status"] not in ("draf", "kembali"): raise Galat(409, "SPJ sudah diajukan.")
                b = self.jbody()
                fs = data.get("files") or {}
                kurang = [d["n"] for i, d in enumerate(data.get("docs", [])) if d.get("s") != "ok" or (r["sumber"] != "contoh" and not berkas_nyata(c, r["opd"], fs.get(str(i))))]
                if kurang: raise Galat(400, "Dokumen belum lengkap atau berkasnya tidak ditemukan di server: " + ", ".join(kurang))
                if not b.get("sptjm"): raise Galat(400, "Pernyataan tanggung jawab wajib dicentang.")
                data["cek"] = [True] * len(data.get("cek", []))
                c.execute("UPDATE spj SET status='diajukan', tgl_aju=?, aicek=?, catatan=NULL, data=?, diubah=? WHERE id=?",
                          (sekarang(), json.dumps(b.get("aicek")) if b.get("aicek") else None, json.dumps(data, ensure_ascii=False), sekarang(), sid))
                catat(c, us, "Ajukan SPJ ke PPK", sid, "Pernyataan tanggung jawab dicentang"); c.commit(); return self.kirim({"ok": True})
            if m == "POST" and aksi == "verifikasi":
                b = self.jbody(); hasil = b.get("aksi"); cat = str(b.get("catatan", "")).strip()
                if us["opd"] != r["opd"] or us["peran"] not in ("ppk", "pakpa"): raise Galat(403, "Hanya PPK atau PA/KPA OPD ini.")
                tahap = {"ppk": "diajukan", "pakpa": "ppk"}[us["peran"]]
                if r["status"] != tahap: raise Galat(409, "SPJ tidak sedang menunggu tindakan Anda.")
                if hasil == "setuju":
                    baru = "ppk" if us["peran"] == "ppk" else "bendahara"
                    c.execute("UPDATE spj SET status=?, diubah=? WHERE id=?", (baru, sekarang(), sid))
                    catat(c, us, "Verifikasi PPK: disetujui" if us["peran"] == "ppk" else "Pengesahan PA/KPA: disahkan", sid, cat)
                elif hasil == "kembalikan":
                    if not cat: raise Galat(400, "Tuliskan alasan pengembalian.")
                    sl = b.get("slot")
                    if sl is not None and 0 <= int(sl) < len(data.get("docs", [])): data["docs"][int(sl)]["s"] = "ditolak"
                    c.execute("UPDATE spj SET status='kembali', catatan=?, data=?, diubah=? WHERE id=?", (cat, json.dumps(data, ensure_ascii=False), sekarang(), sid))
                    catat(c, us, "Dikembalikan ke bendahara", sid, cat)
                else: raise Galat(400, "Aksi tidak dikenal.")
                c.commit(); return self.kirim({"ok": True})
            if m == "POST" and aksi == "sp2d":
                if us["peran"] != "bendahara" or us["opd"] != r["opd"]: raise Galat(403, "Hanya bendahara OPD ini.")
                if r["status"] != "bendahara": raise Galat(409, "SPJ belum disahkan PA/KPA.")
                b = self.jbody(); no = str(b.get("no_sp2d", "")).strip()
                if not no: raise Galat(400, "Nomor SP2D wajib diisi.")
                c.execute("UPDATE spj SET status='dibayar', no_sp2d=?, diubah=? WHERE id=?", (no, sekarang(), sid)); catat(c, us, "SP2D dicatat", sid, no); c.commit()
                return self.kirim({"ok": True})
            raise Galat(404, "Aksi SPJ tidak dikenal.")
        finally:
            c.close()

    # ---------- Audit (kertas kerja) & temuan
    def api_audit(self, us, m, seg):
        if us["peran"] not in INSP: raise Galat(403, "Hanya Inspektorat.")
        c = db()
        try:
            lk = akses.lingkup(c, us)
            if m == "GET": return self.kirim({r["spj_id"]: json.loads(r["data"]) | {"status": r["status"], "auditor": r["auditor"], "tgl": r["tgl"]} for r in c.execute("SELECT a.*, s.opd FROM audit a JOIN spj s ON s.id=a.spj_id") if akses.boleh(lk, r["opd"])})
            if m == "PUT" and seg:
                sid = seg[0]; s = c.execute("SELECT * FROM spj WHERE id=?", (sid,)).fetchone()
                if not s or RANK.get(s["status"], 0) < 1: raise Galat(404, "SPJ belum diajukan.")
                if not akses.boleh(lk, s["opd"]): raise Galat(403, "SPJ di luar obrik yang ditugaskan kepada Anda.")
                b = self.jbody(); st = b.get("status")
                if st not in ("proses", "selesai"): raise Galat(400, "Status tidak valid.")
                cek = {str(k): v for k, v in (b.get("cek") or {}).items() if v in ("s", "t")}; cat = {str(k): str(v)[:1000] for k, v in (b.get("cat") or {}).items()}
                docs = json.loads(s["data"] or "{}").get("docs", [])
                if st == "selesai" and len(cek) < len(docs): raise Galat(400, "Semua dokumen harus dinilai sebelum selesai.")
                c.execute("INSERT OR REPLACE INTO audit VALUES(?,?,?,?,?)", (sid, json.dumps({"cek": cek, "cat": cat}, ensure_ascii=False), st, us["nama"], sekarang()))
                if st == "selesai":
                    # temuan yang sudah masuk LHA atau sudah ditindaklanjuti tidak boleh terhapus/terduplikasi
                    c.execute("DELETE FROM temuan WHERE spj_id=? AND status='belum' AND tl_uraian IS NULL AND lhp_id IS NULL AND id NOT IN (SELECT temuan_id FROM praaudit WHERE temuan_id IS NOT NULL)", (sid,))
                    ada = {r_["dok"] for r_ in c.execute("SELECT dok FROM temuan WHERE spj_id=?", (sid,))}
                    on = c.execute("SELECT nama FROM opd WHERE kode=?", (s["opd"],)).fetchone()["nama"]
                    for k, v in cek.items():
                        if v == "t":
                            dok = docs[int(k)]["n"] if int(k) < len(docs) else "Dokumen"
                            if dok in ada: continue
                            c.execute("INSERT INTO temuan(spj_id,opd,dok,uraian,rekomendasi,nilai,status,dibuat) VALUES(?,?,?,?,?,?,'belum',?)",
                                      (sid, s["opd"], dok, cat.get(k) or "Dokumen tidak sesuai", f"Kepala {on} agar memerintahkan bendahara pengeluaran memperbaiki dan mengunggah ulang \"{dok}\" yang sah.", s["nilai"], sekarang()))
                    catat(c, us, "Pemeriksaan selesai", sid, f"{sum(1 for v in cek.values() if v == 't')} temuan")
                else: catat(c, us, "Kertas kerja disimpan", sid)
                c.commit(); return self.kirim({"ok": True})
            raise Galat(404, "Aksi tidak dikenal.")
        finally: c.close()

    def api_temuan(self, us, m, seg):
        c = db()
        try:
            if m == "GET":
                q = "SELECT t.*, s.uraian spj_uraian FROM temuan t LEFT JOIN spj s ON s.id=t.spj_id"
                lk = akses.lingkup(c, us)
                rows = c.execute(q + " ORDER BY t.id") if us["peran"] in INSP else c.execute(q + " WHERE t.opd=? ORDER BY t.id", (us["opd"],))
                return self.kirim([dict(r) | {"tl_files": json.loads(r["tl_files"] or "[]")} for r in rows if us["peran"] not in INSP or akses.boleh(lk, r["opd"])])
            tid = int(seg[0]) if seg and seg[0].isdigit() else 0; aksi = seg[1] if len(seg) > 1 else ""
            t = c.execute("SELECT * FROM temuan WHERE id=?", (tid,)).fetchone()
            if not t: raise Galat(404, "Temuan tidak ditemukan.")
            if us["peran"] in INSP and not akses.boleh(akses.lingkup(c, us), t["opd"]): raise Galat(403, "Temuan di luar obrik yang ditugaskan kepada Anda.")
            b = self.jbody()
            if m == "PUT" and not aksi:
                if us["peran"] not in INSP: raise Galat(403, "Hanya Inspektorat.")
                if t["lhp_id"]:
                    st = c.execute("SELECT status FROM lhp WHERE id=?", (t["lhp_id"],)).fetchone()
                    if st and st["status"] != "draf": raise Galat(409, "LHP sudah diajukan; kembalikan ke draf untuk mengubah temuan.")
                f = {k: str(b.get(k, t[k]) or "") for k in ("judul", "uraian", "kriteria", "sebab", "akibat", "tanggapan", "rekomendasi")}
                if not f["uraian"].strip(): raise Galat(400, "Kondisi (uraian temuan) wajib diisi.")
                c.execute("UPDATE temuan SET judul=?, uraian=?, kriteria=?, sebab=?, akibat=?, tanggapan=?, rekomendasi=?, nilai_temuan=? WHERE id=?",
                          (f["judul"], f["uraian"], f["kriteria"], f["sebab"], f["akibat"], f["tanggapan"], f["rekomendasi"], int(b.get("nilai_temuan") or 0), tid))
                catat(c, us, "Ubah unsur temuan", t["spj_id"] or f"lhp:{t['lhp_id']}", f["judul"][:120]); c.commit(); return self.kirim({"ok": True})
            if m == "POST" and aksi == "tl":
                if us["peran"] not in ("bendahara", "pakpa") or us["opd"] != t["opd"]: raise Galat(403, "Hanya OPD terkait.")
                if t["status"] == "tuntas": raise Galat(409, "Temuan sudah tuntas.")
                ur = str(b.get("uraian", "")).strip()
                if not ur: raise Galat(400, "Uraikan tindak lanjut yang dilakukan.")
                c.execute("UPDATE temuan SET status='menunggu', tl_uraian=?, tl_files=?, tl_oleh=?, tl_tgl=? WHERE id=?",
                          (ur, json.dumps(b.get("files") or [], ensure_ascii=False), us["nama"], sekarang(), tid))
                catat(c, us, "Unggah tindak lanjut temuan", t["spj_id"], ur[:120]); c.commit(); return self.kirim({"ok": True})
            if m == "POST" and aksi == "verifikasi":
                if us["peran"] not in INSP: raise Galat(403, "Hanya Inspektorat.")
                h = b.get("hasil")
                if h not in ("tuntas", "belum"): raise Galat(400, "Hasil tidak valid.")
                c.execute("UPDATE temuan SET status=?, verif_oleh=?, verif_tgl=?, verif_catatan=? WHERE id=?",
                          ("tuntas" if h == "tuntas" else "belum", us["nama"], sekarang(), str(b.get("catatan", "")), tid))
                catat(c, us, "Verifikasi tindak lanjut: " + ("tuntas" if h == "tuntas" else "belum tuntas"), t["spj_id"], str(b.get("catatan", ""))); c.commit()
                return self.kirim({"ok": True})
            raise Galat(404, "Aksi tidak dikenal.")
        finally: c.close()

    # ---------- Laporan Hasil Audit (LHA/LHP)
    def api_lhp(self, us, m, seg):
        c = db()
        try:
            if m == "GET" and not seg:
                q = "SELECT l.*, o.nama opd_nama, (SELECT COUNT(*) FROM temuan t WHERE t.lhp_id=l.id) n_temuan FROM lhp l LEFT JOIN opd o ON o.kode=l.opd"
                lk = akses.lingkup(c, us)
                rows = c.execute(q + " ORDER BY l.id DESC") if us["peran"] in INSP else c.execute(q + " WHERE l.opd=? AND l.status='terbit' ORDER BY l.id DESC", (us["opd"],))
                return self.kirim([{k: r[k] for k in r.keys() if k != "data"} for r in rows if us["peran"] not in INSP or akses.boleh(lk, r["opd"])])
            if m == "POST" and not seg:
                if us["peran"] not in ("auditor", "ketua", "irban", "inspektur"): raise Galat(403, "Hanya Ketua Tim, auditor, Irban, atau Inspektur.")
                b = self.jbody(); o = c.execute("SELECT nama FROM opd WHERE kode=?", (b.get("opd"),)).fetchone()
                if not o: raise Galat(400, "Pilih perangkat daerah.")
                if not akses.boleh(akses.lingkup(c, us), b.get("opd")): raise Galat(403, "Perangkat daerah di luar obrik yang ditugaskan kepada Anda.")
                periode = str(b.get("periode") or "").strip() or f"Tahun Anggaran {datetime.date.today().year}"
                judul, data, tids = lhp.templat(c, b["opd"], o["nama"], periode, str(b.get("no_st", "")).strip(), us["nama"])
                c.execute("INSERT INTO lhp(opd,judul,periode,status,data,dibuat_oleh,dibuat,diubah) VALUES(?,?,?,'draf',?,?,?,?)",
                          (b["opd"], judul, periode, json.dumps(data, ensure_ascii=False), us["nama"], sekarang(), sekarang()))
                lid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                for t in tids: c.execute("UPDATE temuan SET lhp_id=?, judul=COALESCE(NULLIF(judul,''), dok || ' tidak sesuai ketentuan') WHERE id=?", (lid, t))
                catat(c, us, "Susun LHP baru", f"lhp:{lid}", judul[:120]); c.commit(); return self.kirim({"ok": True, "id": lid})
            lid = int(seg[0]) if seg and seg[0].isdigit() else 0
            r = c.execute("SELECT l.*, o.nama opd_nama FROM lhp l LEFT JOIN opd o ON o.kode=l.opd WHERE l.id=?", (lid,)).fetchone()
            if not r: raise Galat(404, "LHP tidak ditemukan.")
            if us["peran"] not in INSP and not (r["opd"] == us["opd"] and r["status"] == "terbit"): raise Galat(403, "Tidak berwenang.")
            if us["peran"] in INSP and not akses.boleh(akses.lingkup(c, us), r["opd"]): raise Galat(403, "LHA di luar obrik yang ditugaskan kepada Anda.")
            aksi = seg[1] if len(seg) > 1 else ""
            if m == "GET":
                tem = [dict(t) | {"tl_files": json.loads(t["tl_files"] or "[]")} for t in c.execute("SELECT * FROM temuan WHERE lhp_id=? ORDER BY id", (lid,))]
                spj = [dict(x) for x in c.execute("SELECT s.id, s.uraian, s.nilai, s.tgl, s.bku, a.tgl tgl_audit FROM spj s JOIN audit a ON a.spj_id=s.id WHERE s.opd=? AND a.status='selesai' ORDER BY s.id", (r["opd"],))]
                return self.kirim({k: r[k] for k in r.keys() if k != "data"} | {"data": json.loads(r["data"] or "{}"), "temuan": tem, "spj_diperiksa": spj})
            if us["peran"] not in INSP: raise Galat(403, "Hanya Inspektorat.")
            if m == "PUT" and not aksi:
                if r["status"] != "draf": raise Galat(409, "LHP sudah diajukan; kembalikan ke draf untuk mengubah.")
                b = self.jbody()
                c.execute("UPDATE lhp SET judul=?, periode=?, data=?, diubah=? WHERE id=?", (str(b.get("judul") or r["judul"]), str(b.get("periode") or r["periode"]),
                          json.dumps(b.get("data") or {}, ensure_ascii=False), sekarang(), lid))
                c.commit(); return self.kirim({"ok": True})
            if m == "POST" and aksi == "aksi":
                b = self.jbody(); x = b.get("aksi"); cat = str(b.get("catatan", "")).strip(); st = r["status"]
                if x == "ajukan":
                    if st != "draf": raise Galat(409, "LHP bukan draf.")
                    if us["peran"] not in ("auditor", "ketua", "irban", "inspektur"): raise Galat(403, "Tidak berwenang.")
                    c.execute("UPDATE lhp SET status='reviu', catatan=NULL, diubah=? WHERE id=?", (sekarang(), lid)); catat(c, us, "LHP diajukan untuk reviu", f"lhp:{lid}")
                elif x == "setujui" and st == "reviu":
                    if us["peran"] not in ("irban", "inspektur"): raise Galat(403, "Reviu dilakukan Inspektur Pembantu (Pengendali Teknis).")
                    c.execute("UPDATE lhp SET status='persetujuan', reviu_oleh=?, reviu_tgl=?, diubah=? WHERE id=?", (us["nama"], sekarang(), sekarang(), lid))
                    catat(c, us, "LHP direviu dan diteruskan ke Inspektur", f"lhp:{lid}", cat)
                elif x == "setujui" and st == "persetujuan":
                    if us["peran"] != "inspektur": raise Galat(403, "LHP ditandatangani oleh Inspektur.")
                    th = datetime.date.today(); n = c.execute("SELECT COUNT(*) FROM lhp WHERE status='terbit' AND substr(terbit_tgl,1,4)=?", (str(th.year),)).fetchone()[0] + 1
                    nomor = f"700.1.2.1/{n:03d}/{lhp.ROMAWI[th.month - 1]}/{th.year}"
                    c.execute("UPDATE lhp SET status='terbit', nomor=?, tgl=?, terbit_oleh=?, terbit_tgl=?, diubah=? WHERE id=?", (nomor, th.isoformat(), us["nama"], sekarang(), sekarang(), lid))
                    catat(c, us, "LHP disetujui dan diterbitkan", f"lhp:{lid}", nomor)
                elif x == "kembalikan":
                    if not cat: raise Galat(400, "Tuliskan catatan reviu.")
                    if not ((st == "reviu" and us["peran"] in ("irban", "inspektur")) or (st == "persetujuan" and us["peran"] == "inspektur")): raise Galat(403, "Tidak berwenang mengembalikan pada tahap ini.")
                    c.execute("UPDATE lhp SET status='draf', catatan=?, diubah=? WHERE id=?", (cat, sekarang(), lid)); catat(c, us, "LHP dikembalikan ke penyusun", f"lhp:{lid}", cat)
                else: raise Galat(409, "Aksi tidak sesuai tahap LHP.")
                c.commit(); return self.kirim({"ok": True})
            if m == "DELETE":
                if r["status"] != "draf": raise Galat(409, "Hanya draf yang dapat dihapus.")
                c.execute("UPDATE temuan SET lhp_id=NULL WHERE lhp_id=?", (lid,)); c.execute("DELETE FROM lhp WHERE id=?", (lid,)); catat(c, us, "Hapus draf LHP", f"lhp:{lid}"); c.commit()
                return self.kirim({"ok": True})
            raise Galat(404, "Aksi tidak dikenal.")
        finally: c.close()

    # ---------- SPJ GU (pengelompokan transaksi menjadi Ganti Uang, milik OPD)
    def api_gu(self, us, m, seg):
        c = db()
        try:
            lk = akses.lingkup(c, us) if us["peran"] in INSP else None
            def boleh_opd(o): return (us["peran"] in INSP and akses.boleh(lk, o)) or (us["peran"] in OPDR and us["opd"] == o)
            def isi(r):
                ids = json.loads(r["spj_ids"] or "[]"); rows = {x["id"]: x for x in ambil_spj(c, f"id IN ({','.join('?' * len(ids))})", ids)} if ids else {}
                pa = c.execute("SELECT nama, nip FROM users WHERE opd=? AND peran='pakpa' AND aktif=1 LIMIT 1", (r["opd"],)).fetchone()
                bd = c.execute("SELECT nama, nip FROM users WHERE opd=? AND peran='bendahara' AND aktif=1 LIMIT 1", (r["opd"],)).fetchone()
                o = c.execute("SELECT nama FROM opd WHERE kode=?", (r["opd"],)).fetchone()
                spj = [{k: rows[i][k] for k in ("id", "nama", "nilai", "bku", "tgl", "kode", "penerima", "st", "j", "mek")} for i in ids if i in rows]
                return dict(r) | {"spj_ids": ids, "spj": spj, "total": sum(x["nilai"] for x in spj), "opd_nama": o["nama"] if o else r["opd"],
                                  "pa": dict(pa) if pa else None, "bendahara": dict(bd) if bd else None}
            if m == "GET" and not seg:
                rows = c.execute("SELECT * FROM gu ORDER BY id DESC")
                return self.kirim([isi(r) for r in rows if boleh_opd(r["opd"])])
            if m == "GET" and seg and seg[0] == "kandidat":
                if us["peran"] != "bendahara": raise Galat(403, "Hanya bendahara.")
                dipakai = {i for r in c.execute("SELECT spj_ids FROM gu WHERE opd=?", (us["opd"],)) for i in json.loads(r["spj_ids"] or "[]")}
                jn = self.path.split("jenis=")[-1][:2] if "jenis=" in self.path else None
                return self.kirim([x for x in ambil_spj(c, "opd=? AND status IN ('diajukan','ppk','bendahara','dibayar')", (us["opd"],)) if x["id"] not in dipakai and (not jn or x["mek"] == jn)])
            def periksa(b, gid=None):
                if us["peran"] != "bendahara": raise Galat(403, "Hanya bendahara yang dapat menyusun pertanggungjawaban.")
                ids = [str(x) for x in (b.get("spj_ids") or [])]; jn = b.get("jenis") or "GU"
                if jn not in MEK: raise Galat(400, "Jenis pertanggungjawaban tidak valid.")
                if not str(b.get("nama", "")).strip(): raise Galat(400, "Isi nama pertanggungjawaban, misalnya GU I, TU 1, atau LS Maret.")
                if jn == "TU" and int(b.get("nilai_sp2d") or 0) <= 0: raise Galat(400, "Isi nilai TU yang diterima (SP2D TU).")
                if not ids: raise Galat(400, "Pilih minimal satu SPJ.")
                lain = {i for r in c.execute("SELECT id, spj_ids FROM gu WHERE opd=?", (us["opd"],)) if r["id"] != gid for i in json.loads(r["spj_ids"] or "[]")}
                for i in ids:
                    r = c.execute("SELECT opd, status, mekanisme FROM spj WHERE id=?", (i,)).fetchone()
                    if not r or r["opd"] != us["opd"]: raise Galat(403, f"SPJ {i} bukan milik OPD Anda.")
                    if RANK.get(r["status"], 0) < 1: raise Galat(400, f"SPJ {i} belum diajukan.")
                    if i in lain: raise Galat(400, f"SPJ {i} sudah masuk pertanggungjawaban lain.")
                    if (r["mekanisme"] or "GU") != jn: raise Galat(400, f"SPJ {i} bermekanisme {r['mekanisme'] or 'GU'}, tidak dapat masuk pertanggungjawaban {jn}.")
                return ids
            if m == "POST" and not seg:
                b = self.jbody(); ids = periksa(b)
                c.execute("INSERT INTO gu(opd,nama,tgl,spj_ids,status,dibuat_oleh,dibuat,diubah,jenis,no_sp2d,tgl_sp2d,nilai_sp2d,setor) VALUES(?,?,?,?,'draf',?,?,?,?,?,?,?,?)",
                          (us["opd"], str(b["nama"]).strip(), str(b.get("tgl") or datetime.date.today().isoformat()), json.dumps(ids), us["nama"], sekarang(), sekarang(),
                           b.get("jenis") or "GU", str(b.get("no_sp2d") or ""), str(b.get("tgl_sp2d") or ""), int(b.get("nilai_sp2d") or 0), int(b.get("setor") or 0)))
                gid = c.execute("SELECT last_insert_rowid()").fetchone()[0]; catat(c, us, "Susun SPJ GU", f"gu:{gid}", str(b["nama"])); c.commit(); return self.kirim({"ok": True, "id": gid})
            gid = int(seg[0]) if seg and seg[0].isdigit() else 0; r = c.execute("SELECT * FROM gu WHERE id=?", (gid,)).fetchone()
            if not r or not boleh_opd(r["opd"]): raise Galat(404, "SPJ GU tidak ditemukan.")
            aksi = seg[1] if len(seg) > 1 else ""
            if m == "GET": return self.kirim(isi(r))
            if r["status"] != "draf": raise Galat(409, "SPJ GU sudah final dan terkunci.")
            if m == "PUT":
                b = self.jbody(); ids = periksa(b, gid)
                if (b.get("jenis") or "GU") != (r["jenis"] or "GU"): raise Galat(400, "Jenis pertanggungjawaban tidak dapat diubah.")
                c.execute("UPDATE gu SET nama=?, tgl=?, spj_ids=?, diubah=?, no_sp2d=?, tgl_sp2d=?, nilai_sp2d=?, setor=? WHERE id=?",
                          (str(b["nama"]).strip(), str(b.get("tgl") or r["tgl"]), json.dumps(ids), sekarang(), str(b.get("no_sp2d") or ""), str(b.get("tgl_sp2d") or ""),
                           int(b.get("nilai_sp2d") or 0), int(b.get("setor") or 0), gid)); c.commit()
                return self.kirim({"ok": True})
            if m == "POST" and aksi == "final":
                if us["peran"] != "bendahara" or us["opd"] != r["opd"]: raise Galat(403, "Hanya bendahara OPD ini.")
                x = isi(r)
                if (r["jenis"] or "GU") == "TU":
                    selisih = (r["nilai_sp2d"] or 0) - x["total"] - (r["setor"] or 0)
                    if selisih != 0: raise Galat(400, f"TU belum seimbang: nilai TU {r['nilai_sp2d']:,} = SPJ {x['total']:,} + setor {r['setor'] or 0:,}; selisih {selisih:,}.".replace(",", "."))
                c.execute("UPDATE gu SET status='final', diubah=? WHERE id=?", (sekarang(), gid)); catat(c, us, f"Pertanggungjawaban {r['jenis'] or 'GU'} difinalkan", f"gu:{gid}", r["nama"]); c.commit()
                return self.kirim({"ok": True})
            if m == "DELETE":
                if us["peran"] != "bendahara" or us["opd"] != r["opd"]: raise Galat(403, "Hanya bendahara OPD ini.")
                c.execute("DELETE FROM gu WHERE id=?", (gid,)); catat(c, us, "Hapus draf SPJ GU", f"gu:{gid}", r["nama"]); c.commit(); return self.kirim({"ok": True})
            raise Galat(404, "Aksi tidak dikenal.")
        finally: c.close()

    # ---------- tabel sederhana (PKPT, agenda)
    def api_praaudit(self, us, m, seg):
        """Audit awal otomatis: jalankan aturan atas SPJ yang telah diajukan, lalu auditor menerima/menolak setiap draf temuan."""
        if us["peran"] not in INSP: raise Galat(403, "Hanya Inspektorat.")
        c = db()
        try:
            lk = akses.lingkup(c, us)
            if m == "GET" and not seg:
                rows = [dict(r) for r in c.execute("SELECT p.*, s.uraian spj_uraian, s.nilai spj_nilai, j.berkas jdih_berkas FROM praaudit p LEFT JOIN spj s ON s.id=p.spj_id "
                                                   "LEFT JOIN jdih j ON j.id=p.jdih_id ORDER BY p.spj_id, p.id")]
                return self.kirim({"hasil": [r for r in rows if akses.boleh(lk, r["opd"])], "aturan": audit_awal.DAFTAR})
            if m == "POST" and seg == ["jalankan"]:
                opd = str(self.jbody().get("opd") or "")
                spj = [r for r in c.execute("SELECT * FROM spj") if RANK.get(r["status"], 0) >= 1 and akses.boleh(lk, r["opd"]) and (not opd or r["opd"] == opd)]
                c.executemany("DELETE FROM praaudit WHERE spj_id=? AND status='baru'", [(r["id"],) for r in spj])
                sudah = {(r["spj_id"], r["aturan"], r["kondisi"]) for r in c.execute("SELECT spj_id, aturan, kondisi FROM praaudit")}
                baru = [h for h in audit_awal.periksa(c, spj) if (h["spj_id"], h["aturan"], h["kondisi"]) not in sudah]
                kol = ["spj_id", "opd", "aturan", "kategori", "tingkat", "judul", "kondisi", "kriteria", "jdih_id", "akibat", "rekomendasi", "nilai", "bukti"]
                c.executemany(f"INSERT INTO praaudit({','.join(kol)},status,dibuat) VALUES({','.join('?' * len(kol))},'baru',?)", [[h[k] for k in kol] + [sekarang()] for h in baru])
                catat(c, us, "Audit awal otomatis", "praaudit", f"{len(spj)} SPJ diperiksa, {len(baru)} draf temuan")
                c.commit(); return self.kirim({"ok": True, "spj": len(spj), "draf": len(baru)})
            pid = int(seg[0]) if seg and seg[0].isdigit() else 0; aksi = seg[1] if len(seg) > 1 else ""
            p = c.execute("SELECT * FROM praaudit WHERE id=?", (pid,)).fetchone()
            if not p: raise Galat(404, "Draf temuan tidak ditemukan.")
            if not akses.boleh(lk, p["opd"]): raise Galat(403, "Di luar obrik yang ditugaskan kepada Anda.")
            if m != "POST" or aksi not in ("terima", "tolak"): raise Galat(404, "Aksi tidak dikenal.")
            if p["status"] != "baru": raise Galat(409, "Draf ini sudah direviu.")
            b = self.jbody(); cat = str(b.get("catatan") or "").strip()[:1000]
            if aksi == "tolak":
                if not cat: raise Galat(400, "Tuliskan alasan draf temuan ditolak.")
                c.execute("UPDATE praaudit SET status='ditolak', reviu_oleh=?, reviu_tgl=?, catatan=? WHERE id=?", (us["nama"], sekarang(), cat, pid))
                catat(c, us, "Tolak draf temuan audit awal", p["spj_id"], cat[:120]); c.commit(); return self.kirim({"ok": True})
            kondisi = str(b.get("kondisi") or p["kondisi"]).strip()
            nt = int(b["nilai"]) if str(b.get("nilai", "")).isdigit() else p["nilai"]
            sn = c.execute("SELECT nilai FROM spj WHERE id=?", (p["spj_id"],)).fetchone()
            c.execute("INSERT INTO temuan(spj_id,opd,dok,uraian,rekomendasi,nilai,status,dibuat,judul,kriteria,akibat,nilai_temuan) VALUES(?,?,?,?,?,?,'belum',?,?,?,?,?)",
                      (p["spj_id"], p["opd"], p["judul"], kondisi, p["rekomendasi"], sn["nilai"] if sn else 0, sekarang(), p["judul"], p["kriteria"], p["akibat"], nt))
            tid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.execute("UPDATE praaudit SET status='diterima', temuan_id=?, reviu_oleh=?, reviu_tgl=?, catatan=? WHERE id=?", (tid, us["nama"], sekarang(), cat, pid))
            catat(c, us, "Terima draf temuan audit awal", p["spj_id"], p["judul"][:120]); c.commit()
            return self.kirim({"ok": True, "temuan_id": tid})
        finally: c.close()
    def api_jdih(self, us, m, seg, q):
        """JDIH Pengawasan: semua pengguna yang masuk dapat membaca; Admin/Inspektur/Irban mengelola."""
        if m == "GET" and not seg:
            c = db(); rows = [dict(r) for r in c.execute("SELECT * FROM jdih ORDER BY tingkat DESC, tahun DESC, jenis, id")]; c.close()
            return self.kirim(rows)
        if us["peran"] not in PENGELOLA: raise Galat(403, "Hanya Irban, Inspektur, atau Admin yang dapat mengelola JDIH.")
        if m == "POST" and seg == ["unggah"]:
            nm = re.sub(r"\.{2,}", "_", re.sub(r"[^A-Za-z0-9._-]+", "_", q.get("name", ["peraturan.pdf"])[0]))[-80:]
            data = self.body()
            if not nm.lower().endswith(".pdf") or data[:5] != b"%PDF-": raise Galat(400, "Hanya berkas PDF.")
            folder = os.path.join(UP, "JDIH"); os.makedirs(folder, exist_ok=True); fn = f"{int(time.time() * 1000)}_{nm}"
            with open(os.path.join(folder, fn), "wb") as f: f.write(data)
            return self.kirim({"path": f"berkas/JDIH/{fn}", "size": len(data)})
        c = db()
        try:
            if m in ("POST", "PUT"):
                b = self.jbody(); v = {k: str(b.get(k) or "").strip() for k in jdih.KOLOM}
                if not (v["jenis"] and v["nomor"] and v["judul"]): raise Galat(400, "Jenis, nomor, dan judul wajib diisi.")
                if not re.fullmatch(r"\d{4}", v["tahun"]) or not 1945 <= int(v["tahun"]) <= 2100: raise Galat(400, "Tahun tidak valid.")
                if v["status"] not in jdih.STATUS: raise Galat(400, "Status tidak valid.")
                if v["tgl"] and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v["tgl"]): raise Galat(400, "Tanggal tidak valid.")
                if v["berkas"] and not (re.fullmatch(r"(berkas|dokumen)/JDIH/[A-Za-z0-9._-]+\.pdf", v["berkas"]) and os.path.isfile(os.path.join(UP if v["berkas"].startswith("berkas/") else DOK, *v["berkas"].split("/")[1:]))):
                    raise Galat(400, "Berkas PDF tidak ditemukan. Unggah ulang berkasnya.")
                vals = [int(v["tahun"]) if k == "tahun" else v[k] for k in jdih.KOLOM]; judul = f"{v['jenis']} {v['nomor']}/{v['tahun']}"
                if m == "POST":
                    c.execute(f"INSERT INTO jdih({','.join(jdih.KOLOM)}) VALUES({','.join('?' * len(jdih.KOLOM))})", vals); nid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    catat(c, us, "Tambah JDIH", f"jdih:{nid}", judul)
                else:
                    if not seg or not seg[0].isdigit(): raise Galat(400, "Data tidak dikenal.")
                    nid = int(seg[0])
                    if not c.execute("UPDATE jdih SET " + ",".join(k + "=?" for k in jdih.KOLOM) + " WHERE id=?", vals + [nid]).rowcount: raise Galat(404, "Peraturan tidak ditemukan.")
                    catat(c, us, "Ubah JDIH", f"jdih:{nid}", judul)
                c.commit(); return self.kirim({"ok": True, "id": nid})
            if m == "DELETE" and seg and seg[0].isdigit():
                if not c.execute("DELETE FROM jdih WHERE id=?", (int(seg[0]),)).rowcount: raise Galat(404, "Peraturan tidak ditemukan.")
                catat(c, us, "Hapus JDIH", f"jdih:{seg[0]}"); c.commit(); return self.kirim({"ok": True})
            raise Galat(404, "Aksi tidak dikenal.")
        finally: c.close()
    def api_tabel(self, us, m, seg, tabel, kol):
        if us["peran"] not in INSP: raise Galat(403, "Hanya Inspektorat.")
        c = db()
        try:
            if m == "GET":
                rows = [dict(r) for r in c.execute(f"SELECT * FROM {tabel} ORDER BY " + ("tgl, jam" if tabel == "agenda" else "id"))]
                if tabel == "agenda":
                    for r in rows: r["tim"] = json.loads(r["tim"] or "[]")
                return self.kirim(rows)
            if us["peran"] not in PENGELOLA: raise Galat(403, "Hanya Irban, Inspektur, atau Admin yang dapat mengubah.")
            if m in ("POST", "PUT"):
                b = self.jbody(); vals = []
                for k in kol:
                    v = b.get(k)
                    if k == "tim": v = json.dumps(v or [], ensure_ascii=False)
                    if k in ("m1", "m2", "hari", "anggaran", "realisasi", "lama"): v = int(v or 0)
                    vals.append(v)
                if tabel == "pkpt" and not (1 <= vals[3] <= 12 and 1 <= vals[4] <= 12 and vals[3] <= vals[4]): raise Galat(400, "Jadwal bulan tidak valid.")
                if tabel == "agenda" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(b.get("tgl", ""))): raise Galat(400, "Tanggal tidak valid.")
                if m == "POST":
                    c.execute(f"INSERT INTO {tabel}({','.join(kol)}) VALUES({','.join('?' * len(kol))})", vals); nid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    catat(c, us, f"Tambah {tabel.upper()}", f"{tabel}:{nid}", str(vals[0])[:120])
                else:
                    nid = int(seg[0]); c.execute(f"UPDATE {tabel} SET {','.join(k + '=?' for k in kol)} WHERE id=?", vals + [nid])
                    catat(c, us, f"Ubah {tabel.upper()}", f"{tabel}:{nid}", str(vals[0])[:120])
                c.commit(); return self.kirim({"ok": True, "id": nid})
            if m == "DELETE" and seg:
                c.execute(f"DELETE FROM {tabel} WHERE id=?", (int(seg[0]),)); catat(c, us, f"Hapus {tabel.upper()}", f"{tabel}:{seg[0]}"); c.commit()
                return self.kirim({"ok": True})
            raise Galat(404, "Aksi tidak dikenal.")
        finally: c.close()

    # ---------- pengguna
    def api_users(self, us, m, seg):
        if us["peran"] != "admin" and not (m == "GET" and us["peran"] in PENGELOLA) and not (len(seg) > 1 and seg[1] == "penugasan" and us["peran"] in PENGELOLA): raise Galat(403, "Hanya Admin.")
        c = db()
        try:
            if m == "GET":
                tug = {}
                for r in c.execute("SELECT user_id, opd FROM penugasan"): tug.setdefault(r["user_id"], []).append(r["opd"])
                return self.kirim([{k: r[k] for k in ("id", "username", "nama", "nip", "jabatan", "peran", "opd", "aktif", "ganti")} | {"obrik": sorted(tug.get(r["id"], []))} for r in c.execute("SELECT * FROM users ORDER BY peran, opd, username")])
            b = self.jbody()
            if m == "PUT" and len(seg) > 1 and seg[1] == "penugasan":
                uid = int(seg[0]); u2 = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
                if not u2 or u2["peran"] not in akses.TERBATAS: raise Galat(400, "Penugasan obrik hanya untuk Ketua Tim dan Auditor.")
                valid = {r["kode"] for r in c.execute("SELECT kode FROM opd")}; ob = [o for o in (b.get("obrik") or []) if o in valid]
                c.execute("DELETE FROM penugasan WHERE user_id=?", (uid,)); c.executemany("INSERT INTO penugasan VALUES(?,?)", [(uid, o) for o in ob])
                catat(c, us, "Atur penugasan obrik", "Akun", f"{u2['username']}: {', '.join(ob) or '-'}"); c.commit(); return self.kirim({"ok": True})
            if m == "POST" and seg and seg[0] == "kartu":  # sandi awal unik + kartu akun untuk dibagikan
                ids = [int(i) for i in (b.get("ids") or [])]
                if not ids: raise Galat(400, "Pilih minimal satu akun.")
                if us["id"] in ids: raise Galat(400, "Akun Anda sendiri tidak dapat dibuatkan kartu.")
                hasil = [kartu(c, i) for i in ids]
                catat(c, us, "Buat sandi awal & kartu akun", "Akun", ", ".join(h["username"] for h in hasil)); c.commit()
                return self.kirim({"ok": True, "kartu": hasil})
            if m == "POST" and seg and len(seg) > 1 and seg[1] == "reset":
                k = kartu(c, int(seg[0])); catat(c, us, "Reset kata sandi", "Akun", k["username"]); c.commit()
                return self.kirim({"ok": True, "password": k["password"], "kartu": [k]})
            peran = b.get("peran")
            if peran not in INSP | OPDR: raise Galat(400, "Peran tidak valid.")
            if peran in OPDR and not c.execute("SELECT 1 FROM opd WHERE kode=?", (b.get("opd"),)).fetchone(): raise Galat(400, "Pilih perangkat daerah.")
            opd = b.get("opd") if peran in OPDR else None
            if m == "POST":
                un = str(b.get("username", "")).strip().lower()
                if not re.fullmatch(r"[a-z0-9._]{3,40}", un): raise Galat(400, "Nama pengguna 3–40 karakter: huruf kecil, angka, titik.")
                if c.execute("SELECT 1 FROM users WHERE username=?", (un,)).fetchone(): raise Galat(400, "Nama pengguna sudah dipakai.")
                c.execute("INSERT INTO users(username,nama,nip,jabatan,peran,opd,aktif,dibuat) VALUES(?,?,?,?,?,?,1,?)",
                          (un, b.get("nama"), b.get("nip"), b.get("jabatan"), peran, opd, sekarang()))
                k = kartu(c, c.execute("SELECT id FROM users WHERE username=?", (un,)).fetchone()["id"])
                catat(c, us, "Tambah pengguna", "Akun", un); c.commit(); return self.kirim({"ok": True, "password": k["password"], "kartu": [k]})
            if m == "PUT" and seg:
                c.execute("UPDATE users SET nama=?, nip=?, jabatan=?, peran=?, opd=?, aktif=? WHERE id=?",
                          (b.get("nama"), b.get("nip"), b.get("jabatan"), peran, opd, 1 if b.get("aktif", True) else 0, int(seg[0])))
                catat(c, us, "Ubah pengguna", "Akun", str(seg[0])); c.commit(); return self.kirim({"ok": True})
            raise Galat(404, "Aksi tidak dikenal.")
        finally: c.close()

# ------------------------------------------------------------------ cadangan harian
CADANGAN = os.environ.get("EAUDIT_CADANGAN") or os.path.join(os.path.dirname(ROOT), "eAudit-Cadangan")
def cadangkan():
    """Salin database (aman saat berjalan) + berkas unggahan baru; simpan 30 salinan DB terakhir."""
    os.makedirs(CADANGAN, exist_ok=True)
    tujuan = os.path.join(CADANGAN, f"eaudit-{datetime.date.today():%Y%m%d}.db")
    if not os.path.exists(tujuan):
        sem = tujuan + ".tmp"
        if os.path.exists(sem): os.remove(sem)
        src = sqlite3.connect(DBF); dst = sqlite3.connect(sem)
        try: src.backup(dst)
        finally: dst.close(); src.close()
        os.replace(sem, tujuan)
    for d, _, fs in os.walk(UP):
        for f in fs:
            a = os.path.join(d, f); b = os.path.join(CADANGAN, "unggahan", os.path.relpath(a, UP))
            if not os.path.exists(b): os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copy2(a, b)
    lama = sorted(f for f in os.listdir(CADANGAN) if re.match(r"eaudit-\d{8}\.db$", f))[:-30]
    for f in lama: os.remove(os.path.join(CADANGAN, f))
def jadwal_cadangan():
    while True:
        try: cadangkan()
        except Exception as e: print("Cadangan gagal:", e, flush=True)
        time.sleep(6 * 3600)

class Srv(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; allow_reuse_address = False  # Windows: cegah dua server berbagi port

if __name__ == "__main__":
    siapkan()
    if os.environ.get("EAUDIT_UJI") != "1" or os.environ.get("EAUDIT_CADANGAN"):
        threading.Thread(target=jadwal_cadangan, daemon=True).start()
    HOST = os.environ.get("EAUDIT_HOST", "127.0.0.1")  # 0.0.0.0 = dapat dibuka komputer lain di jaringan kantor
    print(f"e-Audit Konawe Selatan berjalan di http://localhost:{PORT}  |  Asisten AI: {'aktif' if ocr.AI else 'tidak aktif'}")
    if HOST != "127.0.0.1":
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as k: k.connect(("10.255.255.255", 1)); ip = k.getsockname()[0]
        except OSError: ip = "<alamat IP komputer ini>"
        print(f"Dari komputer lain di jaringan kantor buka: http://{ip}:{PORT}")
    print("Tutup jendela ini untuk menghentikan aplikasi.")
    try:
        srv = Srv((HOST, PORT), H)
    except OSError:
        print(f"Port {PORT} sedang dipakai aplikasi lain. Tutup aplikasi tersebut lalu jalankan ulang."); sys.exit(1)
    srv.serve_forever()
