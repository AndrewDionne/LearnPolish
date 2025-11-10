/* practice SW */
self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { self.clients.claim(); });

function toAbs(u){
  try { return new URL(u, self.registration.scope || self.location.href).href; }
  catch(_) { return null; }
}

self.addEventListener('message', async (e) => {
  const data = e.data || {};
  const client = await self.clients.get(e.source && e.source.id);
  if (data.type === 'CACHE_SET') {
    const cacheName = data.cache || 'practice-cache';
    const urls = Array.isArray(data.urls) ? data.urls.map(toAbs).filter(Boolean) : [];
    try {
      const cache = await caches.open(cacheName);
      let done = 0, total = urls.length;
      for (const u of urls) {
        try {
          const res = await fetch(u, { mode: 'cors' });
          if (res.ok || res.type === 'opaque') {
            await cache.put(u, res);
          }
        } catch (_) { /* skip failed */ }
        done++;
        client && client.postMessage({ type: 'CACHE_PROGRESS', done, total });
      }
      client && client.postMessage({ type: 'CACHE_DONE', cache: cacheName });
    } catch (err) {
      client && client.postMessage({ type: 'CACHE_ERROR', error: String(err) });
    }
  } else if (data.type === 'UNCACHE_SET') {
    const cacheName = data.cache || 'practice-cache';
    await caches.delete(cacheName);
    client && client.postMessage({ type: 'UNCACHE_DONE', cache: cacheName });
  }
});

// Cache-first for anything we have; otherwise fall through to network
self.addEventListener('fetch', (event) => {
  event.respondWith((async () => {
    const reqUrl = event.request.url;
    const names = await caches.keys();
    for (const name of names) {
      const cache = await caches.open(name);
      const hit = await cache.match(reqUrl, { ignoreSearch: true });
      if (hit) return hit;
    }
    try { return await fetch(event.request); } catch (_) { return new Response('', { status: 504 }); }
  })());
});
