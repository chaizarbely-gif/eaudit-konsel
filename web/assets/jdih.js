/* JDIH Pengawasan Pemerintah Daerah Konawe Selatan — tampilan bersama portal Inspektorat & OPD.
   JDIH.tampil(elemen, { kelola: true/false }) */
window.JDIH = (function () {
  const esc = s => EA.esc(s);
  const ST = { berlaku: ['Berlaku', '#1F7A4D', '#E3F3E8'], diubah: ['Telah diubah', '#9A5B00', '#FFF1D6'], dicabut: ['Dicabut', '#B3261E', '#FDE3E1'], '': ['Belum dicek', '#5B6777', '#EEF1F5'] };
  const css = `.jd *{box-sizing:border-box}.jd{font-size:13.5px;color:#1D2733}
.jd-kpi{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:12px}
.jd-k{background:#fff;border:1px solid var(--line,#E3E8EF);border-radius:12px;padding:12px 14px}.jd-k b{display:block;font-size:22px;line-height:1.1}.jd-k span{color:#677485;font-size:12px}
.jd-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;background:#fff;border:1px solid var(--line,#E3E8EF);border-radius:12px;padding:10px;margin-bottom:12px}
.jd-bar input,.jd-bar select,.jd-f input,.jd-f select,.jd-f textarea{font:inherit;border:1px solid var(--line,#E3E8EF);border-radius:8px;padding:7px 9px;background:#fff;color:inherit;min-width:0}
.jd-bar input{flex:1 1 220px}.jd-bar select{flex:0 1 auto}
.jd-b{font:inherit;font-weight:600;border:1px solid var(--line,#E3E8EF);background:#fff;border-radius:8px;padding:7px 12px;cursor:pointer;color:inherit;text-decoration:none;white-space:nowrap;display:inline-block}
.jd-b.p{background:#1F5FAD;border-color:#1F5FAD;color:#fff}.jd-b.r{color:#B3261E}.jd-b:disabled{opacity:.5;cursor:default}
.jd-t{width:100%;border-collapse:separate;border-spacing:0;background:#fff;border:1px solid var(--line,#E3E8EF);border-radius:12px;overflow:hidden}
.jd-t th{text-align:left;font-size:11.5px;text-transform:uppercase;letter-spacing:.03em;color:#677485;background:#F6F8FB;padding:9px 12px}
.jd-t td{padding:10px 12px;border-top:1px solid #EEF1F5;vertical-align:top}.jd-t td.a{text-align:right;white-space:nowrap}
.jd-n{font-weight:700}.jd-s{color:#677485;font-size:12px;margin-top:3px}
.jd-p{display:inline-block;border-radius:99px;padding:2px 9px;font-size:11.5px;font-weight:700;white-space:nowrap}
.jd-c{display:inline-block;border-radius:6px;padding:2px 7px;font-size:11.5px;background:#EEF3FA;color:#1F4E89;margin-top:4px}
.jd-x{text-align:center;color:#677485;padding:36px!important}
.jd-o{position:fixed;inset:0;background:rgba(15,25,40,.45);display:grid;place-items:center;z-index:60;padding:16px}
.jd-m{background:#fff;border-radius:14px;width:100%;max-width:640px;max-height:92vh;overflow:auto;padding:18px;box-shadow:0 20px 50px rgba(0,0,0,.25)}
.jd-m h3{margin:0 0 12px}.jd-f{display:grid;grid-template-columns:1fr 1fr;gap:10px}.jd-f label{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:700;color:#677485}.jd-f .w2{grid-column:1/-1}
.jd-e{color:#B3261E;font-size:12.5px;min-height:18px;margin-top:8px}.jd-ft{display:flex;gap:8px;justify-content:flex-end;margin-top:8px;flex-wrap:wrap}.jd-ft .sp{flex:1}
@media (max-width:720px){.jd-kpi{grid-template-columns:1fr 1fr}.jd-t thead{display:none}.jd-t,.jd-t tbody,.jd-t tr,.jd-t td{display:block;width:100%}.jd-t tr{border-top:1px solid #EEF1F5;padding:6px 0}.jd-t td{border:0;padding:4px 12px}.jd-t td.a{text-align:left}.jd-f{grid-template-columns:1fr}}`;
  let R = [], F = { q: '', tingkat: '', bidang: '', jenis: '', status: '*' }, EL, KELOLA;

  const pill = s => { const x = ST[s] || ST['']; return `<span class="jd-p" style="color:${x[1]};background:${x[2]}">${x[0]}</span>` };
  const opsi = (arr, pilih, semua) => `<option value="">${semua}</option>` + arr.map(v => `<option ${v === pilih ? 'selected' : ''}>${esc(v)}</option>`).join('');
  const uniq = k => [...new Set(R.map(r => r[k]).filter(Boolean))].sort();
  const cocok = r => (!F.tingkat || r.tingkat === F.tingkat) && (!F.bidang || r.bidang === F.bidang) && (!F.jenis || r.jenis === F.jenis) && (F.status === '*' || (r.status || '') === F.status) &&
    (!F.q || `${r.jenis} ${r.nomor} ${r.tahun} ${r.judul} ${r.ket || ''}`.toLowerCase().includes(F.q.toLowerCase()));

  function gambar() {
    const L = R.filter(cocok);
    EL.innerHTML = `<div class="jd">
      <div class="jd-kpi"><div class="jd-k"><b>${R.length}</b><span>Peraturan tercatat</span></div><div class="jd-k"><b>${R.filter(r => r.tingkat === 'Daerah').length}</b><span>Produk hukum daerah</span></div>
        <div class="jd-k"><b>${R.filter(r => r.tingkat === 'Pusat').length}</b><span>Peraturan pusat</span></div><div class="jd-k"><b>${R.filter(r => r.berkas).length}</b><span>Dengan berkas PDF</span></div></div>
      <div class="jd-bar"><input id="jdQ" placeholder="Cari nomor, tahun, atau judul peraturan…" value="${esc(F.q)}">
        <select data-f="tingkat">${opsi(uniq('tingkat'), F.tingkat, 'Semua tingkat')}</select><select data-f="jenis">${opsi(uniq('jenis'), F.jenis, 'Semua jenis')}</select>
        <select data-f="bidang">${opsi(uniq('bidang'), F.bidang, 'Semua bidang')}</select>
        <select data-f="status"><option value="*">Semua status</option>${Object.entries(ST).map(([k, v]) => `<option value="${k}" ${F.status === k ? 'selected' : ''}>${v[0]}</option>`).join('')}</select>
        ${KELOLA ? '<button class="jd-b p" id="jdAdd">+ Tambah peraturan</button>' : ''}</div>
      <table class="jd-t"><thead><tr><th>Peraturan</th><th>Tentang</th><th>Status</th><th></th></tr></thead><tbody>
      ${L.map(r => `<tr><td style="min-width:170px"><div class="jd-n">${esc(r.jenis)}</div><div class="jd-s">Nomor ${esc(r.nomor)} Tahun ${esc(r.tahun)} · ${esc(r.tingkat || '')}</div></td>
        <td><div>${esc(r.judul)}</div>${r.bidang ? `<span class="jd-c">${esc(r.bidang)}</span>` : ''}${r.ket ? `<div class="jd-s">${esc(r.ket)}</div>` : ''}</td>
        <td>${pill(r.status || '')}</td>
        <td class="a">${r.berkas ? `<a class="jd-b" href="/${esc(r.berkas)}" target="_blank" rel="noopener">📄 Buka PDF</a>` : '<span class="jd-s">Belum ada berkas</span>'}${KELOLA ? ` <button class="jd-b" data-je="${r.id}">Ubah</button>` : ''}</td></tr>`).join('')
        || `<tr><td colspan="4" class="jd-x">${R.length ? 'Tidak ada peraturan yang cocok dengan pencarian.' : 'Belum ada peraturan.'}</td></tr>`}
      </tbody></table><p class="jd-s" style="margin-top:10px">Status "Belum dicek" berarti keberlakuan peraturan belum diverifikasi dengan sumber resmi (JDIH Kementerian/Lembaga atau Bagian Hukum Setda).</p></div>`;
    const q = EL.querySelector('#jdQ'); q.oninput = () => { F.q = q.value; const pos = q.selectionStart; gambar(); const n = EL.querySelector('#jdQ'); n.focus(); n.setSelectionRange(pos, pos) };
    EL.querySelectorAll('[data-f]').forEach(s => s.onchange = () => { F[s.dataset.f] = s.value; gambar() });
    if (KELOLA) { EL.querySelector('#jdAdd').onclick = () => form({}); EL.querySelectorAll('[data-je]').forEach(b => b.onclick = () => form(R.find(r => r.id === +b.dataset.je))) }
  }

  function form(r) {
    const o = document.createElement('div'); o.className = 'jd-o';
    const dl = (id, k) => `<datalist id="${id}">${uniq(k).map(v => `<option>${esc(v)}</option>`).join('')}</datalist>`;
    o.innerHTML = `<div class="jd-m jd"><h3>${r.id ? 'Ubah peraturan' : 'Tambah peraturan'}</h3><div class="jd-f">
      <label>Jenis<input id="fJ" list="dlJ" value="${esc(r.jenis)}" placeholder="Peraturan Bupati">${dl('dlJ', 'jenis')}</label>
      <label>Tingkat<select id="fT">${['Daerah', 'Pusat'].map(v => `<option ${v === r.tingkat ? 'selected' : ''}>${v}</option>`).join('')}</select></label>
      <label>Nomor<input id="fN" value="${esc(r.nomor)}"></label><label>Tahun<input id="fY" inputmode="numeric" maxlength="4" value="${esc(r.tahun || new Date().getFullYear())}"></label>
      <label class="w2">Tentang (judul)<textarea id="fU" rows="3">${esc(r.judul)}</textarea></label>
      <label>Bidang<input id="fB" list="dlB" value="${esc(r.bidang)}">${dl('dlB', 'bidang')}</label>
      <label>Status<select id="fS">${Object.entries(ST).map(([k, v]) => `<option value="${k}" ${(r.status || '') === k ? 'selected' : ''}>${v[0]}</option>`).join('')}</select></label>
      <label>Tanggal ditetapkan (opsional)<input id="fD" type="date" value="${esc(r.tgl)}"></label>
      <label>Berkas PDF (maks. 20 MB)<input id="fF" type="file" accept="application/pdf,.pdf"><span class="jd-s" id="fFi">${r.berkas ? 'Tersimpan: ' + esc(r.berkas.split('/').pop()) : 'Belum ada berkas'}</span></label>
      <label class="w2">Keterangan (mis. diubah/dicabut dengan …)<input id="fK" value="${esc(r.ket)}"></label></div>
      <div class="jd-e" id="fE"></div>
      <div class="jd-ft">${r.id ? '<button class="jd-b r" id="fDel">Hapus</button>' : ''}<span class="sp"></span><button class="jd-b" id="fX">Batal</button><button class="jd-b p" id="fOk">Simpan</button></div></div>`;
    document.body.appendChild(o);
    const $ = id => o.querySelector('#' + id), tutup = () => o.remove(), salah = t => $('fE').textContent = t;
    o.onclick = e => { if (e.target === o) tutup() }; $('fX').onclick = tutup;
    let berkas = r.berkas || '';
    $('fOk').onclick = async () => {
      $('fOk').disabled = true; salah('');
      try {
        const f = $('fF').files[0];
        if (f) {
          if (f.size > 20 * 1024 * 1024) throw new Error('Berkas lebih dari 20 MB.');
          $('fFi').textContent = 'Mengunggah…';
          const x = await fetch('/api/jdih/unggah?name=' + encodeURIComponent(f.name), { method: 'POST', body: f, credentials: 'same-origin' });
          const j = await x.json().catch(() => ({})); if (!x.ok) throw new Error(j.error || 'Gagal mengunggah berkas.'); berkas = j.path;
        }
        const b = { jenis: $('fJ').value, tingkat: $('fT').value, nomor: $('fN').value, tahun: $('fY').value, judul: $('fU').value, bidang: $('fB').value, status: $('fS').value, tgl: $('fD').value, ket: $('fK').value, berkas };
        r.id ? await API.put('/api/jdih/' + r.id, b) : await API.post('/api/jdih', b);
        tutup(); await muat();
      } catch (e) { salah(e.message); $('fOk').disabled = false }
    };
    if (r.id) $('fDel').onclick = async () => { if (!confirm('Hapus peraturan ini dari JDIH?')) return; try { await API.del('/api/jdih/' + r.id); tutup(); await muat() } catch (e) { salah(e.message) } };
  }

  async function muat() { R = await API.get('/api/jdih'); gambar() }
  async function tampil(el, o) {
    if (!document.getElementById('jdCss')) { const s = document.createElement('style'); s.id = 'jdCss'; s.textContent = css; document.head.appendChild(s) }
    EL = el; KELOLA = !!(o && o.kelola);
    try { await muat() } catch (e) { el.innerHTML = `<div class="jd-x">Gagal memuat JDIH: ${esc(e.message)}</div>` }
  }
  return { tampil };
})();
