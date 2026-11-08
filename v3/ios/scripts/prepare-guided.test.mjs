import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { compileGuidedFoundations, readGuidedSources } from './prepare-guided.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const manifest = JSON.parse(fs.readFileSync(path.join(
  repo, 'v2/frontend/public/generated/lessons.json'), 'utf8'));
const sources = readGuidedSources(repo);
const clone = value => structuredClone(value);
const compile = (catalog = manifest, src = sources) => compileGuidedFoundations(catalog, src);

test('all 16 prerequisite-ordered guided sessions reuse 68 original recorded references', () => {
  const guided = compile();
  assert.equal(guided.steps.length, 16);
  assert.deepEqual(guided.steps.slice(0,6).map(s=>s.id), [
    'simple-replies','politeness','greetings',
    'street-words','transport-words','everyday-replies'
  ]);
  assert.deepEqual(guided.steps.slice(6,13).map(s=>s.id),
    ['grammar:requests','grammar:where','grammar:permission',
     'grammar:prices','grammar:yes-no-questions','grammar:negative','grammar:one-two']);
  assert.equal(guided.steps.reduce((n,s)=>n+s.items.length,0), 68);
  assert.equal(guided.steps.filter(s=>s.type==='grammar').length,7);
  assert.equal(guided.steps[0].items[0].id, 'Conversation_1:14');
  assert.equal(guided.steps[0].items[0].polish, 'Tak');
  for(const step of guided.steps){
    for(const item of step.items){
      assert.match(item.audio,/^generated\/audio\/[a-zA-Z0-9_%.-]+\/[0-9]+\.mp3$/);
      assert.ok(item.english.length > 0);
      if(step.type==='grammar'){
        assert.ok(item.focus.length > 0);
        assert.equal(item.polish.split(item.focus).length,2);
      }
    }
  }
});

test('guided source has no independent XP or invented source IDs', () => {
  const guided = compile();
  assert.ok(guided.steps.every(s=>!('xp' in s) && !('mastery' in s)));
  const original = new Set(manifest.lessons.flatMap(l=>l.items.map(x=>x.id)));
  assert.ok(guided.steps.flatMap(s=>s.items).every(x=>original.has(x.id)));
});

test('modified original Polish or audio must fail closed', () => {
  const changed=clone(manifest);
  changed.lessons.find(l=>l.id==='Conversation_1').items[14].polish='DRAFT';
  assert.throws(()=>compile(changed),/uncertified or changed recorded source/);
  const modified=clone(manifest);
  modified.lessons.find(l=>l.id==='Conversation_1').items[14].audio=undefined;
  assert.throws(()=>compile(modified),/uncertified or changed recorded source/);
  const restricted=clone(manifest);
  restricted.lessons.find(l=>l.id==='Conversation_1').items[14].referenceReview='practice_only';
  assert.throws(()=>compile(restricted),/uncertified or changed recorded source/);
});

test('forward grammar prerequisites and missing source groups must fail closed', () => {
  const broken=clone(sources);
  broken.prerequisites.steps[1].requires=['how-much'];
  assert.throws(()=>compile(manifest,broken),/prerequisite/);
  const removed=clone(sources);
  removed.grammar.groups.pop();
  assert.throws(()=>compile(manifest,removed),/inventory/);
});

test('grammatical cue source corruption cannot fabricate an example', () => {
  const bad=clone(sources);
  bad.grammar.groups[0].examples[0].focus='not in source';
  assert.throws(()=>compile(manifest,bad),/ambiguous authored grammar focus/);
  const badTranslation=clone(sources);
  badTranslation.next.groups[0].itemRefs[0].expectedEnglish='New translation';
  assert.throws(()=>compile(manifest,badTranslation),/uncertified or changed recorded source/);
  const status=clone(sources);
  status.grammar.status='approved';
  assert.throws(()=>compile(manifest,status),/editorial source status/);
});
