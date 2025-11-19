// static/js/avatar.js
// Pierogi avatar library + chooser + builder helpers.
// Assumes SVG files live under: docs/static/avatar/
//   hero-neutral-1.svg, hero-win-1.svg, hero-milestone-1.svg, hero-tired-1.svg, hero-embarrassed-1.svg, hero-inactive-1.svg
//   chonky-*.svg, tall-*.svg, junior-*.svg in the same pattern.

(function (global) {
  const DOC_BASE = ''; // paths are relative to docs/ root; <base> in HTML handles GitHub vs Flask.

  const CHAR_DEFS = {
    hero: {
      id: 'pierogi-hero',
      label: 'Pierogi Hero',
      moods: {
        neutral: 'hero-neutral-1.svg',
        win: 'hero-win-1.svg',
        milestone: 'hero-milestone-1.svg',
        tired: 'hero-tired-1.svg',
        embarrassed: 'hero-embarrassed-1.svg',
        inactive: 'hero-inactive-1.svg'
      }
    },
    chonky: {
      id: 'pierogi-chonky',
      label: 'Pierogi Chonky',
      moods: {
        neutral: 'chonky-neutral-1.svg',
        win: 'chonky-win-1.svg',
        milestone: 'chonky-milestone-1.svg',
        tired: 'chonky-tired-1.svg',
        embarrassed: 'chonky-embarrassed-1.svg',
        inactive: 'chonky-inactive-1.svg'
      }
    },
    tall: {
      id: 'pierogi-tall',
      label: 'Pierogi Tall',
      moods: {
        neutral: 'tall-neutral-1.svg',
        win: 'tall-win-1.svg',
        milestone: 'tall-milestone-1.svg',
        tired: 'tall-tired-1.svg',
        embarrassed: 'tall-embarrassed-1.svg',
        inactive: 'tall-inactive-1.svg'
      }
    },
    junior: {
      id: 'pierogi-junior',
      label: 'Pierogi Junior',
      moods: {
        neutral: 'junior-neutral-1.svg',
        win: 'junior-win-1.svg',
        milestone: 'junior-milestone-1.svg',
        tired: 'junior-tired-1.svg',
        embarrassed: 'junior-embarrassed-1.svg',
        inactive: 'junior-inactive-1.svg'
      }
    }
  };

  const DEFAULT_CHAR = 'hero';
  const DEFAULT_MOOD = 'neutral';

  function pathFor(charId, mood) {
    const cid = (charId || DEFAULT_CHAR);
    const m = (mood || DEFAULT_MOOD);
    const def = CHAR_DEFS[cid] || CHAR_DEFS[DEFAULT_CHAR];
    const file = (def.moods[m] || def.moods[DEFAULT_MOOD]);
    return DOC_BASE + 'static/avatar/' + file;
  }

  // Flat list for profile avatar grid (always neutral pose).
  const AVATAR_LIST = Object.keys(CHAR_DEFS).map(charId => {
    const def = CHAR_DEFS[charId];
    return {
      id: def.id,                // stored in profile.avatar_id
      char: charId,              // 'hero' | 'chonky' | 'tall' | 'junior'
      mood: 'neutral',
      label: def.label,
      src: pathFor(charId, 'neutral')
    };
  });

  function findByAvatarId(id) {
    if (!id) return null;

    // Exact match (pierogi-hero, etc.)
    const direct = AVATAR_LIST.find(a => a.id === id);
    if (direct) return direct;

    // Legacy ids (hero, chonky, tall, junior) → map to new ids
    if (CHAR_DEFS[id]) {
      const def = CHAR_DEFS[id];
      return {
        id: def.id,
        char: id,
        mood: 'neutral',
        label: def.label,
        src: pathFor(id, 'neutral')
      };
    }

    return null;
  }

  function renderAvatar(target, charId, mood) {
    const el = (typeof target === 'string')
      ? document.getElementById(target)
      : target;
    if (!el) return;

    const cid = (charId && CHAR_DEFS[charId]) ? charId : DEFAULT_CHAR;
    const m = mood || DEFAULT_MOOD;
    const def = CHAR_DEFS[cid] || CHAR_DEFS[DEFAULT_CHAR];
    const src = pathFor(cid, m);

    // Clear & inject <img>. The container (avatar-big, previewBox, etc.)
    // provides rounded corners / background.
    while (el.firstChild) el.removeChild(el.firstChild);

    const img = document.createElement('img');
    img.src = src;
    img.alt = def.label + ' (' + m + ')';
    img.style.display = 'block';
    img.style.maxWidth = '100%';
    img.style.maxHeight = '100%';
    img.style.margin = '0 auto';

    el.appendChild(img);
  }

  // ----- Profile page integration -----
  function initProfileAvatar(opts) {
    const doc = document;
    const big = doc.getElementById('avatarBig');
    const openBtn = doc.getElementById('chooseAvatarBtn');
    const modal = doc.getElementById('avatarModal');
    const grid = doc.getElementById('avatarGrid');
    const closeBtn = doc.getElementById('avatarModalClose');
    const doneBtn = doc.getElementById('avatarModalDone');

    if (!big || !openBtn || !modal || !grid) return;

    let current = null;

    // Initial selection from stored avatar_id (server/local) if present
    if (opts && opts.initialId) {
      current = findByAvatarId(opts.initialId);
    }
    if (!current) {
      current = AVATAR_LIST[0];
    }

    // Render big avatar
    renderAvatar(big, current.char, current.mood);

    function syncGrid() {
      const nodes = grid.querySelectorAll('[data-avatar-id]');
      nodes.forEach(node => {
        const id = node.getAttribute('data-avatar-id');
        node.classList.toggle('active', id === current.id);
      });
    }

    function buildGridOnce() {
      if (grid.dataset.wired === '1') return;
      grid.dataset.wired = '1';
      grid.innerHTML = '';

      AVATAR_LIST.forEach(a => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'ava';
        btn.setAttribute('data-avatar-id', a.id);
        btn.setAttribute('aria-label', a.label);

        const thumb = document.createElement('img');
        thumb.src = a.src;
        thumb.alt = a.label;
        thumb.style.maxWidth = '100%';
        thumb.style.maxHeight = '100%';
        thumb.style.display = 'block';

        btn.appendChild(thumb);

        btn.addEventListener('click', () => {
          current = a;
          renderAvatar(big, current.char, current.mood);
          syncGrid();
        });

        grid.appendChild(btn);
      });

      syncGrid();
    }

    function openModal() {
      buildGridOnce();
      modal.classList.add('show');
      document.body.classList.add('modal-open');
      syncGrid();
    }
    function closeModal() {
      modal.classList.remove('show');
      document.body.classList.remove('modal-open');
    }

    openBtn.addEventListener('click', openModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (doneBtn) doneBtn.addEventListener('click', () => {
      closeModal();
      if (opts && typeof opts.onChange === 'function') {
        opts.onChange(current.id);
      }
    });

    // Optional helper if you ever need current selection in other scripts
    AvatarChooser.current = function () {
      return Object.assign({}, current);
    };
  }

  const AvatarChooser = {
    list: AVATAR_LIST,
    renderAvatar,
    initProfileAvatar,
    pathFor
  };

  global.AvatarChooser = AvatarChooser;
  // Simple library handle for any other pages that just want the list.
  global.AvatarLib = { list: AVATAR_LIST };
})(window);
