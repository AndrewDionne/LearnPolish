// docs/static/js/avatar.js
// Pierogi avatar chooser used on profile.html

const AvatarChooser = (() => {
  const SPRITE_PATH = "static/avatar/pierogi.svg";   // bodies
  const FACE_PATH   = "static/avatar/";              // individual face SVGs
  const DEFAULT_FACE = "neutral-1";

  const AVATARS = [
    { id: "hero",   label: "Pierogi Hero" },
    { id: "chonky", label: "Pierogi Chonky" },
    { id: "tall",   label: "Pierogi Tall" },
    { id: "junior", label: "Pierogi Junior" }
  ];

  const SVG_NS   = "http://www.w3.org/2000/svg";
  const XLINK_NS = "http://www.w3.org/1999/xlink";

  function buildSvgAvatar(id, sizePx) {
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 200 200");
    if (sizePx) {
      svg.setAttribute("width", String(sizePx));
      svg.setAttribute("height", String(sizePx));
    }

    // Body (from pierogi.svg symbol)
    const bodySymbolId = `pierogi-${id}`;
    const use = document.createElementNS(SVG_NS, "use");
    const bodyHref = `${SPRITE_PATH}#${bodySymbolId}`;
    use.setAttributeNS(XLINK_NS, "xlink:href", bodyHref);
    use.setAttribute("href", bodyHref);
    svg.appendChild(use);

    // Face (separate SVG, same 200x200 viewBox)
    const img = document.createElementNS(SVG_NS, "image");
    const faceHref = `${FACE_PATH}${id}-${DEFAULT_FACE}.svg`;
    img.setAttributeNS(XLINK_NS, "xlink:href", faceHref);
    img.setAttribute("href", faceHref);
    img.setAttribute("x", "0");
    img.setAttribute("y", "0");
    img.setAttribute("width", "200");
    img.setAttribute("height", "200");
    svg.appendChild(img);

    return svg;
  }

  function initProfileAvatar(options) {
    const initialId = (options && options.initialId) || "hero";
    const onChange  = (options && options.onChange) || (() => {});

    const bigEl    = document.getElementById("avatarBig");
    const openBtn  = document.getElementById("chooseAvatarBtn");
    const modal    = document.getElementById("avatarModal");
    const grid     = document.getElementById("avatarGrid");
    const closeBtn = document.getElementById("avatarModalClose");
    const doneBtn  = document.getElementById("avatarModalDone");

    if (!bigEl || !openBtn || !modal || !grid) {
      return;
    }

    let currentId = AVATARS.some(a => a.id === initialId) ? initialId : "hero";

    function renderBig() {
      bigEl.innerHTML = "";
      bigEl.appendChild(buildSvgAvatar(currentId, 88));
    }

    function renderGrid() {
      grid.innerHTML = "";
      AVATARS.forEach(av => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ava" + (av.id === currentId ? " active" : "");
        btn.setAttribute("data-id", av.id);
        btn.setAttribute("role", "option");
        btn.setAttribute("aria-label", av.label);

        const svg = buildSvgAvatar(av.id, 56);
        btn.appendChild(svg);

        const label = document.createElement("span");
        label.className = "tiny";
        label.textContent = av.label;
        btn.appendChild(label);

        btn.addEventListener("click", () => {
          currentId = av.id;
          renderBig();
          renderGrid();
        });

        grid.appendChild(btn);
      });
    }

    function openModal() {
      modal.classList.add("show");
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("modal-open");
    }

    function closeModal() {
      modal.classList.remove("show");
      modal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("modal-open");
    }

    openBtn.addEventListener("click", openModal);
    if (closeBtn) {
      closeBtn.addEventListener("click", closeModal);
    }
    if (doneBtn) {
      doneBtn.addEventListener("click", () => {
        onChange(currentId);
        closeModal();
      });
    }

    // Click on dark overlay to close
    modal.addEventListener("click", (ev) => {
      if (ev.target === modal) {
        closeModal();
      }
    });

    // Initial render
    renderBig();
    renderGrid();
  }

  return { initProfileAvatar };
})();
