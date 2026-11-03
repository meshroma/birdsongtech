/* birdsongtech — banner di consenso per Google Analytics.
   Google Analytics viene caricato SOLO dopo "Accetta". La scelta resta salvata nel browser
   per 6 mesi; poi il banner ricompare. Il link "Preferenze cookie" (data-preferenze-cookie)
   riapre il banner in qualsiasi momento. */
(function(){
  const GA_ID = 'G-NLEB8DFKFN';
  const CHIAVE = 'birdsongtech-consenso';
  const DURATA = 183 * 24 * 3600 * 1000;          // circa 6 mesi

  function leggi(){
    try{
      const v = JSON.parse(localStorage.getItem(CHIAVE) || 'null');
      return v && (Date.now() - v.data) < DURATA ? v.scelta : null;
    }catch(e){ return null; }
  }
  function salva(scelta){
    try{ localStorage.setItem(CHIAVE, JSON.stringify({scelta, data: Date.now()})); }catch(e){}
  }

  let caricato = false;
  function attivaAnalytics(){
    if (caricato) return; caricato = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function(){ dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', GA_ID);
    const s = document.createElement('script');
    s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);
  }

  const stile = `
  #consenso{position:fixed;left:16px;right:16px;bottom:16px;z-index:1000;max-width:560px;margin:0 auto;
    background:#252b2f;color:#eef0ee;border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:16px 18px;
    box-shadow:0 10px 30px rgba(0,0,0,.45);font:400 14px/1.5 'Montserrat',system-ui,sans-serif}
  #consenso p{margin:0 0 12px}
  #consenso .scelte{display:flex;gap:10px;flex-wrap:wrap}
  #consenso button{font:600 14px/1 'Montserrat',system-ui,sans-serif;padding:10px 18px;border-radius:999px;cursor:pointer;
    border:1px solid rgba(255,255,255,.35);background:transparent;color:#eef0ee;min-width:110px}
  #consenso button:hover{border-color:#f87e2e}
  #consenso button:focus-visible{outline:2px solid #f87e2e;outline-offset:3px}
  #consenso .chiudi{position:absolute;top:8px;right:10px;min-width:0;border:none;padding:6px 8px;font-size:18px;color:#8f989f}`;

  function mostraBanner(){
    if (document.getElementById('consenso')) return;
    if (!document.getElementById('consenso-stile')){
      const st = document.createElement('style'); st.id = 'consenso-stile'; st.textContent = stile; document.head.appendChild(st);
    }
    const b = document.createElement('div');
    b.id = 'consenso'; b.setAttribute('role', 'dialog'); b.setAttribute('aria-label', 'Consenso ai cookie');
    b.innerHTML = `<button class="chiudi" type="button" aria-label="Chiudi e rifiuta">×</button>
      <p>Con il tuo consenso usiamo Google Analytics per contare le visite al sito in forma aggregata.
      Senza consenso il sito funziona allo stesso modo e non viene usato alcun cookie di statistica.</p>
      <div class="scelte"><button type="button" data-scelta="no">Rifiuta</button><button type="button" data-scelta="si">Accetta</button></div>`;
    b.addEventListener('click', e => {
      const t = e.target.closest('button'); if (!t) return;
      const scelta = t.dataset.scelta === 'si' ? 'si' : 'no';   // anche la chiusura vale come rifiuto
      salva(scelta);
      b.remove();
      if (scelta === 'si') attivaAnalytics();
      else if (caricato) location.reload();                     // consenso revocato: ricarica senza Analytics
    });
    document.body.appendChild(b);
  }

  function avvia(){
    const scelta = leggi();
    if (scelta === 'si') attivaAnalytics();
    else if (scelta === null) mostraBanner();
    document.querySelectorAll('[data-preferenze-cookie]').forEach(a =>
      a.addEventListener('click', e => { e.preventDefault(); mostraBanner(); }));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', avvia); else avvia();
})();
