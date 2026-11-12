import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {compileExposure,readExposureSources} from './prepare-exposure.mjs';

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const catalog=JSON.parse(fs.readFileSync(path.join(repo,'v2/frontend/public/generated/lessons.json'),'utf8'));
const sources=readExposureSources(repo);
const compile=(m=catalog,s=sources)=>compileExposure(m,s);
const clone=x=>structuredClone(x);

test('source-first prepares all 51 existing reading lines and seven basic Listen sources',()=>{
  const result=compile();
  assert.equal(result.reading.length,6);
  assert.equal(result.listening.length,7);
  assert.equal(result.reading.reduce((n,x)=>n+x.items.length,0),51);
  assert.ok(result.listening.reduce((n,x)=>n+x.items.length,0)<=172);
  assert.equal(result.reading[0].lessonId,'Basic_01R');
  assert.equal(result.reading[0].items.length,6);
  assert.ok(result.reading.flatMap(x=>x.items).every(x=>x.audio.startsWith('generated/audio/')));
  assert.match(result.editorialStatus,/not_native_reviewed/);
});
test('Read teaching cues remain exact original editorial drafts',()=>{
  const result=compile();
  const first=result.reading[0].items[0];
  assert.equal(first.id,'Basic_01R:0');
  assert.ok(first.teachingCue?.length>40);
  assert.equal('correctIndex' in first,false);
  assert.equal('score' in first,false);
  const originals=new Map(catalog.lessons.flatMap(l=>l.items.map(x=>[x.id,x])));
  for(const entry of [...result.reading,...result.listening]){
    for(const row of entry.items){
      assert.equal(row.polish,originals.get(row.id)?.polish);
      assert.equal(row.english,originals.get(row.id)?.english);
      assert.equal(row.audio,originals.get(row.id)?.audio);
      assert.equal(originals.get(row.id)?.referenceReview,undefined);
    }
  }
});
test('read source text or canonical MP3 drift disables source introduction',()=>{
  const changed=clone(catalog);
  changed.lessons.find(l=>l.id==='Basic_01R').items[0].polish='FAKE';
  assert.throws(()=>compile(changed),/source text\/audio drift/);
  const missing=clone(catalog);
  missing.lessons.find(l=>l.id==='Basic_01R').items[0].audio=undefined;
  assert.throws(()=>compile(missing),/source text\/audio drift/);
});
test('source audit status, counts and incomplete dialogue reject generated exposure',()=>{
  const bad=clone(sources);
  bad.audit.status='approved';
  assert.throws(()=>compile(catalog,bad),/editorial audit/);
  const removed=clone(catalog);
  removed.lessons.find(l=>l.id==='Basic_01R').items.pop();
  assert.throws(()=>compile(removed),/audit source count|read source count/);
});
test('cue drift withholds the outdated cue without rewriting original Polish',()=>{
  const altered=clone(sources);
  altered.first.lines[0].polish='OTHER';
  const result=compile(catalog,altered);
  assert.equal(result.reading[0].items[0].teachingCue,undefined);
  assert.equal(result.reading[0].items[0].polish,
    catalog.lessons.find(l=>l.id==='Basic_01R').items[0].polish);
});
