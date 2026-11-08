#!/usr/bin/env node
// Reuse the source-locked V2 content compiler. No invented sample lessons.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(scriptDir, '../../..');
const ios = path.resolve(scriptDir, '..');
const src = path.join(repo, 'v2/frontend/public/generated');
const dst = path.join(ios, 'Resources/generated');

execFileSync('node', [path.join(repo, 'v2/frontend/scripts/prepare-content.mjs')], { cwd: repo, stdio: 'inherit' });
const manifest = JSON.parse(fs.readFileSync(path.join(src, 'lessons.json'), 'utf8'));
if (manifest.schemaVersion !== 1 || !Array.isArray(manifest.lessons) || manifest.lessons.length < 26) {
  throw new Error('V2 catalog missing or unexpectedly smaller; native build refused');
}
const ids = new Set();
let items = 0;
let audio = 0;
for (const lesson of manifest.lessons) {
  if (!lesson.id || !Array.isArray(lesson.items) || !lesson.items.length) throw new Error('Invalid lesson');
  if (ids.has(lesson.id)) throw new Error('Duplicate lesson ID: ' + lesson.id);
  ids.add(lesson.id);
  for (const item of lesson.items) {
    if (!item.id || !item.polish?.trim() || !item.english?.trim() || ids.has(item.id)) {
      throw new Error('Missing, empty or duplicate source item: ' + item.id);
    }
    ids.add(item.id);
    items++;
    if (!item.audio) continue;
    if (!item.audio.startsWith('generated/audio/')) throw new Error('Non-local audio reference: ' + item.id);
    const decoded = decodeURIComponent(item.audio.slice('generated/'.length));
    const local = path.resolve(src, decoded);
    if (!local.startsWith(src + path.sep) || !fs.existsSync(local) || fs.statSync(local).size === 0) {
      throw new Error('Missing or unsafe MP3 for ' + item.id);
    }
    audio++;
  }
}
if (items < 482 || audio < 455) throw new Error('V2 content/audio regression: ' + items + ' / ' + audio);
fs.rmSync(dst, { recursive: true, force: true });
fs.mkdirSync(path.dirname(dst), { recursive: true });
fs.cpSync(src, dst, { recursive: true });
const coreSource = JSON.parse(fs.readFileSync(path.join(repo, 'v2/content/core-journey-v1.json'), 'utf8'));
if (coreSource.schemaVersion !== 1 || coreSource.editorialStatus !== 'source-mapped-pilot_not_native-audio-certified' ||
    !Array.isArray(coreSource.placements) || coreSource.placements.length !== 21 ||
    new Set(coreSource.placements.map(x => x.lessonId)).size !== coreSource.placements.length ||
    coreSource.placements.some(x => !manifest.lessons.some(lesson => lesson.id === x.lessonId))) {
  throw new Error('V2 core-journey manifest does not match native lesson inventory');
}
fs.writeFileSync(path.join(dst, 'core-journey.json'), JSON.stringify(coreSource, null, 2) + '\\n');
fs.writeFileSync(path.join(dst, 'native-asset-report.json'), JSON.stringify({lessons:manifest.lessons.length,items,audioReferences:audio},null,2)+'\n');
console.log('Native offline assets verified:', { lessons: manifest.lessons.length, items, audioReferences: audio });
