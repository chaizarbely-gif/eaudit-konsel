"""Hak akses berbasis penugasan obrik (objek pemeriksaan = perangkat daerah).
- Administrator, Inspektur, dan Inspektur Pembantu (Irban): melihat seluruh obrik.
- Ketua Tim dan Auditor (anggota tim): hanya obrik yang ditugaskan kepadanya (tabel penugasan)."""

TERBATAS = {"auditor", "ketua"}
SKEMA = "CREATE TABLE IF NOT EXISTS penugasan(user_id INTEGER NOT NULL, opd TEXT NOT NULL, PRIMARY KEY(user_id, opd));"
TIM = [("ketua.tim1", "Ketua Tim Irban Wilayah I", ["PUPR", "DINKES"]),
       ("ketua.tim2", "Ketua Tim Irban Wilayah II", ["DIKBUD", "DINSOS", "BKAD"]),
       ("ketua.tim3", "Ketua Tim Irban Wilayah III", ["BAPPEDA", "KOMINFO", "SETDA"]),
       ("ketua.tim4", "Ketua Tim Irban Wilayah IV", ["PK"])]
ANGGOTA = {"auditor1": ["PUPR", "DINKES", "PK"], "auditor2": ["DIKBUD", "DINSOS", "BKAD", "BAPPEDA", "KOMINFO", "SETDA"]}

def migrasi(c, hash_pw, sekarang, sandi=None):
    import secrets
    sandi = sandi or "".join(secrets.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(10))
    c.executescript(SKEMA)
    if c.execute("SELECT COUNT(*) FROM penugasan").fetchone()[0]: return
    for un, nama, opds in TIM:
        if not c.execute("SELECT 1 FROM users WHERE username=?", (un,)).fetchone():
            s, h = hash_pw(sandi)
            c.execute("INSERT INTO users(username,nama,nip,jabatan,peran,opd,salt,hash,aktif,dibuat) VALUES(?,?,?,?,?,NULL,?,?,1,?)", (un, nama, "", "Ketua Tim", "ketua", s, h, sekarang()))
        uid = c.execute("SELECT id FROM users WHERE username=?", (un,)).fetchone()[0]
        for o in opds: c.execute("INSERT OR IGNORE INTO penugasan VALUES(?,?)", (uid, o))
    for un, opds in ANGGOTA.items():
        r = c.execute("SELECT id FROM users WHERE username=?", (un,)).fetchone()
        if r:
            for o in opds: c.execute("INSERT OR IGNORE INTO penugasan VALUES(?,?)", (r[0], o))

def lingkup(c, u):
    """None = seluruh obrik; set kode OPD = hanya obrik yang ditugaskan."""
    if u["peran"] not in TERBATAS: return None
    return {r[0] for r in c.execute("SELECT opd FROM penugasan WHERE user_id=?", (u["id"],))}

def boleh(lk, opd): return lk is None or opd in lk
