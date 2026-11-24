/* Menu samping portal OPD: hanya menu milik OPD pengguna, disusun menurut peran. */
(async () => {
  const nav = document.getElementById('navOPD'); if (!nav) return;
  const me = await API.me(); if (!me) return;
  const ic = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const I = { book: '<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v17H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 21.5A2.5 2.5 0 0 1 6.5 19H20v3H6.5"/><path d="M9 7h7M9 11h5"/>', grid: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    up: '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M4 20h16"/>', stack: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>', check: '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    lock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>', out: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>' };
  const MENU = {
    bendahara: [['/ringkasan.html', 'Ringkasan', 'grid'], ['/bendahara.html', 'Input & unggah SPJ', 'up'], ['/gu.html', 'Pertanggungjawaban GU/TU/LS', 'stack'], ['/lha-opd.html', 'LHA OPD', 'file'], ['/tindaklanjut.html', 'Tindak lanjut temuan', 'check'], ['/jdih.html', 'JDIH Pengawasan', 'book']],
    ppk: [['/ringkasan.html', 'Ringkasan', 'grid'], ['/verifikasi.html', 'Verifikasi SPJ', 'check'], ['/lha-opd.html', 'LHA OPD', 'file'], ['/jdih.html', 'JDIH Pengawasan', 'book']],
    pakpa: [['/ringkasan.html', 'Ringkasan', 'grid'], ['/verifikasi.html', 'Pengesahan SPJ', 'check'], ['/gu.html', 'Pertanggungjawaban GU/TU/LS', 'stack'], ['/lha-opd.html', 'LHA OPD', 'file'], ['/tindaklanjut.html', 'Tindak lanjut temuan', 'check'], ['/jdih.html', 'JDIH Pengawasan', 'book']] }[me.peran] || [];
  const p = location.pathname;
  nav.innerHTML = `<div class="grp">PORTAL OPD</div><div style="padding:0 10px 6px;color:#fff;font-weight:600;font-size:12.5px;line-height:1.35">${EA.esc(me.opd_nama || '')}</div>` +
    MENU.map(([h, n, i]) => `<a href="${h}" class="${p === h ? 'on' : ''}">${ic(I[i])}${n}</a>`).join('') +
    `<div class="grp">AKUN</div><a id="navGs">${ic(I.lock)}Ganti kata sandi</a><a onclick="API.logout()">${ic(I.out)}Keluar</a>`;
  document.getElementById('navGs').onclick = () => {
    const o = document.createElement('div');
    o.style.cssText = 'position:fixed;inset:0;background:rgba(15,25,40,.45);display:grid;place-items:center;z-index:50;padding:16px';
    o.innerHTML = `<div style="background:#fff;border-radius:14px;max-width:400px;width:100%;padding:18px;font-family:inherit;box-shadow:0 20px 50px rgba(0,0,0,.25)">
      <h3 style="margin:0 0 10px">Ganti kata sandi</h3>
      <label style="display:block;font-size:12px;font-weight:700;color:#677485">Kata sandi lama<input type="password" id="gsL" style="width:100%;border:1px solid #E3E8EF;border-radius:8px;padding:8px;margin:4px 0 10px;font:inherit"></label>
      <label style="display:block;font-size:12px;font-weight:700;color:#677485">Kata sandi baru (min. 8 karakter)<input type="password" id="gsB" style="width:100%;border:1px solid #E3E8EF;border-radius:8px;padding:8px;margin-top:4px;font:inherit"></label>
      <div id="gsE" style="color:#C8433A;font-size:12.5px;min-height:18px;margin-top:6px"></div>
      <div style="display:flex;justify-content:flex-end;gap:8px"><button class="btn btn-out" id="gsX">Batal</button><button class="btn btn-pri" id="gsS">Simpan</button></div></div>`;
    document.body.appendChild(o); const tutup = () => o.remove();
    o.onclick = e => { if (e.target === o) tutup() }; document.getElementById('gsX').onclick = tutup;
    document.getElementById('gsS').onclick = async () => { try { await API.post('/api/password', { lama: document.getElementById('gsL').value, baru: document.getElementById('gsB').value }); tutup(); alert('Kata sandi berhasil diganti.') } catch (e) { document.getElementById('gsE').textContent = e.message } };
  };
})();
