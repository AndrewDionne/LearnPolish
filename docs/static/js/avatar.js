// docs/static/js/avatar.js
// Pierogi avatar system: 4 base characters + mood-based facial expressions.
//
// - Profile only stores `avatar_id`: "hero" | "chonky" | "tall" | "junior".
// - Faces are separate SVGs layered on top of bodies via <image>.
// - Use AvatarChooser.renderAvatar(el, avatarId, mood) in game UIs.
// - Profile uses AvatarChooser.initProfileAvatar(...).

(function (global) {
  const NS = "http://www.w3.org/2000/svg";
  const XLINK_NS = "http://www.w3.org/1999/xlink";

  // Where the body sprite is
  const SPRITE_URL = "static/avatar/pierogi.svg";

  // Base characters
  const CHARACTERS = {
    hero: {
      id: "hero",
      label: "Pierogi Hero",
      bodyId: "pierogi-hero-body",
      folder: "hero"
    },
    chonky: {
      id: "chonky",
      label: "Pierogi Chonky",
      bodyId: "pierogi-chonky-body",
      folder: "chonky"
    },
    tall: {
      id: "tall",
      label: "Pierogi Tall",
      bodyId: "pierogi-tall-body",
      folder: "tall"
    },
    junior: {
      id: "junior",
      label: "Pierogi Junior",
      bodyId: "pierogi-junior-body",
      folder: "junior"
    }
  };

  // Mood → list of SVG URLs per character.
  // Adjust these to match the actual filenames you have.
  const FACE_SETS = {
    hero: {
      neutral: [
        "static/avatar/hero/hero-neutral-1.svg",
        "static/avatar/hero/hero-neutral-2.svg"
      ],
      win: [
        "static/avatar/hero/hero-win-1.svg"
      ],
      milestone: [
        "static/avatar/hero/hero-milestone-1.svg"
      ],
      tired: [
        "static/avatar/hero/hero-tired-1.svg"
      ],
      embarrassed: [
        "static/avatar/hero/hero-embarrassed-1.svg"
      ],
      inactive: [
        "static/avatar/hero/hero-inactive-1.svg"
      ]
    },
    chonky: {
      neutral: [
        "static/avatar/chonky/chonky-neutral-1.svg",
        "static/avatar/chonky/chonky-neutral-2.svg"
      ],
      win: [
        "static/avatar/chonky/chonky-win-1.svg"
      ],
      milestone: [
        "static/avatar/chonky/chonky-milestone-1.svg"
      ],
      tired: [
        "static/avatar/chonky/chonky-tired-1.svg"
      ],
      embarrassed: [
        "static/avatar/chonky/chonky-embarrassed-1.svg"
      ],
      inactive: [
        "static/avatar/chonky/chonky-inactive-1.svg"
      ]
    },
    tall: {
      neutral: [
        "static/avatar/tall/tall-neutral-1.svg",
        "static/avatar/tall/tall-neutral-2.svg"
      ],
      win: [
        "static/avatar/tall/tall-win-1.svg"
      ],
      milestone: [
        "static/avatar/tall/tall-milestone-1.svg"
      ],
      tired: [
        "static/avatar/tall/tall-tired-1.svg"
      ],
      embarrassed: [
        "static/avatar/tall/tall-embarrassed-1.svg"
      ],
      inactive: [
        "static/avatar/tall/tall-inactive-1.svg"
      ]
    },
    junior: {
      neutral: [
        "static/avatar/junior/junior-neutral-1.svg",
        "static/avatar/junior/junior-neutral-2.svg"
      ],
      win: [
        "static/avatar/junior/junior-win-1.svg"
      ],
      milestone: [
        "static/avatar/junior/junior-milestone-1.svg"
      ],
      tired: [
        "static/avatar/junior/junior-tired-1.svg"
      ],
      embarrassed: [
        "static/avatar/junior/junior-embarrassed-1.svg"
      ],
      inactive: [
        "static/avatar/junior/junior-inactive-1.svg"
      ]
    }
  };

  function pickFace(avatarId, mood) {
    const c = FACE_SETS[avatarId];
    if (!c) return null;

    const m = (mood || "neutral").toLowerCase();
    const pool = (c[m] && c[m].length ? c[m] : c.neutral) || [];
    if (!pool.length) return null;

    const idx = Math.floor(Math.random() * pool.length);
    return pool[idx];
  }

  function renderAvatar(targetEl, avatarId, mood) {
    if (!targetEl) return;
    while (targetEl.firstChild) targetEl.removeChild(targetEl.firstChild);

    const config = CHARACTERS[avatarId] || CHARACTERS.hero;
    const faceUrl = pickFace(config.id, mood || "neutral");

    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 512 512");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    svg.setAttribute("aria-hidden", "true");
    svg.style.display = "block";

    // Body
    const use = document.createElementNS(NS, "use");
    const hrefVal = SPRITE_URL + "#" + config.bodyId;
    use.setAttributeNS(XLINK_NS, "xlink:href", hrefVal);
    use.setAttribute("href", hrefVal);
    svg.appendChild(use);

    // Face overlay (if configured)
    if (faceUrl) {
      const img = document.createElementNS(NS, "image");
      img.setAttributeNS(XLINK_NS, "xlink:href", faceUrl);
      img.setAttribute("href", faceUrl);
      img.setAttribute("x", "0");
      img.setAttribute("y", "0");
      img.setAttribute("width", "512");
      img.setAttribute("height", "512");
      svg.appendChild(img);
    }

    targetEl.appendChild(svg);
  }

  // ---------------- Profile page wiring ----------------

  function initProfileAvatar(options) {
    const opts = options || {};
    const initialId = opts.initialId || "hero";
    const onChange = typeof opts.onChange === "function" ? opts.onChange : null;

    const avatarBig = document.getElementById("avatarBig");
    const openBtn = document.getElementById("chooseAvatarBtn");
    const modal = document.getElementById("avatarModal");
    const grid = document.getElementById("avatarGrid");
    const closeBtn = document.getElementById("avatarModalClose");
    const doneBtn = document.getElementById("avatarModalDone");

    if (!avatarBig || !openBtn || !modal || !grid) {
      // If markup is missing, nothing to do
      return;
    }

    let currentId = CHARACTERS[initialId] ? initialId : "hero";

    function updateBig() {
      renderAvatar(avatarBig, currentId, "neutral");
    }

    function openModal() {
      modal.classList.add("show");
      document.body.classList.add("modal-open");
    }

    function closeModal() {
      modal.classList.remove("show");
      document.body.classList.remove("modal-open");
    }

    // Build selection grid
    grid.innerHTML = "";
    Object.values(CHARACTERS).forEach((cfg) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "ava";
      btn.setAttribute("data-id", cfg.id);
      btn.setAttribute("role", "option");
      btn.setAttribute("aria-label", cfg.label);

      const inner = document.createElement("div");
      inner.style.width = "48px";
      inner.style.height = "48px";
      inner.style.marginBottom = "4px";

      const label = document.createElement("div");
      label.className = "tiny";
      label.textContent = cfg.label;

      btn.appendChild(inner);
      btn.appendChild(label);
      grid.appendChild(btn);

      renderAvatar(inner, cfg.id, "neutral");

      if (cfg.id === currentId) {
        btn.classList.add("active");
      }

      btn.addEventListener("click", () => {
        currentId = cfg.id;

        grid.querySelectorAll(".ava").forEach((el) => {
          el.classList.toggle("active", el === btn);
        });

        updateBig();
        if (onChange) onChange(currentId);
      });
    });

    updateBig();

    openBtn.addEventListener("click", openModal);
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (doneBtn) doneBtn.addEventListener("click", closeModal);

    // Click outside dialog to close
    modal.addEventListener("click", (ev) => {
      if (ev.target === modal) closeModal();
    });
  }

  global.AvatarChooser = {
    CHARACTERS,
    FACE_SETS,
    pickFace,
    renderAvatar,
    initProfileAvatar
  };
})(window);
