// finish.js — universal end-of-session handoff
window.Finish = (function(){
  const KEY = 'lp.finish';

  function store(data){
    try { sessionStorage.setItem(KEY, JSON.stringify(data || {})); } catch(_){}
  }
  function load(){
    try { return JSON.parse(sessionStorage.getItem(KEY) || '{}'); } catch(_){ return {}; }
  }
  async function post(payload){
    try{
      const r = await api.fetch('/api/submit_score', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(payload || {})
      });
      if (!r.ok) throw new Error('submit_failed');
      const j = await r.json();
      // cache stats for summary
      try { sessionStorage.setItem(KEY+'.stats', JSON.stringify(j.stats||{})); } catch(_){}
      return j;
    }catch(e){
      return { ok:false, error:String(e) };
    }
  }
  async function postAndRedirect(payload, summaryHref='summary.html'){
    store(payload);
    try { await post(payload); } catch(_){ /* non-fatal; summary can still render */ }
    window.location.href = summaryHref;
  }
  return { store, load, post, postAndRedirect };
})();
