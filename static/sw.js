/* Sonara — service worker: cachea estáticos y audio ya reproducido para uso offline. */
'use strict';

const STATIC_CACHE = 'sonara-static-v4';
const AUDIO_CACHE = 'sonara-audio-v2';

// Solo assets sin versión en la URL (los .css/.js versionados ?v=N se cachean
// solos al primer fetch gracias a la estrategia cache-first de abajo; así no
// hay que acordarse de mantener esta lista sincronizada en cada despliegue).
const STATIC_ASSETS = [
  '/static/icons/icon.svg',
  '/static/images/logo.png',
  '/static/images/favicon-32.png',
  '/static/images/favicon-16.png',
  '/static/manifest.json',
];

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

  if (url.pathname.startsWith('/api/stream/')) {
    event.respondWith(handleStream(event.request));
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

/**
 * Streaming de audio: cachea SIEMPRE el fichero completo (clave = la URL sin
 * query/Range) y, si ya está en caché, sirve cualquier petición con Range
 * recortando el blob guardado en el propio service worker. Así una canción
 * ya escuchada se puede volver a buscar (seek) sin red, con el byte-range
 * correcto — cachear directamente la respuesta 206 parcial del servidor
 * rompería el seek, porque Cache.match() solo compara por URL, no por el
 * header Range de cada petición.
 */
async function handleStream(request) {
  const cacheKey = new URL(request.url).pathname; // sin query ni Range
  const cache = await caches.open(AUDIO_CACHE);
  const cached = await cache.match(cacheKey);
  if (cached) return sliceCachedResponse(cached, request);

  const response = await fetch(request);
  const total = responseTotalSize(response);
  if (response.ok && total != null && isWholeFileResponse(response, total)) {
    cache.put(cacheKey, await toFullCacheableResponse(response.clone(), total));
  }
  return response;
}

function responseTotalSize(response) {
  const contentRange = response.headers.get('content-range');
  if (contentRange) {
    const m = /\/(\d+)$/.exec(contentRange);
    return m ? parseInt(m[1], 10) : null;
  }
  const len = response.headers.get('content-length');
  return len ? parseInt(len, 10) : null;
}

function isWholeFileResponse(response, total) {
  if (response.status === 200) return true;
  if (response.status !== 206) return false;
  const contentRange = response.headers.get('content-range');
  const m = contentRange && /bytes (\d+)-(\d+)\//.exec(contentRange);
  return !!m && parseInt(m[1], 10) === 0 && parseInt(m[2], 10) === total - 1;
}

async function toFullCacheableResponse(response, total) {
  const blob = await response.blob();
  return new Response(blob, {
    status: 200,
    headers: { 'Content-Type': 'audio/mpeg', 'Content-Length': String(total), 'Accept-Ranges': 'bytes' },
  });
}

async function sliceCachedResponse(cachedResponse, request) {
  const rangeHeader = request.headers.get('range');
  if (!rangeHeader) return cachedResponse.clone();

  const blob = await cachedResponse.clone().blob();
  const size = blob.size;
  const match = /bytes=(\d*)-(\d*)/.exec(rangeHeader);
  const start = match && match[1] ? parseInt(match[1], 10) : 0;
  let end = match && match[2] ? parseInt(match[2], 10) : size - 1;
  end = Math.min(end, size - 1);
  if (Number.isNaN(start) || start > end || start >= size) {
    return new Response(null, { status: 416, headers: { 'Content-Range': `bytes */${size}` } });
  }
  const sliced = blob.slice(start, end + 1);
  return new Response(sliced, {
    status: 206,
    headers: {
      'Content-Type': 'audio/mpeg',
      'Content-Range': `bytes ${start}-${end}/${size}`,
      'Accept-Ranges': 'bytes',
      'Content-Length': String(end - start + 1),
    },
  });
}
