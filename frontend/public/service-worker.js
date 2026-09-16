const SHELL_CACHE = 'pubchat-shell-v1';
const RUNTIME_CACHE = 'pubchat-runtime-v1';

const SHELL_URLS = [
  '/',
  '/index.html',
  '/favicons/site.webmanifest',
  '/favicons/favicon-32x32.png',
  '/favicons/android-chrome-192x192.png',
  '/favicons/android-chrome-512x512.png',
];

const STATIC_DESTINATIONS = new Set(['script', 'style', 'font', 'image']);

const isStaticAsset = (request, url) => {
  if (!STATIC_DESTINATIONS.has(request.destination)) return false;
  return url.pathname.startsWith('/assets/')
    || url.pathname.startsWith('/favicons/')
    || url.pathname === '/favicon.ico';
};

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL_URLS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith('pubchat-') && ![SHELL_CACHE, RUNTIME_CACHE].includes(key))
          .map((key) => caches.delete(key)),
      ))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Navigation gets network-first semantics. The cached index is only an offline
  // application shell; auth/API state is never persisted by this worker.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok && response.headers.get('content-type')?.includes('text/html')) {
            const clone = response.clone();
            caches.open(SHELL_CACHE).then((cache) => cache.put('/index.html', clone));
          }
          return response;
        })
        .catch(async () => (
          (await caches.match('/index.html'))
          || (await caches.match('/'))
          || Response.error()
        )),
    );
    return;
  }

  // Only static browser resources are cached. fetch/XHR/API requests have an
  // empty destination and intentionally bypass the service worker cache.
  if (!isStaticAsset(request, url)) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, clone));
        }
        return response;
      });
      return cached || network;
    }),
  );
});
