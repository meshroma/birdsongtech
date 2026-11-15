/* birdsongtech - animazione della migrazione in una finestra sopra la pagina.
   Uso: BSMigrazione.apri('ciconia ciconia')  (le specie disponibili sono in data/migrazioni/indice.js)
   Ogni punto e' un individuo seguito via satellite; la scia mostra gli ultimi giorni di viaggio. */
(function(){
  const IND = window.BIRDSONG_MIGRAZIONI || {};
  const MESI = ['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre'];
  const DURATA = 18;          // secondi per l'intera stagione
  const SCIA = 12;            // giorni di scia dietro ogni punto
  const TORRE_FLAVIA = [41.96, 12.05];
  const cache = {};
  let dlg, tela, ctx, stato = null, dimensiona = () => {};
  addEventListener('resize', () => dimensiona());

  function disponibile(sci){ return !!IND[String(sci || '').toLowerCase()]; }

  function carica(url){
    if (!cache[url]) cache[url] = fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
    return cache[url];
  }

  function crea(){
    if (dlg) return;
    const st = document.createElement('style');
    st.textContent = `
      dialog.migra{width:min(1120px,calc(100% - 24px));max-width:none;max-height:calc(100% - 24px);padding:0;border:1px solid var(--linea,#3b444a);
        border-radius:16px;background:#14191c;color:var(--testo,#eef0ee);overflow:auto}
      dialog.migra::backdrop{background:rgba(0,0,0,.7)}
      .migra .corpo{display:flex;align-items:stretch}
      .migra .mappa{position:relative;background:#0a0d0f;flex:none}
      .migra canvas{display:block}
      .migra .lato{flex:1;min-width:0;padding:18px 20px;display:flex;flex-direction:column;gap:10px}
      .migra .testa{display:flex;align-items:flex-start;gap:12px}
      .migra h2{font-size:21px;margin:0;line-height:1.2}
      .migra h2 small{display:block;font-family:var(--serif,Georgia,serif);font-style:italic;font-weight:400;font-size:15px;color:var(--piuma,#8f989f);margin-top:3px}
      .migra .chiudi{margin-left:auto;flex:none;width:38px;height:38px;border-radius:50%;border:1px solid rgba(255,255,255,.2);background:transparent;
        color:var(--testo,#eef0ee);font-size:22px;line-height:1;cursor:pointer}
      .migra .chiudi:hover{border-color:var(--arancio,#f87e2e)}
      .migra .data{position:absolute;left:14px;top:12px;font-size:16px;font-weight:600;color:#fff;text-shadow:0 1px 6px #000;pointer-events:none}
      .migra .data span{display:block;font-size:12px;font-weight:400;color:var(--piuma,#8f989f)}
      .migra .barra{position:absolute;left:14px;right:14px;bottom:10px;height:3px;background:rgba(255,255,255,.12);border-radius:2px}
      .migra .barra i{display:block;height:100%;width:0;background:var(--arancio,#f87e2e);border-radius:2px}
      .migra .descr{margin:0;font-size:14px;line-height:1.55;color:#d9dddb}
      .migra .leg{list-style:none;margin:0;padding:0;display:grid;gap:5px;font-size:13.5px;color:#d9dddb}
      .migra .leg li{display:flex;align-items:center;gap:9px}
      .migra .leg i{flex:none;width:9px;height:9px;border-radius:50%}
      .migra .leg .viaggio{background:#ffd2a8}
      .migra .leg .arrivo{background:#ffa25e;opacity:.75}
      .migra .leg .tf{border:1.5px solid #fff;width:8px;height:8px}
      .migra .crediti{margin:auto 0 0;font-size:11.5px;line-height:1.5;color:var(--piuma,#8f989f)}
      .migra .crediti a{color:var(--piuma,#8f989f)}
      .migra .riga-btn{display:flex;gap:8px}
      @media (max-width:820px){
        dialog.migra{width:calc(100% - 16px);max-height:calc(100% - 16px)}
        .migra .corpo{flex-direction:column}
        .migra .lato{display:contents}
        .migra .testa{order:-1;padding:12px 14px 8px}
        .migra h2{font-size:17px}
        .migra .riga-btn{padding:10px 14px 0}
        .migra .descr{padding:8px 14px 0;font-size:13.5px}
        .migra .leg{padding:8px 14px 0;font-size:13px}
        .migra .crediti{padding:8px 14px 14px;margin:0}
      }`;
    document.head.appendChild(st);
    dlg = document.createElement('dialog');
    dlg.className = 'migra';
    dlg.setAttribute('aria-labelledby', 'migra-t');
    dlg.innerHTML = `
      <div class="corpo">
        <div class="mappa"><canvas width="760" height="760" aria-label="Mappa animata della migrazione"></canvas>
          <div class="data" aria-live="off"></div><div class="barra"><i></i></div></div>
        <div class="lato">
          <div class="testa"><h2 id="migra-t"></h2><button type="button" class="chiudi" aria-label="Chiudi">×</button></div>
          <div class="riga-btn"><button type="button" class="btn piccolo" data-az="rivedi">Rivedi</button>
            <button type="button" class="btn secondario piccolo" data-az="pausa">Pausa</button></div>
          <p class="descr"></p>
          <ul class="leg">
            <li><i class="viaggio"></i>Punto chiaro: in viaggio</li>
            <li><i class="arrivo"></i>Punto arancio: arrivata ai quartieri d'inverno</li>
            <li><i class="tf"></i>Cerchio bianco: Torre Flavia</li>
          </ul>
          <p class="crediti"></p>
        </div>
      </div>`;
    document.body.appendChild(dlg);
    tela = dlg.querySelector('canvas'); ctx = tela.getContext('2d');
    dlg.querySelector('.chiudi').addEventListener('click', () => dlg.close());
    dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });      // clic fuori dalla finestra
    dlg.addEventListener('close', () => { if (stato) cancelAnimationFrame(stato.raf); stato = null; });
    dlg.querySelector('[data-az="rivedi"]').addEventListener('click', () => { if (stato){ stato.t = 0; stato.pausa = false; aggiornaPausa(); } });
    dlg.querySelector('[data-az="pausa"]').addEventListener('click', () => { if (stato){ stato.pausa = !stato.pausa; aggiornaPausa(); } });
  }
  function aggiornaPausa(){ dlg.querySelector('[data-az="pausa"]').textContent = stato && stato.pausa ? 'Riprendi' : 'Pausa'; }

  async function apri(sci){
    const info = IND[String(sci || '').toLowerCase()];
    if (!info) return;
    crea();
    dlg.querySelector('#migra-t').innerHTML = `Migrazione d'${info.stagione === 'autunno' ? 'autunno' : info.stagione}: ${info.nome}<small>${info.sci}</small>`;
    dlg.querySelector('.descr').textContent = `${info.descrizione} ${info.individui} viaggi registrati fra il ${info.anni[0]} e il ${info.anni[1]}, mostrati tutti insieme sullo stesso calendario.`;
    dlg.querySelector('.crediti').innerHTML = `Dati: ${info.crediti} <a href="${info.doi}" target="_blank" rel="noopener">${info.doi.replace('https://', '')}</a>` +
      (info.licenza ? `, licenza <a href="${info.licenza_url}" target="_blank" rel="noopener">${info.licenza}</a>` : '') +
      (info.modifiche ? `. Elaborazione birdsongtech: ${info.modifiche}` : '') + '. Mappa: Natural Earth (pubblico dominio).';
    dlg.showModal();
    try {
      const [terre, dati] = await Promise.all([carica('data/migrazioni/terre.json'), carica(info.file)]);
      avvia(terre, dati);
    } catch (e) {
      dlg.querySelector('.descr').textContent = 'Non è stato possibile caricare i dati della migrazione.';
    }
  }

  function avvia(terre, dati){
    const [lo0, lo1, la0, la1] = terre.zona;
    const kx = Math.cos((la0 + la1) / 2 * Math.PI / 180);     // proiezione equirettangolare con correzione a meta' latitudine
    const W = 760, H = Math.round(W * (la1 - la0) / ((lo1 - lo0) * kx));
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    tela.width = W * dpr; tela.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    dimensiona = () => {                                       // la mappa riempie l'altezza (computer) o la larghezza (telefono)
      const largo = innerWidth > 820;
      let w, h;
      if (largo){ h = innerHeight - 26; w = h * W / H; const max = Math.min(1120, innerWidth - 24) - 300; if (w > max){ w = max; h = w * H / W; } }
      else { w = Math.min(innerWidth, 1120) - 18; h = w * H / W; }
      tela.style.width = Math.round(w) + 'px'; tela.style.height = Math.round(h) + 'px';
    };
    dimensiona();
    const X = lo => (lo - lo0) / (lo1 - lo0) * W, Y = la => (la1 - la) / (la1 - la0) * H;
    // fondo: terre disegnate una volta sola
    const fondo = document.createElement('canvas'); fondo.width = W * dpr; fondo.height = H * dpr;
    const f = fondo.getContext('2d'); f.setTransform(dpr, 0, 0, dpr, 0, 0);
    f.fillStyle = '#0a0d0f'; f.fillRect(0, 0, W, H);
    f.fillStyle = '#1f272b'; f.strokeStyle = '#33404a'; f.lineWidth = 0.8;
    for (const pol of terre.poligoni){
      f.beginPath(); pol.forEach(([x, y], i) => i ? f.lineTo(X(x), Y(y)) : f.moveTo(X(x), Y(y))); f.closePath(); f.fill(); f.stroke();
    }
    // Torre Flavia
    const tx = X(TORRE_FLAVIA[1]), ty = Y(TORRE_FLAVIA[0]);
    f.strokeStyle = '#ffffff'; f.lineWidth = 1.2; f.beginPath(); f.arc(tx, ty, 4, 0, 7); f.stroke();
    f.fillStyle = 'rgba(255,255,255,.85)'; f.font = '600 11px Montserrat, system-ui, sans-serif'; f.fillText('Torre Flavia', tx + 7, ty + 4);
    // equatore
    f.strokeStyle = 'rgba(255,255,255,.08)'; f.setLineDash([3, 5]); f.beginPath(); f.moveTo(0, Y(0)); f.lineTo(W, Y(0)); f.stroke(); f.setLineDash([]);
    f.fillStyle = 'rgba(255,255,255,.25)'; f.font = 'italic 10px system-ui, sans-serif'; f.fillText('equatore', W - 56, Y(0) - 4);

    const tracce = dati.tracce.map(t => t.p);
    const ultimo = Math.max(...tracce.map(p => p[p.length - 1][0]));
    const inizio = new Date(2001, 7, 1);                      // 1 agosto (anno qualsiasi non bisestile)
    const pos = (p, d) => {                                   // posizione al giorno d (interpolata)
      if (d <= p[0][0]) return p[0];
      for (let i = 1; i < p.length; i++){
        if (p[i][0] >= d){
          const a = p[i - 1], b = p[i], k = (d - a[0]) / (b[0] - a[0] || 1);
          return [d, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
        }
      }
      return p[p.length - 1];
    };
    const etichetta = dlg.querySelector('.data'), barra = dlg.querySelector('.barra i');
    const ridotto = matchMedia('(prefers-reduced-motion: reduce)').matches;
    stato = {t: ridotto ? DURATA : 0, pausa: false, ultimoT: performance.now(), raf: 0};
    aggiornaPausa();
    function disegna(ora){
      if (!stato) return;
      const dt = Math.min(0.1, (ora - stato.ultimoT) / 1000); stato.ultimoT = ora;
      if (!stato.pausa) stato.t = Math.min(DURATA + 2, stato.t + dt);
      const giorno = Math.min(ultimo, stato.t / DURATA * ultimo);
      ctx.drawImage(fondo, 0, 0, W, H);
      ctx.lineCap = 'round';
      for (const p of tracce){
        if (giorno < p[0][0]) continue;
        // scia: ultimi SCIA giorni, sempre piu' trasparente
        const da = Math.max(p[0][0], giorno - SCIA);
        let prec = pos(p, da);
        for (let d = da + 1; d <= giorno + 0.001; d += 1){
          const q = pos(p, Math.min(d, giorno));
          ctx.strokeStyle = `rgba(248,126,46,${0.08 + 0.5 * (d - da) / SCIA})`; ctx.lineWidth = 1.6;
          ctx.beginPath(); ctx.moveTo(X(prec[2]), Y(prec[1])); ctx.lineTo(X(q[2]), Y(q[1])); ctx.stroke();
          prec = q;
        }
        const q = pos(p, giorno), arrivato = giorno >= p[p.length - 1][0];
        ctx.fillStyle = arrivato ? 'rgba(255,162,94,.55)' : '#ffd2a8';
        ctx.beginPath(); ctx.arc(X(q[2]), Y(q[1]), arrivato ? 2 : 2.6, 0, 7); ctx.fill();
      }
      const data = new Date(inizio.getTime() + giorno * 86400000);
      etichetta.innerHTML = `${data.getDate()} ${MESI[data.getMonth()]}<span>in viaggio: ${tracce.filter(p => giorno >= p[0][0] && giorno < p[p.length - 1][0]).length} su ${tracce.length}</span>`;
      barra.style.width = (giorno / ultimo * 100) + '%';
      stato.raf = requestAnimationFrame(disegna);
    }
    stato.raf = requestAnimationFrame(disegna);
  }

  window.BSMigrazione = {disponibile, apri};
  // apertura diretta da un link, es. archivio.html?migrazione=ciconia%20ciconia (utile per le prove e per i link esterni)
  const daLink = new URLSearchParams(location.search).get('migrazione');
  if (daLink) addEventListener('load', () => apri(daLink));
})();
