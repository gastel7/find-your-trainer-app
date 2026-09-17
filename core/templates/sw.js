const CACHE_NAME = 'fyt-cache-v1';

self.addEventListener('install', () => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
    // Stratégie minimale : réseau d'abord, cache en secours
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});