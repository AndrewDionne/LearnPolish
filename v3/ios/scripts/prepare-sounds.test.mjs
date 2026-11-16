import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {compileSoundStudio,readSoundSources} from './prepare-sounds.mjs';

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const manifest=JSON.parse(fs.readFileSync(path.join(repo,'v2/frontend/public/generated/lessons.json'),'utf8'));
const sources=readSoundSources(repo);
const clone=x=>structuredClone(x);
const build=(m=manifest,s=sources)=>compileSoundStudio(m,s);

test('all Polish 32 letters, 13 combinations and 25 distinct recorded sound questions resolve',()=>{
  const result=build();
  assert.equal(result.letters.length,32);
  assert.equal(result.combinations.length,13);
  assert.equal(result.soundLessons.length,5);
  assert.equal(result.soundLessons.flatMap(x=>x.questions).length,25);
  assert.deepEqual(result.letters.slice(0,3).map(x=>x.label),['A','Ą','B']);
  assert.ok(result.soundLessons.every(x=>new Set(x.questions.map(y=>y.groupId)).size>=2));
  assert.match(result.editorialStatus,/no_isolated_letter_audio/);
});
test('all alphabet examples reuse source and actual existing MP3',()=>{
  const result=build();
  const original=new Map(manifest.lessons.flatMap(l=>l.items.map(i=>[i.id,i])));
  for(const row of [...result.letters,...result.combinations]){
    const existing=original.get(row.id);
    assert.ok(existing);
    assert.equal(row.polish,existing.polish);
    assert.equal(row.english,existing.english);
    assert.equal(row.audio,existing.audio);
    assert.equal(existing.referenceReview,undefined);
    assert.equal(row.polish.split(row.focus).length,2);
  }
});
test('no sound answers or guide cards mint new item identity, XP or scores',()=>{
  const result=build();
  const IDs=new Set(manifest.lessons.flatMap(l=>l.items.map(i=>i.id)));
  for(const row of result.soundLessons.flatMap(x=>x.questions)){
    assert.ok(IDs.has(row.id));
    assert.equal(row.audio.startsWith('generated/audio/'),true);
    assert.equal(row.focus.length>0,true);
    assert.equal('score' in row,false);
  }
});
test('altered alphabet text, original MP3 and source-only status fail closed',()=>{
  const m1=clone(manifest);
  m1.lessons.find(l=>l.id==='Transit_1').items[6].polish='DRAFT';
  assert.throws(()=>build(m1),/alphabet/);
  const m2=clone(manifest);
  m2.lessons.find(l=>l.id==='Transit_1').items[6].audio='https://external/a.mp3';
  assert.throws(()=>build(m2),/alphabet/);
  const s=clone(sources);
  s.alphabet.status='native-certified';
  assert.throws(()=>build(manifest,s),/editorial/);
});
test('altered sound focus and missing curated group fail closed',()=>{
  const m=clone(manifest);
  const plan=sources.listening.lessons[0];
  const lesson=m.lessons.find(l=>l.id===plan.lessonId);
  const item=lesson.items.find(x=>x.id===plan.questions[0].itemId);
  item.soundFocus='X';
  assert.throws(()=>build(m),/sound card/);
  const m2=clone(manifest);
  m2.lessons.find(l=>l.id===plan.lessonId).soundGroups=[];
  assert.throws(()=>build(m2),/sound lesson/);
});
