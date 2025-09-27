// docs/static/js/session_state.js
// Tiny helper for saving/restoring in-progress sessions via /api/session_state
// Usage from a mode page:
//   await SessionSync.restore({ setName, mode }, (progress) => { ...apply... });
//   SessionSync.save({ setName, mode, progress: { index, ... } });
//   SessionSync.complete({ setName, mode });

window.SessionSync = {
  async restore({ setName, mode }, apply) {
    try {
      const url = '/api/session_state?set=' + encodeURIComponent(setName) +
                  '&mode=' + encodeURIComponent(mode);
      const r = await api.fetch(url);
      if (!r.ok) return false;
      const ss = await r.json();
      if (ss && ss.progress && typeof apply === 'function') {
        apply(ss.progress);
      }
      return true;
    } catch (_) { return false; }
  },

  async save({ setName, mode, progress }) {
    try {
      await api.fetch('/api/session_state', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ set_name:setName, mode, progress })
      });
    } catch (_) {}
  },

  async complete({ setName, mode }) {
    try {
      await api.fetch('/api/session_state/complete', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ set_name:setName, mode })
      });
    } catch (_) {}
  }
};
