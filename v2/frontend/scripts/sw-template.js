/* Path to Polish V2 — minimal same-origin offline service worker.
 * Built app shell resources are inserted by build-offline.mjs; do not edit dist/sw.js.
 */
const VERSION = /*__APP_CACHE_VERSION__*/;
const PRECACHE = /*__PRECACHE_RESOURCES__*/;
const SHELL_PREFIX = 'ptp-v2-shell-';
const SHELL = SHELL_PREFIX + VERSION;
const LESSONS = 'ptp-v2-lesson-audio-v1';
const SCOPE = self.registration.scope;

function resolveAudioPaths(urls) {
  if (!Array.isArray(urls) || urls.length > 150) throw new Error('Too many audio items in offline request');
  const list = [...new Set(urls)];
  return list.map(relative => {
    if (typeof relative !== 'string' ||
        !/^generated\/audio\/[a-zA-Z0-9_%.-]+\/[0-9]+\.mp3$/.test(relative)) {
      throw new Error('Only trusted bundled lesson MP3s can be downloaded');
    }
    const absolute = new URL(relative, SCOPE);
    if (absolute.origin !== new URL(SCOPE).origin || !absolute.href.startsWith(SCOPE + 'generated/audio/')) {
      throw new Error('Audio must belong to this application');
    }
    return absolute.href;
  });
}

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL);
    await cache.addAll(PRECACHE.map(x => new URL(x, SCOPE).href));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith(SHELL_PREFIX) && name !== SHELL).map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== new URL(SCOPE).origin || !url.href.startsWith(SCOPE)) return;
  const relative = url.href.slice(SCOPE.length);
  if (relative.startsWith('generated/audio/')) {
    // Only explicitly downloaded audio is made available offline.
    event.respondWith((async () => (await (await caches.open(LESSONS)).match(request, { ignoreVary: true })) || fetch(request))());
    return;
  }
  if (request.mode === 'navigate') {
    // Prefer the live single-origin Render response so a sleeping/unready
    // backend can withhold the app instead of showing a stale cached shell.
    // Only when truly disconnected do we fall back to verified offline UI.
    event.respondWith((async () => {
      try {
        return await fetch(request);
      } catch {
        const shell = await caches.open(SHELL);
        return (await shell.match(new URL('./', SCOPE).href)) || Response.error();
      }
    })());
    return;
  }
  event.respondWith((async () => {
    const shell = await caches.open(SHELL);
    // Module scripts may have an Origin header that differs from install requests.
    // This is safe for exact same-origin, same-URL cached static assets.
    const cached = await shell.match(request, { ignoreVary: true });
    return cached || fetch(request);
  })());
});

self.addEventListener('message', event => {
  const port = event.ports && event.ports[0];
  if (!port) return;
  event.waitUntil((async () => {
    const type = event.data && event.data.type;
    const urls = resolveAudioPaths(event.data && event.data.urls);
    const cache = await caches.open(LESSONS);
    const report = data => port.postMessage(data);
    if (type === 'STATUS') {
      let done = 0;
      for (const url of urls) if (await cache.match(url)) done++;
      report({ type: 'done', ready: urls.length > 0 && urls.length === done, done, total: urls.length });
      return;
    }
    if (type === 'REMOVE') {
      // Removing several audio clips must be all-or-nothing as far as storage
      // permits. A failed deletion must not strand a previously ready lesson.
      const originals = new Map();
      const touched = [];
      for (const url of urls) originals.set(url, await cache.match(url));
      try {
        for (const url of urls) {
          touched.push(url); // Track before delete: the operation may throw.
          await cache.delete(url);
        }
        for (const url of urls) {
          if (await cache.match(url)) throw new Error('Offline copy removal could not be verified');
        }
      } catch (error) {
        let rollbackFailed = false;
        for (const url of touched.reverse()) {
          try {
            const previous = originals.get(url);
            if (previous) await cache.put(url, previous);
            else await cache.delete(url);
          } catch { rollbackFailed = true; }
        }
        if (rollbackFailed) throw new Error('Offline removal failed; some audio may be missing. Check offline status and retry.');
        throw error;
      }
      report({ type: 'done', ready: false, done: 0, total: urls.length });
      return;
    }
    if (type !== 'DOWNLOAD' || urls.length === 0) throw new Error('No downloadable audio found');
    const tempName = 'ptp-v2-temporary-' + Date.now() + '-' + Math.random();
    try {
      const staging = await caches.open(tempName);
      let completed = 0;
      for (const url of urls) {
        const response = await fetch(url, { cache: 'no-store', credentials: 'same-origin' });
        const contentType = response.headers.get('content-type') || '';
        if (!response.ok || (!contentType.includes('audio/') && !contentType.includes('application/octet-stream'))) {
          throw new Error('Audio could not be downloaded and verified');
        }
        await staging.put(url, response);
        completed++;
        report({ type: 'progress', done: completed, total: urls.length });
      }
      // Keep existing files intact and roll back any promoted files if the
      // durable cache runs out of space halfway through a multi-file download.
      // Staged progress is not evidence of a completed offline lesson.
      const originals = new Map();
      const promoted = [];
      try {
        for (const url of urls) {
          const stored = await staging.match(url);
          if (!stored) throw new Error('Offline staging failed');
          originals.set(url, await cache.match(url));
          promoted.push(url); // Track before put; storage may fail during it.
          await cache.put(url, stored);
        }
        const verified = await Promise.all(urls.map(url => cache.match(url)));
        if (verified.some(item => !item)) throw new Error('Offline cache verification failed');
      } catch (error) {
        let rollbackFailed = false;
        for (const url of promoted.reverse()) {
          try {
            const previous = originals.get(url);
            if (previous) await cache.put(url, previous);
            else await cache.delete(url);
          } catch { rollbackFailed = true; }
        }
        if (rollbackFailed) throw new Error('Offline caching failed; incomplete files may remain. Retry download before relying on this lesson offline.');
        throw error;
      }
      report({ type: 'done', ready: true, done: urls.length, total: urls.length });
    } finally {
      await caches.delete(tempName);
    }
  })().catch(error => {
    port.postMessage({ type: 'error', message: error instanceof Error ? error.message : 'Offline download failed' });
  }));
});
