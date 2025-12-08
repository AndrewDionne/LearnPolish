// docs/offline/sw.js

const SHELL_CACHE = "ptp-offline-shell-v1";
const PACK_PREFIX = "ptp-offline-pack-";

self.addEventListener("install", (event) => {
  // Pre-cache the offline shell
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) =>
        cache.addAll([
          "./index.html",
          "./vocab.html",
          "./reading.html",
          "./vocab.js",
          "./reading.js",
          "../static/app.css",
          "../static/js/app-config.js",
          "../static/js/audio-paths.js"
        ])
      )
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      // Basic old-cache cleanup
      const keys = await caches.keys();
      await Promise.all(
        keys.map((key) => {
          if (
            key.startsWith("ptp-offline-shell-") &&
            key !== SHELL_CACHE
          ) {
            return caches.delete(key);
          }
          if (key.startsWith(PACK_PREFIX) && !key.startsWith(PACK_PREFIX)) {
            // placeholder; we keep all packs for now
            return Promise.resolve();
          }
          return Promise.resolve();
        })
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener("message", (event) => {
  const msg = event.data || {};
  if (msg.type === "CACHE_PACK") {
    const packId = String(msg.pack || "default");
    const urls = Array.isArray(msg.urls) ? msg.urls : [];
    const cacheName = PACK_PREFIX + packId;

    if (!urls.length) return;

    event.waitUntil(
      (async () => {
        const cache = await caches.open(cacheName);
        try {
          await cache.addAll(urls);
        } catch (err) {
          // On some browsers, cross-origin + opaque responses might throw for addAll;
          // fall back to individual fetches.
          for (const u of urls) {
            try {
              const req = new Request(u, { mode: "no-cors" });
              const resp = await fetch(req);
              if (resp && (resp.ok || resp.type === "opaque")) {
                await cache.put(req, resp);
              }
            } catch (_) {}
          }
        }
      })()
    );
  }
});

self.addEventListener("fetch", (event) => {
  const req = event.request;

  event.respondWith(
    (async () => {
      // 1) Try any offline cache (shell or packs)
      const cached = await caches.match(req);
      if (cached) return cached;

      try {
        // 2) Network as normal
        return await fetch(req);
      } catch (err) {
        // 3) On complete failure, try a friendly fallback for HTML navigations
        if (req.mode === "navigate") {
          const fallback = await caches.match("./index.html");
          if (fallback) return fallback;
        }
        throw err;
      }
    })()
  );
});
