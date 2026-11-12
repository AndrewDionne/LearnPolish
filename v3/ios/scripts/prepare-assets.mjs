#!/usr/bin/env node
// Reuse the source-locked V2 content compiler. No invented sample lessons.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { compileGuidedFoundations, readGuidedSources } from './prepare-guided.mjs';
import { compileSoundStudio, readSoundSources } from './prepare-sounds.mjs';
import { compileExposure, readExposureSources } from './prepare-exposure.mjs';
import { compileTouristUnits, readTouristSource } from './prepare-tourist.mjs';

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
const unifiedSource = JSON.parse(fs.readFileSync(path.join(repo, 'v3/content/journey1-unified-v1.json'), 'utf8'));
const unifiedEntries = unifiedSource.chapters?.flatMap(chapter => chapter.activities ?? []) ?? [];
const sourceCoreIds = new Set(coreSource.placements.filter(x => x.journey === 1).map(x => 'l:' + x.lessonId));
const sourceGuidedIds = new Set([
  'simple-replies', 'politeness', 'greetings', 'street-words',
  'transport-words', 'everyday-replies', 'grammar:requests',
  'grammar:where', 'grammar:permission', 'grammar:prices',
  'grammar:yes-no-questions', 'grammar:negative', 'grammar:one-two',
  'food-requests', 'shopping-questions', 'location-questions'
].map(x => 'g:' + x));
if (unifiedSource.schemaVersion !== 1 ||
    unifiedSource.editorialStatus !== 'source-mapped_unified_navigation_not_independently_linguistic_reviewed' ||
    unifiedSource.chapters?.length !== 8 || unifiedEntries.length !== 35 ||
    new Set(unifiedEntries).size !== 35 ||
    sourceCoreIds.size !== 19 || sourceGuidedIds.size !== 16 ||
    !unifiedEntries.every(ref => sourceCoreIds.has(ref) || sourceGuidedIds.has(ref)) ||
    ![...sourceCoreIds, ...sourceGuidedIds].every(ref => unifiedEntries.includes(ref)) ||
    unifiedSource.chapters.some(c => !c.id || !c.title || !c.description ||
      !c.activities?.length)) {
  throw new Error('Unified Journey 1 source no longer matches original guided and core inventories');
}
fs.writeFileSync(path.join(dst, 'unified-journey.json'),
  JSON.stringify(unifiedSource, null, 2) + '\n');

const regionsSource = JSON.parse(fs.readFileSync(path.join(repo, 'v2/frontend/src/expedition/regions.json'), 'utf8'));
if (!Array.isArray(regionsSource) || regionsSource.length !== 16 ||
    new Set(regionsSource.map(x => x.id)).size !== 16 ||
    !regionsSource.some(x => x.id === 'mazowieckie') ||
    regionsSource.some(x => !x.name || !x.path || !/^[-0-9.MLZ\s]+$/.test(x.path))) {
  throw new Error('V2 region geometry invalid or incomplete');
}
fs.writeFileSync(path.join(dst, 'regions.json'), JSON.stringify(regionsSource, null, 2) + '\n');
fs.writeFileSync(path.join(dst, 'core-journey.json'), JSON.stringify(coreSource, null, 2) + '\n');
const guided = compileGuidedFoundations(manifest, readGuidedSources(repo));
fs.writeFileSync(path.join(dst, 'guided-foundations.json'),
  JSON.stringify(guided, null, 2) + '\n');
const soundStudio = compileSoundStudio(manifest, readSoundSources(repo));
fs.writeFileSync(path.join(dst, 'sound-studio.json'), JSON.stringify(soundStudio, null, 2) + '\n');
const exposures = compileExposure(manifest, readExposureSources(repo));
fs.writeFileSync(path.join(dst, 'source-exposure.json'),
  JSON.stringify(exposures, null, 2) + '\n');
const tourist = compileTouristUnits(manifest, readTouristSource(repo));
fs.writeFileSync(path.join(dst, 'tourist-units.json'),
  JSON.stringify(tourist, null, 2) + '\n');
fs.writeFileSync(path.join(dst, 'native-asset-report.json'), JSON.stringify({lessons:manifest.lessons.length,items,audioReferences:audio},null,2)+'\n');
console.log('Native offline assets verified:', { lessons: manifest.lessons.length, items, audioReferences: audio });

if (process.platform !== 'darwin') {
  throw new Error('Native iPhone app icon rendering requires macOS (AppKit)');
}
const iconPath = path.join(ios, 'Resources/AppIcon.xcassets/AppIcon.appiconset/AppIcon.png');
execFileSync('swift', [path.join(scriptDir, 'render-app-icon.swift'), iconPath],
  { cwd: repo, stdio: 'inherit' });
