/* birdsongtech — funzioni comuni. I dati arrivano da data/rilevamenti.js (window.BIRDSONG),
   generato da pubblica.py. */
(function(){
  const vuoto = {aggiornato:null, stazione:{lat:41.95970, lon:12.05215}, nodi:[], rilevamenti:[]};
  const D = window.BIRDSONG || vuoto;

  const MESI = ['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre'];

  function esc(s){
    return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function dataLunga(iso){            // 2026-10-30 -> 30 ottobre 2026
    if(!iso) return '';
    const [a,m,g] = iso.split('-').map(Number);
    return `${g} ${MESI[m-1]} ${a}`;
  }
  function dataBreve(iso){            // 2026-10-30 -> 30/10/2026
    if(!iso) return '';
    const [a,m,g] = iso.split('-');
    return `${g}/${m}/${a}`;
  }
  function ora(hms){ return (hms||'').slice(0,5); }
  function perc(score){ return Math.round((score||0)*100) + '%'; }
  function confHTML(score){
    const p = Math.round((score||0)*100);
    return `<span class="conf" title="Affidabilità del riconoscimento"><i><b style="width:${p}%"></b></i>${p}%</span>`;
  }
  function nomeNodo(n){               // TORRE_FLAVIA_01 -> Torre Flavia (la stazione e' unica: niente numero)
    return String(n||'').replace(/_\d+$/,'').replace(/_/g,' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  }
  function linkPlayer(r){ return `player.html?id=${encodeURIComponent(r.id)}`; }
  const ONDE = '<svg class="onde" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M6 4.5a5 5 0 0 0 0 7"/><path d="M3.2 2a9 9 0 0 0 0 12"/><path d="M8.8 6.6a2 2 0 0 0 0 2.8"/></svg>';
  function bottoneAscolta(r, piccolo=true){
    const cls = 'btn' + (piccolo ? ' piccolo' : '');
    if(!r.audio){
      return `<span class="${cls}" aria-disabled="true" title="Il file audio verrà pubblicato dopo il prossimo scarico dalla stazione">Audio in arrivo</span>`;
    }
    return `<a class="${cls}" href="${linkPlayer(r)}">${ONDE}Ascolta in 3D</a>`;
  }
  function specieConteggio(){
    const m = new Map();
    for(const r of D.rilevamenti){
      const k = r.specie;
      const e = m.get(k) || {specie:k, sci:r.sci, n:0, conAudio:0, ultimo:r.data};
      e.n++; if(r.audio) e.conAudio++;
      if(r.data > e.ultimo) e.ultimo = r.data;
      m.set(k, e);
    }
    return [...m.values()].sort((a,b) => b.n - a.n || a.specie.localeCompare(b.specie,'it'));
  }

  window.BS = {D, esc, dataLunga, dataBreve, ora, perc, confHTML, nomeNodo, linkPlayer, bottoneAscolta, specieConteggio, ONDE};

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-aggiornato]').forEach(el => {
      el.textContent = D.aggiornato
        ? `Dati aggiornati al ${dataBreve(D.aggiornato.slice(0,10))} alle ${D.aggiornato.slice(11,16)}`
        : 'Dati non ancora pubblicati';
    });
  });
})();
