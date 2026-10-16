import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const appRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dist = path.join(appRoot, 'dist');
const template = path.join(appRoot, 'scripts', 'sw-template.js');
const assetDir = path.join(dist, 'assets');

export function shellResources(baseDir = dist) {
  const assets = fs.existsSync(path.join(baseDir, 'assets'))
    ? fs.readdirSync(path.join(baseDir, 'assets')).filter(name => /\.(?:js|css)$/.test(name)).sort()
      .map(name => 'assets/' + name)
    : [];
  return ['./', 'index.html', 'generated/lessons.json', ...assets];
}

export function writeServiceWorker() {
  const manifestFile = path.join(dist, 'generated/lessons.json');
  if (!fs.existsSync(manifestFile)) throw new Error('Prepare lesson content before building offline shell');
  const precache = shellResources();
  if (precache.length < 4) throw new Error('Expected bundled JS/CSS assets before producing a service worker');
  const hash = createHash('sha256').update(precache.join('\n')).update(fs.readFileSync(manifestFile)).digest('hex').slice(0, 16);
  const output = fs.readFileSync(template, 'utf8')
    .replace('/*__APP_CACHE_VERSION__*/', JSON.stringify(hash))
    .replace('/*__PRECACHE_RESOURCES__*/', JSON.stringify(precache));
  fs.writeFileSync(path.join(dist, 'sw.js'), output);
  return { cacheVersion: hash, precacheCount: precache.length };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log('Generated offline app shell:', writeServiceWorker());
}
