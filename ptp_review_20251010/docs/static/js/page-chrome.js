;(function () {
  'use strict';

  // ----- Banner (uses data-header or left part of <title> before "•") -----
  var bannerEl = document.getElementById('headerBanner');
  if (bannerEl && !(bannerEl.textContent || '').trim()) {
    var explicit  = document.body.getAttribute('data-header') || document.body.getAttribute('data-banner');
    var fromTitle = ((document.title.split('•')[0]) || '').trim();
    bannerEl.textContent = explicit || fromTitle || '';
  }

  // ----- Page note (data-note-lead / data-note-tail OR single data-note) -----
  var noteEl = document.getElementById('pageNote');
  if (noteEl) {
    var lead = (document.body.getAttribute('data-note-lead') || '').trim();
    var tail = (document.body.getAttribute('data-note-tail') || '').trim();

    if (!lead && !tail) {
      var raw = (document.body.getAttribute('data-note') || '').trim();
      if (raw) {
        var bold = raw.match(/^\s*\*\*(.+?)\*\*\s*(.*)$/); // **Lead** Tail
        if (bold) { lead = (bold[1] || '').trim(); tail = (bold[2] || '').trim(); }
        else { tail = raw; }
      }
    }

    if (!lead && !tail) {
      noteEl.style.display = 'none';
    } else {
      noteEl.textContent = '';
      if (lead) {
        var L = document.createElement('span');
        L.className = 'note-lead';
        L.textContent = lead;
        noteEl.appendChild(L);
      }
      var noSep = document.body.hasAttribute('data-note-no-sep');
      if (lead && tail && !noSep) {
        var S = document.createElement('span');
        S.className = 'note-sep';
        S.textContent = '—';
        noteEl.appendChild(S);
      }
      if (tail) {
        var T = document.createElement('span');
        T.className = 'note-tail';
        T.textContent = tail;
        noteEl.appendChild(T);
      }
    }
  }

  // ----- Auth buttons show/hide (works even if api.js is missing) -----
  var loginLink    = document.getElementById('loginLink');
  var registerLink = document.getElementById('registerLink');
  var logoutBtn    = document.getElementById('logoutBtn');

  (function initAuth(){
    if (!window.api || typeof window.api.fetch !== 'function') return; // quietly skip if api.js not present
    (async function(){
      var me = null;
      try {
        var r = await api.fetch('/api/me');
        if (r && r.ok) me = await r.json();
      } catch(e) {}
      if (me) {
        if (loginLink)    loginLink.style.display    = 'none';
        if (registerLink) registerLink.style.display = 'none';
        if (logoutBtn)    logoutBtn.style.display    = 'inline-flex';
      } else {
        if (loginLink)    loginLink.style.display    = 'inline-flex';
        if (registerLink) registerLink.style.display = 'inline-flex';
        if (logoutBtn)    logoutBtn.style.display    = 'none';
      }
      if (logoutBtn) {
        logoutBtn.addEventListener('click', async function(){
          try { await api.fetch('/api/logout', { method:'POST' }); } catch(_){}
          try { localStorage.removeItem('lp_token'); } catch(_){}
          location.href = '/login.html';
        });
      }
    })();
  })();

  // ----- Bottom nav: auto-highlight current page (robust URL resolve) -----
  (function highlightBottomNav(){
    var path = location.pathname.replace(/\/index\.html?$/,'/'); // treat / and /index.html as same
    var links = document.querySelectorAll('nav.bottom a');
    for (var i=0; i<links.length; i++){
      var a = links[i];
      var href = a.getAttribute('href');
      if (!href) continue;
      var tmp = document.createElement('a');
      tmp.href = href;                                    // browser resolves it for us
      var resolved = (tmp.pathname || '').replace(/\/index\.html?$/,'/');
      if (resolved === path) a.classList.add('active');
    }
  })();
})();
