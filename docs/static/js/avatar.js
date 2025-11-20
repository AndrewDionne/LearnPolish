// docs/static/js/avatar.js
//
// AvatarChooser:
//   - renderAvatar(containerEl, charId, mood)
//   - initProfileAvatar({ initialId, onChange })
//
// charId: "hero" | "chonky" | "tall" | "junior"
// mood:   "neutral" | "win" | "milestone" | "tired" | "embarrassed" | "inactive"
//
// All assets live in docs/static/avatar/:
//   - pierogi.svg          (bodies; symbols: pierogi-hero, pierogi-chonky, pierogi-tall, pierogi-junior)
//   - hero-*.svg, chonky-*.svg, tall-*.svg, junior-*.svg (faces)

(function (global) {
  const ROOT = "static/avatar/";
  const VIEWBOX = "0 0 200 200";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const XLINK_NS = "http://www.w3.org/1999/xlink";

  // ---- Character + mood definitions ----------------------------------------

  const CHAR_DEFS = {
    hero: {
      id: "hero",
      label: "Pierogi Hero",
      bodySymbolId: "pierogi-hero",
      faces: {
        neutral: ["hero-neutral-1.svg", "hero-neutral-2.svg"],
        win: ["hero-neutral-win.svg"],
        milestone: ["hero-neutral-win.svg"],
        tired: ["hero-tired-1.svg"],
        embarrassed: ["hero-embarrassed-1.svg"],
        inactive: ["hero-inactive-1.svg"]
      }
    },
    chonky: {
      id: "chonky",
      label: "Pierogi Chonky",
      bodySymbolId: "pierogi-chonky",
      faces: {
        neutral: ["chonky-neutral-1.svg", "chonky-neutral-2.svg"],
        win: ["chonky-win-1.svg"],
        milestone: ["chonky-milestone-1.svg"],
        tired: ["chonky-tired-1.svg"],
        embarrassed: ["chonky-embarrassed-1.svg"],
        inactive: ["chonky-inactive-1.svg"]
      }
    },
    tall: {
      id: "tall",
      label: "Pierogi Tall",
      bodySymbolId: "pierogi-tall",
      faces: {
        neutral: ["tall-neutral-1.svg", "tall-neutral-2.svg"],
        win: ["tall-win-1.svg"],
        // filename typo: tall-milstone-1.svg
        milestone: ["tall-milstone-1.svg"],
        tired: ["tall-tired-1.svg"],
        embarrassed: ["tall-embarrassed-1.svg"],
        inactive: ["tall-inactive-1.svg"]
      }
    },
    junior: {
      id: "junior",
      label: "Pierogi Junior",
      bodySymbolId: "pierogi-junior",
      faces: {
        neutral: ["junior-neutral-1.svg", "junior-neutral-2.svg"],
        win: ["junior-neutral-2.svg"], // no explicit win; reuse a neutral
        milestone: ["junior-milestone-1.svg"],
        tired: ["junior-tired-1.svg"],
        // filename typo: junior-emarrassed-1.svg
        embarrassed: ["junior-emarrassed-1.svg"],
        inactive: ["junior-inactive-1.svg"]
      }
    }
  };

  function getChar(id) {
    if (CHAR_DEFS[id]) return CHAR_DEFS[id];
    // Fallback for legacy avatar ids like "scout", "fox", etc.
    return CHAR_DEFS.hero;
  }

  function randFrom(list) {
    if (!Array.isArray(list) || !list.length) return null;
    const i = Math.floor(Math.random() * list.length);
    return list[i];
  }

  function pickFaceFile(charId, mood) {
    const ch = getChar(charId);
    const m = (mood || "neutral").toLowerCase();

    const faces = ch.faces || {};
    const exact = faces[m];
    if (exact && exact.length) return randFrom(exact);

    const neutrals = faces.neutral;
    if (neutrals && neutrals.length) return randFrom(neutrals);

    // Last resort: first image from any mood
    for (const key of Object.keys(faces)) {
      const arr = faces[key];
      if (arr && arr.length) return arr[0];
    }
    return null;
  }

  // ---- Core render: body + face into a container ---------------------------

  function clearNode(el) {
    if (!el) return;
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function renderAvatar(container, charId, mood) {
    if (!container) return;

    const ch = getChar(charId);
    const faceFile = pickFaceFile(charId, mood);

    clearNode(container);

    // Fallback: simple emoji if something goes very wrong
    if (!ch) {
      container.textContent = "🙂";
      return;
    }

    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", VIEWBOX);
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    svg.setAttribute("xmlns:xlink", XLINK_NS);

    // Body from pierogi.svg symbol
    const useBody = document.createElementNS(SVG_NS, "use");
    const hrefVal = ROOT + "pierogi.svg#" + ch.bodySymbolId;
    // Old + new ways, for maximum browser compatibility
    useBody.setAttributeNS(XLINK_NS, "href", hrefVal);
    useBody.setAttribute("href", hrefVal);

    svg.appendChild(useBody);

    // Face overlay as an <image>, aligned to full viewBox (200x200)
    if (faceFile) {
      const img = document.createElementNS(SVG_NS, "image");
      const faceHref = ROOT + faceFile;

      img.setAttribute("x", "0");
      img.setAttribute("y", "0");
      img.setAttribute("width", "200");
      img.setAttribute("height", "200");
      img.setAttributeNS(XLINK_NS, "href", faceHref);
      img.setAttribute("href", faceHref);

      svg.appendChild(img);
    }

    container.appendChild(svg);
  }

  // ---- Profile page integration --------------------------------------------

  function initProfileAvatar(options) {
    const opts = options || {};
    const big = document.getElementById("avatarBig");
    const btn = document.getElementById("chooseAvatarBtn");
    const modal = document.getElementById("avatarModal");
    const grid = document.getElementById("avatarGrid");
    const closeBtn = document.getElementById("avatarModalClose");
    const doneBtn = document.getElementById("avatarModalDone");

    if (!big || !btn || !modal || !grid) {
      return;
    }

    let currentId = opts.initialId || "hero";
    if (!CHAR_DEFS[currentId]) {
      currentId = "hero";
    }

    function updateBig() {
      // Use neutral mood for the static profile avatar
      renderAvatar(big, currentId, "neutral");
    }

    function syncGrid() {
      const items = grid.querySelectorAll(".ava");
      items.forEach((el) => {
        const id = el.getAttribute("data-id");
        el.classList.toggle("active", id === currentId);
      });
    }

    // Build the avatar options inside the modal grid
    clearNode(grid);
    Object.values(CHAR_DEFS).forEach((ch) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "ava";
      btn.setAttribute("data-id", ch.id);
      btn.setAttribute("role", "option");
      btn.setAttribute("aria-label", ch.label);

      const previewBox = document.createElement("div");
      previewBox.style.width = "56px";
      previewBox.style.height = "56px";

      renderAvatar(previewBox, ch.id, "neutral");
      btn.appendChild(previewBox);

      const label = document.createElement("div");
      label.className = "tiny";
      label.style.marginTop = "4px";
      label.textContent = ch.label;
      btn.appendChild(label);

      btn.addEventListener("click", () => {
        currentId = ch.id;
        syncGrid();
      });

      grid.appendChild(btn);
    });

    function openModal() {
      modal.classList.add("show");
      document.body.classList.add("modal-open");
      syncGrid();
    }
    function closeModal() {
      modal.classList.remove("show");
      document.body.classList.remove("modal-open");
    }

    btn.addEventListener("click", openModal);
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (doneBtn) {
      doneBtn.addEventListener("click", () => {
        closeModal();
        updateBig();
        if (typeof opts.onChange === "function") {
          opts.onChange(currentId);
        }
      });
    }

    // Initial render in the big square
    updateBig();
  }

  // ---- Export ---------------------------------------------------------------

  global.AvatarChooser = {
    renderAvatar,
    initProfileAvatar,
    getCharIds: function () {
      return Object.keys(CHAR_DEFS);
    }
  };
})(window);
