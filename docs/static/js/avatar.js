// docs/static/js/avatar.js
(function () {
  const AVATARS = [
    { id: "scout", glyph: "🧭" },
    { id: "fox", glyph: "🦊" },
    { id: "owl", glyph: "🦉" },
    { id: "bear", glyph: "🐻" },
    { id: "koala", glyph: "🐨" },
    { id: "dragon", glyph: "🐉" },
    { id: "mage", glyph: "🧙‍♂️" },
    { id: "ninja", glyph: "🥷" },
    { id: "robot", glyph: "🤖" },
    { id: "books", glyph: "📚" },
    { id: "rocket", glyph: "🚀" },
    { id: "clover", glyph: "🍀" }
  ];

  function glyphFor(id) {
    const found = AVATARS.find(a => a.id === id);
    return found ? found.glyph : "🙂";
  }

  function renderGrid(root, currentId, onSelect) {
    if (!root) return;
    root.innerHTML = "";

    const selected = currentId || "scout";

    AVATARS.forEach(a => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "ava" + (a.id === selected ? " active" : "");
      btn.setAttribute("role", "option");
      btn.setAttribute("aria-label", a.id);
      btn.dataset.id = a.id;
      btn.textContent = a.glyph;

      btn.addEventListener("click", () => {
        root.querySelectorAll(".ava").forEach(el => {
          el.classList.toggle("active", el === btn);
        });
        if (typeof onSelect === "function") onSelect(a.id);
      });

      root.appendChild(btn);
    });
  }

  function initProfileAvatar(opts) {
    const options = opts || {};
    const bigId    = options.bigId    || "avatarBig";
    const buttonId = options.buttonId || "chooseAvatarBtn";
    const modalId  = options.modalId  || "avatarModal";
    const gridId   = options.gridId   || "avatarGrid";
    const closeId  = options.closeId  || "avatarModalClose";
    const doneId   = options.doneId   || "avatarModalDone";
    const onChange = typeof options.onChange === "function" ? options.onChange : null;
    let current    = options.initialId || "scout";

    const bigEl   = document.getElementById(bigId);
    const btn     = document.getElementById(buttonId);
    const modal   = document.getElementById(modalId);
    const grid    = document.getElementById(gridId);
    const close   = document.getElementById(closeId);
    const done    = document.getElementById(doneId);

    if (!bigEl || !btn || !modal || !grid) {
      return null;
    }

    function updateBig() {
      bigEl.textContent = glyphFor(current);
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

    btn.addEventListener("click", (ev) => {
      ev.preventDefault();
      renderGrid(grid, current, (id) => {
        current = id;
        updateBig();
        if (onChange) onChange(id);
      });
      openModal();
    });

    if (close) {
      close.addEventListener("click", (ev) => {
        ev.preventDefault();
        closeModal();
      });
    }

    if (done) {
      done.addEventListener("click", (ev) => {
        ev.preventDefault();
        closeModal();
      });
    }

    // Click outside dialog closes
    modal.addEventListener("click", (ev) => {
      if (ev.target === modal) {
        closeModal();
      }
    });

    // Initial render of big avatar
    updateBig();

    return {
      getCurrent: () => current,
      setCurrent: (id) => {
        current = id;
        updateBig();
      }
    };
  }

  window.AvatarChooser = {
    AVATARS,
    glyphFor,
    initProfileAvatar
  };
})();
