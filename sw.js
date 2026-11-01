// Offline cache. Bump VERSION whenever index.html or anything in data/ changes:
// the old cache is dropped and the page downloads everything again on its next launch.
const VERSION = 1;
const CACHE = "lemiz-v" + VERSION;
const SHELL = ["index.html", "data/tomes.js", "manifest.webmanifest", "icon-180.png", "icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE)
    .then(c => c.addAll(SHELL.map(u => new Request(u, { cache: "reload" }))))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith("lemiz-") && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function respond(req) {
  const c = await caches.open(CACHE);
  const hit = await c.match(req.mode === "navigate" ? "index.html" : req, { ignoreSearch: true });
  if (hit) return hit;
  const r = await fetch(req);
  if (r.ok) await c.put(req, r.clone());
  return r;
}

self.addEventListener("fetch", e => {
  if (e.request.method === "GET" && new URL(e.request.url).origin === location.origin) e.respondWith(respond(e.request));
});
