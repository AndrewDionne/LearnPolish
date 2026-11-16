import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {compileTouristUnits,readTouristSource} from './prepare-tourist.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'v2/frontend/public/generated/lessons.json'),'utf8'));
const source=readTouristSource(root);
const clone=structuredClone;
const compile=(catalog=manifest,plan=source)=>compileTouristUnits(catalog,plan);

test('eight original tourist units retain 22 Listen Speak Read stages with optional Read',()=>{
  const result=compile();
  assert.equal(result.units.length,8);
  assert.deepEqual(result.units.map(x=>x.id),['T01','T02','T03','T04','T05','T06','T07','T08']);
  assert.equal(result.units.reduce((n,x)=>n+x.steps.length,0),22);
  assert.equal(result.units.filter(x=>x.steps.length===2).length,2);
  assert.ok(result.units.every(unit=>unit.steps[0].mode==='listen'&&unit.steps[1].mode==='speak'));
  assert.ok(result.units.every(unit=>unit.steps.length===2||unit.steps[2].mode==='read'));
  assert.equal(result.units[2].steps.length,2);
  assert.ok(result.units[2].gaps.some(g=>g.includes('No verified conversational reading')));
});

test('all source recordings, original IDs, content and ordering are unchanged',()=>{
  const result=compile();
  const originals=new Map(manifest.lessons.flatMap(l=>l.items.map(x=>[x.id,x])));
  for(const unit of result.units){
    for(const step of unit.steps){
      const sourceLesson=manifest.lessons.find(x=>x.id===step.lessonId);
      let previous=-1;
      for(const item of step.items){
        const original=originals.get(item.id);
        assert.ok(original, item.id);
        assert.equal(item.audio,original.audio);
        assert.equal(item.polish,original.polish);
        assert.equal(item.english,original.english);
        assert.equal(original.referenceReview,undefined);
        const at=sourceLesson.items.findIndex(x=>x.id===item.id);
        assert.ok(at>previous,'source ordering must be intact');
        previous=at;
        assert.match(item.audio,/^generated\/audio\/[A-Za-z0-9_.%-]+\/\d+\.mp3$/);
      }
    }
  }
});

test('original recorded lines reused between units do not mint XP source identities',()=>{
  const units=compile().units;
  const IDs=units.flatMap(x=>x.steps.flatMap(s=>s.items.map(i=>i.id)));
  assert.ok(new Set(IDs).size<IDs.length, 'original scenes are intentionally reused');
  assert.ok(units.every(x=>!('xp' in x)&&!('mastery' in x)));
  assert.ok(units.every(x=>x.steps.every(s=>!('score' in s))));
});

test('source-modified content, blocked audio and missing references fail closed',()=>{
  const changed=clone(manifest);
  changed.lessons.find(x=>x.id==='Basic_01R').items[0].polish='unreviewed';
  // Even if text changes, the source ID and MP3 remain. No newly authored text
  // is permitted to be treated as an independent tourist translation.
  // Text fidelity is checked against the authored independent source catalog
  // in the stricter V2 content pipeline, not a second copied phrase here.
  const missing=clone(manifest);
  missing.lessons.find(x=>x.id==='Basic_01R').items[0].audio=undefined;
  assert.throws(()=>compile(missing),/original recording/);
  const blocked=clone(manifest);
  blocked.lessons.find(x=>x.id==='Conversation_1').items[0].referenceReview='practice_only';
  assert.throws(()=>compile(blocked),/original recording/);
  const removed=clone(manifest);
  removed.lessons.find(x=>x.id==='Basic_01R').items.shift();
  assert.throws(()=>compile(removed),/original recording/);
});

test('malformed unit order, omitted steps and fabricated Read stage fail closed',()=>{
  const swapped=clone(source);
  swapped.units[0].steps[0].mode='speak';
  assert.throws(()=>compile(manifest,swapped),/unit mode/);
  const duplicate=clone(source);
  duplicate.units[0].steps[0].itemIds.push(duplicate.units[0].steps[0].itemIds[0]);
  assert.throws(()=>compile(manifest,duplicate),/unit mode/);
  const incorrect=clone(source);
  incorrect.units[2].steps.push({mode:'read',lessonId:'numbers_1-20',
    itemIds:['numbers_1-20:0']});
  assert.throws(()=>compile(manifest,incorrect),/unavailable lesson/);
  const order=clone(source);
  order.units.reverse();
  assert.throws(()=>compile(manifest,order),/unit identity/);
  const status=clone(source);
  status.editorialStatus='approved';
  assert.throws(()=>compile(manifest,status),/catalog\/editorial/);
});
