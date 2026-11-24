/* Pustaka bersama e-Audit Konawe Selatan: akses API, konstanta, format angka. */
window.API = {
  async req(m, url, body) {
    const o = { method: m, headers: {}, credentials: 'same-origin', cache: 'no-store' };
    if (body !== undefined) { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(body) }
    const r = await fetch(url, o); let j = null; try { j = await r.json() } catch (e) { }
    if (r.status === 401) { location.href = '/login.html'; throw new Error('Sesi berakhir, silakan masuk kembali.') }
    if (r.status === 403 && j && j.ganti) { location.href = '/login.html#ganti'; throw new Error(j.error) }
    if (!r.ok) throw new Error((j && j.error) || ('Gagal (' + r.status + ')'));
    return j;
  },
  get(u) { return this.req('GET', u) }, post(u, b) { return this.req('POST', u, b || {}) }, put(u, b) { return this.req('PUT', u, b || {}) }, del(u) { return this.req('DELETE', u) },
  async me() { try { return await this.get('/api/me') } catch (e) { return null } },
  async logout() { try { await this.post('/api/logout') } catch (e) { } location.href = '/login.html' },
};
window.EA = (function () {
  const BLN = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
  const JENIS = {
    HON: { n: 'Honorarium Narasumber', docs: ['Undangan', 'Daftar hadir', 'Daftar penerima honor', 'Resume kegiatan', 'Kuitansi'] },
    SPPD: { n: 'Perjalanan Dinas', docs: ['Surat tugas', 'SPPD', 'Bukti transportasi', 'Bukti penginapan', 'Laporan perjalanan'] },
    BRG: { n: 'Belanja Barang', docs: ['SPK / kontrak', 'Faktur / kuitansi', 'BAST', 'Foto barang'] },
    KON: { n: 'Konstruksi (termin)', docs: ['Kontrak', 'Laporan progres fisik', 'BA pemeriksaan', 'Foto progres', 'Kuitansi'] },
    MMR: { n: 'Makan Minum Rapat', docs: ['Undangan', 'Daftar hadir', 'Kuitansi', 'Foto kegiatan'] },
    PDGU: { n: 'Perjalanan Dinas (GU)', docs: ['Tanda Bukti Kas', 'Surat Tugas', 'SPPD', 'Laporan Hasil Perjalanan', 'Rincian Biaya Perjalanan'] },
    BLGU: { n: 'Belanja Lainnya (GU)', docs: ['Tanda Bukti Kas'] } };
  const ST = { draf: ['Draf', 'p-grey', 0], kembali: ['Dikembalikan', 'p-red', 0], diajukan: ['Menunggu PPK', 'p-blue', 1],
    ppk: ['Menunggu PA/KPA', 'p-teal', 2], bendahara: ['Disahkan · siap SP2D', 'p-amber', 3], dibayar: ['SP2D terbit', 'p-green', 4] };
  const MEK = { GU: 'UP/GU', TU: 'TU', LS: 'LS' };
  const PERAN = { admin: 'Administrator', inspektur: 'Inspektur', irban: 'Inspektur Pembantu', ketua: 'Ketua Tim', auditor: 'Auditor (anggota tim)', bendahara: 'Bendahara', ppk: 'PPK', pakpa: 'PA/KPA' };
  const rp = v => 'Rp ' + Math.round(v || 0).toLocaleString('id-ID');
  const rpS = v => v >= 1e9 ? 'Rp ' + (v / 1e9).toFixed(2).replace('.', ',') + ' M' : v >= 1e6 ? 'Rp ' + (v / 1e6).toFixed(1).replace('.', ',') + ' jt' : rp(v);
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const tgl = iso => { if (!iso) return ''; const d = new Date(iso); return isNaN(d) ? iso : d.getDate() + ' ' + BLN[d.getMonth()] + ' ' + d.getFullYear() };
  const E = { BLN, JENIS, ST, MEK, PERAN, rp, rpS, esc, tgl, NOW_M: new Date().getMonth() + 1, OPD: [], OPDN: {}, MON: [] };
  E.init = ref => { E.OPD = ref.opd.map(o => ({ k: o.kode, n: o.nama })); E.OPDN = Object.fromEntries(E.OPD.map(o => [o.k, o.n])); E.MON = ref.monalisa; E.NOW_M = ref.now_m || E.NOW_M; return E };
  return E;
})();
