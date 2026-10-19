// Service worker של BET-IT: האפליקציה נפתחת גם בקליטה גרועה.
// הדף הראשי – קודם מהרשת (תמיד הגרסה הכי חדשה), ואם אין רשת – מהעותק השמור.
const CACHE = 'betit-v1';
const SHELL = ['/', '/index.html', '/og.png', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;          // נתונים חיים (Firebase) – תמיד מהרשת
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request).then(r => r || caches.match('/index.html'))));
});
