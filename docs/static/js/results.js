// docs/static/js/results.js
(function(){
  function _repoBase(){
    if (/\.github\.io$/i.test(location.hostname)) {
      const p = location.pathname.split('/').filter(Boolean);
      return '/' + (p[0] || 'LearnPolish');
    }
    return '';
  }
  async function submit({ set, mode, score, attempts=1, details={} }){
    try{
      await api.fetch('/api/submit_score', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          set_name: set, mode, score, attempts, details
        })
      });
    }catch(_){}
    try{ sessionStorage.setItem('lp.lastResult', JSON.stringify({set, mode, score, details, ts: Date.now()})); }catch(_){}
  }
  function goSummary({ set, mode, score }){
    const q = new URLSearchParams({ set, mode, score: String(Math.round(score||0)) });
    location.href = _repoBase() + '/summary.html?' + q.toString();
  }
  window.Results = { submit, goSummary, repoBase: _repoBase };
})();
