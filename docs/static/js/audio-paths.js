// ===== audio-paths.js (unified) =====
// Purpose: One place to resolve audio/asset URLs across modes (flashcards, practice, listening, reading)
// - Tries per-set r2_manifest.json first (if present)
// - Falls back to assetsBase in manifest (CDN base)
// - Finally falls back to local: ../../static/<set>/<folder>/<file>
// Exports:
//   AudioPaths.fetchManifest(setName)
//   AudioPaths.buildAudioPath(setName, index, item, manifest)   // flashcards/practice
//   AudioPaths.resolveListening(setName, item, manifest)        // listening dialogs
//   AudioPaths.readingPath(setName, index, manifest)            // reading passages

(function (w) {
  const APP = w.APP_CONFIG || {};

  function sanitize(t) {
    return (t || "")
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-zA-Z0-9_-]+/g, "_")
      .replace(/^_+|_+$/g, "");
  }
  function isAbs(u) { return !!u && /^(https?:)?\/\//i.test(String(u)); }

  async function fetchManifest(setName) {
    const base = `../../static/${encodeURIComponent(setName)}`;
    const probes = [
      `${base}/r2_manifest.json`,   // per-set
      `../../static/r2_manifest.json` // legacy/global
    ];
    for (const u of probes) {
      try {
        const r = await fetch(u, { cache: "no-cache" });
        if (r.ok) return await r.json();
      } catch (_) {}
    }
    return null;
  }

  // Core resolver used by helpers below
  function resolveSetAsset(setName, relOrFile, folder, manifest) {
    // Absolute wins
    if (isAbs(relOrFile)) return relOrFile;

    const rel = String(relOrFile || "").replace(/^\/+/, "");
    const file = rel.includes("/") ? rel.split("/").pop() : rel;

    // Choose a canonical key for manifest lookups
    const key = (folder && file) ? `${folder}/${setName}/${file}` :
      (rel ? `${setName}/${rel}` : "");

    // Manifest → direct file mapping
    if (manifest && manifest.files && key && manifest.files[key]) {
      return manifest.files[key];
    }

    // Manifest → assetsBase fallback
    const base = (manifest && (manifest.assetsBase || manifest.cdn || manifest.base)) || APP.assetsBase || "";
    if (base && key) return String(base).replace(/\/$/, "") + "/" + key;

    // Local static fallback
    const setEnc = encodeURIComponent(setName);
    // If rel already has folder prefix (e.g., "listening/d001.mp3"), keep it; else add folder if present
    const relNorm = rel
      ? rel
      : (folder && file ? `${folder}/${file}` : "");
    return `../../static/${setEnc}/${encodeURIComponentPath(relNorm)}`;
  }

  // encode path but keep slashes
  function encodeURIComponentPath(p) {
    return (p || "").split("/").map(encodeURIComponent).join("/");
  }

  // ---- Mode helpers ----

  // Flashcards/Practice: item.audio_url (abs) | item.audio (abs) | audio/<set>/<idx>_<phrase>.mp3
  function buildAudioPath(setName, index, item, manifest) {
    const explicit = (item && (item.audio_url || item.audio)) || "";
    if (isAbs(explicit)) return explicit;

    const fn = (item && item.audio_file)
      ? String(item.audio_file)
      : `${index}_${sanitize(item?.phrase || item?.polish || "")}.mp3`;

    // rel path expected by manifest = "audio/<set>/<file>"
    return resolveSetAsset(setName, `audio/${fn}`, "audio", manifest);
  }

  // Listening dialogs: honor abs URL, else "listening/<set>/<file>"
  function resolveListening(setName, item, manifest) {
    const abs = (item && (item.audio_url || item.audio)) || "";
    if (isAbs(abs)) return abs;

    // Accept either "listening/dXXX.mp3" or just "dXXX.mp3"
    const rel = String(item && item.audio || "").replace(/^\/+/, "");
    const file = rel ? rel.split("/").pop() : ((item && item.id) ? `${item.id}.mp3` : "");
    const relNorm = rel && rel.startsWith("listening/") ? rel : (file ? `listening/${file}` : "");
    return resolveSetAsset(setName, relNorm, "listening", manifest);
  }

  // Reading passages: "reading/<index>.mp3"
  function readingPath(setName, index, manifest) {
    const rel = `reading/${index}.mp3`;
    return resolveSetAsset(setName, rel, "reading", manifest);
  }

  w.AudioPaths = { fetchManifest, buildAudioPath, resolveListening, readingPath };
})(window);
