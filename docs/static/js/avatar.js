/**
 * Avatar system for Path to POLISH
 *
 * Pierogi characters + moods backed by SVG assets in docs/static/avatar.
 *
 * Exposes:
 *   window.AvatarChooser.initProfileAvatar({ initialId, onChange })
 *   window.AvatarChooser.renderAvatar(containerEl, charOrId, moodId)
 *   window.AvatarChooser.pathFor(avatarId)   // helper -> neutral face SVG URL
 *
 * Char IDs:
 *   "hero" | "chonky" | "tall" | "junior"
 *
 * Mood IDs:
 *   "neutral" | "win" | "milestone" | "tired" | "embarrassed" | "inactive"
 */
(function (global) {
  'use strict';

  var SVG_NS   = 'http://www.w3.org/2000/svg';
  var XLINK_NS = 'http://www.w3.org/1999/xlink';

  var AVATAR_BASE    = 'static/avatar/';
  var PIEROGI_SPRITE = AVATAR_BASE + 'pierogi.svg';

  var CHAR_IDS = ['hero', 'chonky', 'tall', 'junior'];
  var MOODS    = ['neutral', 'win', 'milestone', 'tired', 'embarrassed', 'inactive'];

  var CHAR_DEFS = {
    hero:   { label: 'Pierogi Hero'   },
    chonky:{ label: 'Pierogi Chonky' },
    tall:  { label: 'Pierogi Tall'   },
    junior:{ label: 'Pierogi Junior' }
  };

  // Map character + mood -> list of expression SVG filenames (no path).
  // Filenames live in docs/static/avatar/.
  var EXP_MAP = {
    hero: {
      neutral:     ['hero-neutral-1.svg', 'hero-neutral-2.svg'],
      win:         ['hero-neutral-win.svg'],
      milestone:   ['hero-neutral-win.svg'],
      tired:       ['hero-neutral-1.svg'],
      embarrassed: ['hero-neutral-1.svg'],
      inactive:    ['hero-neutral-2.svg']
    },
    chonky: {
      neutral:     ['chonky-neutral-1.svg', 'chonky-neutral-2.svg'],
      win:         ['chonky-win-1.svg'],
      milestone:   ['chonky-milestone-1.svg'],
      tired:       ['chonky-tired-1.svg'],
      embarrassed: ['chonky-embarrassed-1.svg'],
      inactive:    ['chonky-inactive-1.svg']
    },
    tall: {
      neutral:     ['tall-neutral-1.svg', 'tall-neutral-2.svg'],
      win:         ['tall-win-1.svg'],
      // NOTE: asset is spelled "milstone" (no second 'e')
      milestone:   ['tall-milstone-1.svg'],
      tired:       ['tall-tired-1.svg'],
      embarrassed: ['tall-embarrassed-1.svg'],
      inactive:    ['tall-inactive-1.svg']
    },
    junior: {
      neutral:     ['junior-neutral-1.svg', 'junior-neutral-2.svg'],
      win:         ['junior-milestone-1.svg'],
      milestone:   ['junior-milestone-1.svg'],
      tired:       ['junior-tired-1.svg'],
      // NOTE: asset is spelled "emarrassed" in the files
      embarrassed: ['junior-emarrassed-1.svg'],
      inactive:    ['junior-inactive-1.svg']
    }
  };

  function randChoice(list) {
    if (!list || !list.length) return null;
    if (list.length === 1) return list[0];
    var idx = Math.floor(Math.random() * list.length);
    return list[idx];
  }

  function normalizeCharId(id) {
    if (!id) return 'hero';
    var s = String(id).toLowerCase();

    if (CHAR_IDS.indexOf(s) !== -1) return s;

    // Support stored IDs like "pierogi-hero" or "pierogi:hero"
    if (s.indexOf('pierogi-') === 0) {
      var c1 = s.slice('pierogi-'.length);
      if (CHAR_IDS.indexOf(c1) !== -1) return c1;
    }
    if (s.indexOf('pierogi:') === 0) {
      var c2 = s.slice('pierogi:'.length);
      if (CHAR_IDS.indexOf(c2) !== -1) return c2;
    }

    return 'hero';
  }

  function normalizeMoodId(mood) {
    if (!mood) return 'neutral';
    var s = String(mood).toLowerCase();
    if (MOODS.indexOf(s) !== -1) return s;
    return 'neutral';
  }

  function pickExpressionFilename(charId, moodId) {
    var c = normalizeCharId(charId);
    var m = normalizeMoodId(moodId);
    var byChar = EXP_MAP[c] || EXP_MAP.hero;
    var list = byChar[m] || byChar.neutral || EXP_MAP.hero.neutral;
    return randChoice(list);
  }

  function expressionUrl(charId, moodId) {
    var file = pickExpressionFilename(charId, moodId);
    return file ? (AVATAR_BASE + file) : '';
  }

  // -------- Pierogi body sprite (pierogi.svg) loader --------
  var PierogiSprite = {
    loaded: false,
    loadPromise: null,
    stylesText: '',
    symbols: {} // id -> <symbol> element
  };

  function ensurePierogiSpriteLoaded() {
    if (PierogiSprite.loaded && PierogiSprite.loadPromise) {
      return PierogiSprite.loadPromise;
    }
    if (PierogiSprite.loadPromise) return PierogiSprite.loadPromise;

    PierogiSprite.loadPromise = fetch(PIEROGI_SPRITE)
      .then(function (r) { return r.text(); })
      .then(function (txt) {
        var parser = new DOMParser();
        var doc = parser.parseFromString(txt, 'image/svg+xml');

        var styleNode = doc.querySelector('style');
        PierogiSprite.stylesText = (styleNode && styleNode.textContent) ? styleNode.textContent : '';

        var symbols = doc.querySelectorAll('symbol[id^="pierogi-"]');
        Array.prototype.forEach.call(symbols, function (sym) {
          PierogiSprite.symbols[sym.id] = sym;
        });

        PierogiSprite.loaded = true;
      })
      .catch(function (err) {
        console.warn('AvatarChooser: failed to load pierogi.svg', err);
      });

    return PierogiSprite.loadPromise;
  }

  // -------- Core: renderAvatar(containerEl, charOrId, moodId) --------
  function renderAvatar(container, charOrId, moodId) {
    if (!container) return;

    var charId = normalizeCharId(charOrId);
    var mood   = normalizeMoodId(moodId);

    // Clear container
    while (container.firstChild) container.removeChild(container.firstChild);

    // Fixed logical canvas 200×200
    var svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('viewBox', '0 0 200 200');
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    svg.style.display = 'block';
    container.appendChild(svg);

    // Background card
    var bg = document.createElementNS(SVG_NS, 'rect');
    bg.setAttribute('x', '0');
    bg.setAttribute('y', '0');
    bg.setAttribute('width', '200');
    bg.setAttribute('height', '200');
    bg.setAttribute('rx', '40');

    var bgFill;
    switch (charId) {
      case 'chonky': bgFill = '#0f172a'; break;
      case 'tall':   bgFill = '#111827'; break;
      case 'junior': bgFill = '#1e293b'; break;
      default:       bgFill = '#020617'; break; // hero
    }
    bg.setAttribute('fill', bgFill);
    svg.appendChild(bg);

    // Face overlay first, so something shows even if sprite fails
    var img = null;
    var faceHref = expressionUrl(charId, mood);
    if (faceHref) {
      img = document.createElementNS(SVG_NS, 'image');

      // ---- FACE SIZE + POSITION CONTROL ----
      var FACE_SCALE   = 0.4;   // 0.8 = 80% of card size
      var FACE_SIZE    = 200 * FACE_SCALE;

      // Base centered position
      var FACE_X = 100 - FACE_SIZE / 2;
      var FACE_Y = 100 - FACE_SIZE / 2;

      // Positive = move face *down*, negative = move up
      var FACE_Y_SHIFT = 10;    // try 10–30 and tune by eye
      FACE_Y += FACE_Y_SHIFT;

      img.setAttribute('x', String(FACE_X));
      img.setAttribute('y', String(FACE_Y));
      img.setAttribute('width',  String(FACE_SIZE));
      img.setAttribute('height', String(FACE_SIZE));

      img.setAttributeNS(XLINK_NS, 'href', faceHref);
      img.setAttribute('href', faceHref);
      svg.appendChild(img);
    }

    // Load body sprite + draw pierogi body behind the face
    ensurePierogiSpriteLoaded().then(function () {
      if (!PierogiSprite.loaded) return;
      if (!container.contains(svg)) return; // container reused/cleared

      // defs + styles for pg-shell/pg-ridge/pg-shadow/pg-limb
      if (PierogiSprite.stylesText && !svg.querySelector('defs')) {
        var defs = document.createElementNS(SVG_NS, 'defs');
        var st = document.createElementNS(SVG_NS, 'style');
        st.textContent = PierogiSprite.stylesText;
        defs.appendChild(st);
        svg.insertBefore(defs, bg.nextSibling || svg.firstChild);
      }

      var symbolId = 'pierogi-' + normalizeCharId(charId);
      var sym = PierogiSprite.symbols[symbolId];
      if (!sym) return;

      var g = document.createElementNS(SVG_NS, 'g');

      // ***** THIS IS THE MAIN SIZE KNOB *****
      // Previously we used SCALE = 2.0. Now ~1.5× bigger → 2.6.
      var BODY_SCALE = 1;
      var cx = 100, cy = 100;
      var tx = cx * (1 - BODY_SCALE);
      var ty = cy * (1 - BODY_SCALE);
      g.setAttribute(
        'transform',
        'translate(' + tx + ',' + ty + ') scale(' + BODY_SCALE + ')'
      );

      Array.prototype.forEach.call(sym.childNodes, function (node) {
        g.appendChild(node.cloneNode(true));
      });

      if (img && img.parentNode === svg) {
        // Put body behind the face
        svg.insertBefore(g, img);
      } else {
        svg.appendChild(g);
      }
    });
  }

  // -------- Profile page modal wiring --------
  function initProfileAvatar(opts) {
    opts = opts || {};
    var initial = normalizeCharId(opts.initialId || 'hero');

    var big    = document.getElementById('avatarBig');
    var open   = document.getElementById('chooseAvatarBtn');
    var modal  = document.getElementById('avatarModal');
    var grid   = document.getElementById('avatarGrid');
    var closeB = document.getElementById('avatarModalClose');
    var doneB  = document.getElementById('avatarModalDone');

    if (!big || !open || !modal || !grid) return;

    var currentChar = initial;

    function refreshBig() {
      renderAvatar(big, currentChar, 'neutral');
    }

    function syncGridSelection() {
      var cells = grid.querySelectorAll('.ava');
      Array.prototype.forEach.call(cells, function (btn) {
        var c = btn.getAttribute('data-char');
        btn.classList.toggle('active', normalizeCharId(c) === currentChar);
      });
    }

    function buildGridOnce() {
      if (grid.dataset.built === '1') return;

      CHAR_IDS.forEach(function (id) {
        var def = CHAR_DEFS[id];
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'ava';
        btn.setAttribute('data-char', id);
        btn.setAttribute('aria-label', def.label);

        var shell = document.createElement('div');
        shell.style.width = '40px';
        shell.style.height = '40px';
        shell.style.borderRadius = '12px';
        shell.style.overflow = 'hidden';
        shell.style.display = 'flex';
        shell.style.alignItems = 'center';
        shell.style.justifyContent = 'center';

        btn.appendChild(shell);
        renderAvatar(shell, id, 'neutral');

        btn.addEventListener('click', function () {
          currentChar = id;
          syncGridSelection();
          refreshBig();
        });

        grid.appendChild(btn);
      });

      grid.dataset.built = '1';
      syncGridSelection();
    }

    function openModal() {
      buildGridOnce();
      modal.classList.add('show');
      document.body.classList.add('modal-open');
    }

    function closeModal() {
      modal.classList.remove('show');
      document.body.classList.remove('modal-open');
    }

    open.addEventListener('click', openModal);

    if (closeB) {
      closeB.addEventListener('click', closeModal);
    }
    if (doneB) {
      doneB.addEventListener('click', function () {
        closeModal();
        if (typeof opts.onChange === 'function') {
          // Store as "pierogi-hero" etc. for compatibility
          opts.onChange('pierogi-' + currentChar);
        }
      });
    }

    modal.addEventListener('click', function (ev) {
      if (ev.target === modal) {
        closeModal();
      }
    });

    refreshBig();
  }

  // -------- Simple path helper for legacy callers --------
  function pathFor(avatarId) {
    var charId = normalizeCharId(avatarId);
    var url = expressionUrl(charId, 'neutral');
    return url || '';
  }

  // Public list (mainly for non-profile UI that wants a catalogue)
  var AVATAR_LIST = CHAR_IDS.map(function (id) {
    var storedId = 'pierogi-' + id;
    return {
      id: storedId,
      char: id,
      mood: 'neutral',
      label: CHAR_DEFS[id].label,
      src: pathFor(storedId)
    };
  });

  var AvatarChooser = {
    list: AVATAR_LIST,
    renderAvatar: renderAvatar,
    initProfileAvatar: initProfileAvatar,
    pathFor: pathFor
  };

  global.AvatarChooser = AvatarChooser;
  global.AvatarLib = { list: AVATAR_LIST };
})(window);
