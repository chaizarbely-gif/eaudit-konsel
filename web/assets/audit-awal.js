/* Audit awal otomatis (portal Inspektorat): jalankan aturan, reviu draf temuan (terima -> temuan resmi / tolak + alasan).
   AUDITAWAL.tampil(elemen, { opd: [{k, n}] }) */
window.AUDITAWAL = (function () {
  const esc = s => EA.esc(s), rp = v => EA.rp(v);
  const css = `.aa *{box-sizing:border-box}.aa{font-size:13.5px;color:#1D2733}
.aa-kpi{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-bottom:12px}
.aa-k{background:#fff;border:1px solid var(--line,#E3E8EF);border-radius:12px;padding:12px 14px}.aa-k b{display:block;font-size:21px;line-height:1.15}.aa-k span{color:#677485;font-size:12px}
.aa-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;background:#fff;border:1px solid var(--line,#E3E8EF);border-radius:12px;padding:10px;margin-bottom:12px}
.aa-bar input,.aa-bar select,.aa-m textarea,.aa-m input{font:inherit;border:1px solid var(--line,#E3E8EF);border-radius:8px;padding:7px 9px;background:#fff;color:inherit;min-width:0}
.aa-bar input{flex:1 1 200px}
.aa-b{font:inherit;font-weight:600;border:1px solid var(--line,#E3E8EF);background:#fff;border-radius:8px;padding:7px 12px;cursor:pointer;color:inherit;text-decoration:none;white-space:nowrap;display:inline-block}
.aa-b.p{background:#1F5FAD;border-color:#1F5FAD;color:#fff}.aa-b.g{background:#1F7A4D;border-color:#1F7A4D;color:#fff}.aa-b.r{color:#B3261E}.aa-b:disabled{opacity:.5;cursor:default}
.aa-c{background:#fff;border:1px solid var(--line,#E3E8EF);border-radius:12px;padding:14px 16px;margin-bottom:10px}
.aa-c h4{margin:6px 0 6px;font-size:14.5px}.aa-r{display:grid;grid-template-columns:110px 1fr;gap:4px 12px;font-size:13px;margin-top:6px}.aa-r dt{color:#677485;font-weight:700;font-size:12px}.aa-r dd{margin:0}
.aa-p{display:inline-block;border-radius:99px;padding:2px 9px;font-size:11.5px;font-weight:700;margin-right:4px;white-space:nowrap}
.aa-s{color:#677485;font-size:12px}.aa-f{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;margin-top:10px;align-items:center}.aa-f .sp{flex:1}
.aa-x{text-align:center;color:#677485;padding:36px;background:#fff;border:1px dashed var(--line,#E3E8EF);border-radius:12px}
.aa-o{position:fixed;inset:0;background:rgba(15,25,40,.45);display:grid;place-items:center;z-index:60;padding:16px}
.aa-m{background:#fff;border-radius:14px;width:100%;max-width:620px;max-height:92vh;overflow:auto;padding:18px;box-shadow:0 20px 50px rgba(0,0,0,.25)}
.aa-m h3{margin:0 0 10px}.aa-m label{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:700;color:#677485;margin-bottom:10px}.aa-e{color:#B3261E;font-size:12.5px;min-height:18px}
.aa details{background:#fff;border:1px solid var(--line,#E3E8EF);border-radius:12px;padding:10px 14px;margin-bottom:12px}.aa summary{cursor:pointer;font-weight:700}
@media (max-width:720px){.aa-kpi{grid-template-columns:1fr 1fr}.aa-r{grid-template-columns:1fr}}`;
  const TK = { temuan: ['Temuan', '#B3261E', '#FDE3E1'], cek: ['Perlu dicek', '#9A5B00', '#FFF1D6'] };
  const SR = { baru: ['Menunggu reviu', '#1F4E89', '#E4EEF9'], diterima: ['Diterima → temuan', '#1F7A4D', '#E3F3E8'], ditolak: ['Ditolak', '#5B6777', '#EEF1F5'] };
  const pill = x => `<span class="aa-p" style="color:${x[1]};background:${x[2]}">${x[0]}</span>`;
  let D = { hasil: [], aturan: {} }, EL, OPD = [], F = { st: 'baru', kat: '', at: '', opd: '', q: '' };

  function gambar() {
    const H = D.hasil, B = H.filter(h => h.status === 'baru');
    const L = H.filter(h => (F.st === '*' || h.status === F.st) && (!F.kat || h.kategori === F.kat) && (!F.at || h.aturan === F.at) && (!F.opd || h.opd === F.opd) &&
      (!F.q || `${h.spj_id} ${h.judul} ${h.kondisi}`.toLowerCase().includes(F.q.toLowerCase())));
    const spjN = new Set(B.map(h => h.spj_id)).size;
    EL.innerHTML = `<div class="aa">
      <div class="aa-kpi"><div class="aa-k"><b>${B.length}</b><span>Draf menunggu reviu (${spjN} SPJ)</span></div>
        <div class="aa-k"><b>${B.filter(h => h.tingkat === 'temuan').length}</b><span>Bukti cukup (temuan)</span></div><div class="aa-k"><b>${B.filter(h => h.tingkat === 'cek').length}</b><span>Perlu dicek auditor</span></div>
        <div class="aa-k"><b>${H.filter(h => h.status === 'diterima').length}</b><span>Diterima jadi temuan</span></div><div class="aa-k"><b>${EA.rpS(B.filter(h => h.tingkat === 'temuan').reduce((a, h) => a + (h.nilai || 0), 0))}</b><span>Nilai draf bukti cukup</span></div></div>
      <details><summary>Aturan yang diperiksa (${Object.keys(D.aturan).length})</summary><ul style="margin:8px 0 0 18px;padding:0">${Object.entries(D.aturan).map(([k, v]) => `<li><b>${k}</b> · ${esc(v)}</li>`).join('')}</ul>
        <p class="aa-s">Hasil audit awal adalah <b>draf</b>. Setiap draf wajib direviu auditor dengan memeriksa bukti aslinya sebelum diterima menjadi temuan. "Perlu dicek" berarti datanya berasal dari OCR atau indikasi yang belum pasti.</p></details>
      <div class="aa-bar"><button class="aa-b p" id="aaRun">▶ Jalankan audit awal</button><select id="aaOpdRun"><option value="">Semua obrik yang diajukan</option>${OPD.map(o => `<option value="${o.k}">${esc(o.n)}</option>`).join('')}</select>
        <span class="aa-s" id="aaMsg"></span></div>
      <div class="aa-bar"><input id="aaQ" placeholder="Cari nomor SPJ atau isi temuan…" value="${esc(F.q)}">
        <select data-f="st">${[['baru', 'Menunggu reviu'], ['diterima', 'Diterima'], ['ditolak', 'Ditolak'], ['*', 'Semua status']].map(([k, n]) => `<option value="${k}" ${F.st === k ? 'selected' : ''}>${n}</option>`).join('')}</select>
        <select data-f="kat"><option value="">Semua kategori</option>${['Penatausahaan', 'Ketaatan'].map(k => `<option ${F.kat === k ? 'selected' : ''}>${k}</option>`).join('')}</select>
        <select data-f="at"><option value="">Semua aturan</option>${Object.entries(D.aturan).map(([k, v]) => `<option value="${k}" ${F.at === k ? 'selected' : ''}>${k} · ${esc(v)}</option>`).join('')}</select>
        <select data-f="opd"><option value="">Semua OPD</option>${[...new Set(H.map(h => h.opd))].map(k => `<option value="${k}" ${F.opd === k ? 'selected' : ''}>${esc(EA.OPDN[k] || k)}</option>`).join('')}</select></div>
      ${L.map(h => `<div class="aa-c">${pill([h.kategori, '#1F4E89', '#EEF3FA'])}${pill(TK[h.tingkat] || TK.cek)}${pill(SR[h.status])}<span class="aa-s"> · ${esc(h.aturan)} · <a href="#kk/${esc(h.spj_id)}">${esc(h.spj_id)}</a> · ${esc(EA.OPDN[h.opd] || h.opd)}</span>
        <h4>${esc(h.judul)}</h4><dl class="aa-r"><dt>Kondisi</dt><dd>${esc(h.kondisi)}</dd>
        <dt>Kriteria</dt><dd>${esc(h.kriteria)}${h.jdih_berkas ? ` <a href="/${esc(h.jdih_berkas)}" target="_blank" rel="noopener">📄 buka peraturan</a>` : h.jdih_id ? ' <span class="aa-s">(PDF belum diunggah ke JDIH)</span>' : ''}</dd>
        <dt>Akibat</dt><dd>${esc(h.akibat)}</dd><dt>Rekomendasi</dt><dd>${esc(h.rekomendasi)}</dd>
        ${h.nilai ? `<dt>Nilai</dt><dd><b>${rp(h.nilai)}</b></dd>` : ''}${h.bukti ? `<dt>Bukti</dt><dd>${esc(h.bukti)}</dd>` : ''}
        ${h.status !== 'baru' ? `<dt>Reviu</dt><dd>${esc(h.reviu_oleh || '')} · ${esc(EA.tgl(h.reviu_tgl))}${h.catatan ? ' — ' + esc(h.catatan) : ''}</dd>` : ''}</dl>
        ${h.status === 'baru' ? `<div class="aa-f"><span class="sp"></span><button class="aa-b r" data-tolak="${h.id}">Tolak</button><button class="aa-b g" data-terima="${h.id}">Terima jadi temuan</button></div>` : ''}</div>`).join('')
        || `<div class="aa-x">${H.length ? 'Tidak ada draf yang cocok dengan saringan.' : 'Belum ada hasil. Klik "Jalankan audit awal" untuk memeriksa SPJ yang telah diajukan.'}</div>`}</div>`;
    const q = EL.querySelector('#aaQ'); q.oninput = () => { F.q = q.value; const p = q.selectionStart; gambar(); const n = EL.querySelector('#aaQ'); n.focus(); n.setSelectionRange(p, p) };
    EL.querySelectorAll('[data-f]').forEach(s => s.onchange = () => { F[s.dataset.f] = s.value; gambar() });
    EL.querySelector('#aaRun').onclick = async e => {
      e.target.disabled = true; EL.querySelector('#aaMsg').textContent = 'Memeriksa SPJ…';
      try { const r = await API.post('/api/praaudit/jalankan', { opd: EL.querySelector('#aaOpdRun').value }); F.st = 'baru'; await muat(); EL.querySelector('#aaMsg').textContent = `${r.spj} SPJ diperiksa · ${r.draf} draf temuan baru` }
      catch (x) { EL.querySelector('#aaMsg').textContent = x.message; e.target.disabled = false }
    };
    EL.querySelectorAll('[data-terima]').forEach(b => b.onclick = () => reviu(H.find(h => h.id === +b.dataset.terima), true));
    EL.querySelectorAll('[data-tolak]').forEach(b => b.onclick = () => reviu(H.find(h => h.id === +b.dataset.tolak), false));
  }

  function reviu(h, terima) {
    const o = document.createElement('div'); o.className = 'aa-o';
    o.innerHTML = `<div class="aa-m aa"><h3>${terima ? 'Terima sebagai temuan' : 'Tolak draf temuan'}</h3><p class="aa-s" style="margin-top:0">${esc(h.spj_id)} · ${esc(h.judul)}</p>
      ${terima ? `<label>Kondisi (sesuaikan dengan hasil pemeriksaan bukti asli)<textarea id="rK" rows="4">${esc(h.kondisi)}</textarea></label><label>Nilai temuan (Rp)<input id="rN" inputmode="numeric" value="${h.nilai || 0}"></label>` : ''}
      <label>${terima ? 'Catatan reviu (opsional)' : 'Alasan ditolak (wajib)'}<textarea id="rC" rows="3"></textarea></label><div class="aa-e" id="rE"></div>
      <div class="aa-f"><span class="sp"></span><button class="aa-b" id="rX">Batal</button><button class="aa-b ${terima ? 'g' : 'r'}" id="rY">${terima ? 'Terima' : 'Tolak'}</button></div></div>`;
    document.body.appendChild(o); const $ = id => o.querySelector('#' + id), tutup = () => o.remove();
    o.onclick = e => { if (e.target === o) tutup() }; $('rX').onclick = tutup;
    $('rY').onclick = async () => {
      $('rY').disabled = true;
      try {
        const b = { catatan: $('rC').value }; if (terima) { b.kondisi = $('rK').value; b.nilai = String($('rN').value).replace(/\D/g, '') }
        await API.post(`/api/praaudit/${h.id}/${terima ? 'terima' : 'tolak'}`, b); tutup(); await muat();
      } catch (e) { $('rE').textContent = e.message; $('rY').disabled = false }
    };
  }

  async function muat() { D = await API.get('/api/praaudit'); gambar() }
  async function tampil(el, o) {
    if (!document.getElementById('aaCss')) { const s = document.createElement('style'); s.id = 'aaCss'; s.textContent = css; document.head.appendChild(s) }
    EL = el; OPD = (o && o.opd) || [];
    try { await muat() } catch (e) { el.innerHTML = `<div class="aa-x">Gagal memuat audit awal: ${esc(e.message)}</div>` }
  }
  return { tampil };
})();
