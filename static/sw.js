/* Sonara — service worker: cachea estáticos y audio ya reproducido para uso offline. */
'use strict';

const STATIC_CACHE = 'sonara-static-v2';
const AUDIO_CACHE = 'sonara-audio-v1';
const STATIC_ASSETS = ['/static/css/app.css?v=4', '/static/js/app.js?v=4', '/static/js/player.js?v=4', '/static/icons/icon.svg'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(STATIC_CACHE).then((c) => c.addAll(STATIC_ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== STATIC_CACHE && k !== AUDIO_CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'clear-audio-cache') {
    caches.delete(AUDIO_CACHE);
  }
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Audio: cache-first una vez descargado, para poder reescuchar sin red.
  if (url.pathname.startsWith('/api/stream/')) {
    event.respondWith(
      caches.open(AUDIO_CACHE).then(async (cache) => {
        const cached = await cache.match(event.request);
        if (cached) return cached;
        try {
          const resp = await fetch(event.request);
          if (resp.ok) cache.put(event.request, resp.clone());
          return resp;
        } catch (e) {
          return cached || Promise.reject(e);
        }
      })
    );
    return;
  }

  // API: siempre red (datos dinámicos).
  if (url.pathname.startsWith('/api/')) return;

  // Estáticos: cache-first.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
  }
});
