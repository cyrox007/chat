import { readFileSync } from 'node:fs';

const manifest = JSON.parse(readFileSync(new URL('../public/favicons/site.webmanifest', import.meta.url), 'utf8'));
const worker = readFileSync(new URL('../public/service-worker.js', import.meta.url), 'utf8');
const registration = readFileSync(new URL('../src/pwa/registerServiceWorker.js', import.meta.url), 'utf8');

const fail = (message) => {
  console.error(`PWA guard failed: ${message}`);
  process.exitCode = 1;
};

if (manifest.name !== 'PubChat' || manifest.short_name !== 'PubChat') {
  fail('manifest must identify PubChat');
}
if (manifest.start_url !== '/' || manifest.scope !== '/') {
  fail('manifest start_url/scope must remain app-root relative');
}
if (!Array.isArray(manifest.icons) || !manifest.icons.some((icon) => icon.sizes === '192x192') || !manifest.icons.some((icon) => icon.sizes === '512x512')) {
  fail('manifest must include 192x192 and 512x512 icons');
}
if (!worker.includes("if (request.method !== 'GET') return;")) {
  fail('service worker must bypass non-GET requests');
}
if (!worker.includes("if (!isStaticAsset(request, url)) return;")) {
  fail('service worker must bypass non-static fetch/XHR requests');
}
if (!worker.includes("request.mode === 'navigate'")) {
  fail('service worker must handle navigation separately from API/static traffic');
}
if (!worker.includes("STATIC_DESTINATIONS")) {
  fail('runtime caching must be constrained by browser destination');
}
if (!registration.includes("import.meta.env.PROD")) {
  fail('service worker must only register in production builds');
}

if (process.exitCode) process.exit(process.exitCode);
console.log('PWA manifest/service-worker guard passed');
