// docs/static/js/results.js
(function(){
  function _repoBase(){
    if (/\.github\.io$/i.test(location.hostname)) {
      const p = location.pathname.split('/').filter(Boolean);
      return '/' + (p[0] || 'LearnPolish');
    }
    return '';
  }

  async function submit({ set, mode, score, attempts = 1, details = {} }){
    // Only cache locally; summary.html will POST /api/submit_score once.
    try {
      sessionStorage.setItem(
        'lp.lastResult',
        JSON.stringify({ set, mode, score, attempts, details, ts: Date.now() })
      );
    } catch(_){}
  }

  function goSummary({ set, mode, score }){
    const q = new URLSearchParams({ set, mode, score: String(Math.round(score||0)) });
    location.href = _repoBase() + '/summary.html?' + q.toString();
  }

  window.Results = { submit, goSummary, repoBase: _repoBase };
})();
