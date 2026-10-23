import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateDialogueDrafts,renderReviewSheet,checkDialogueDrafts}
  from './tourist-dialogue-review-gate.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const read=p=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const draft=read('v2/content/tourist-t02-t05-dialogue-drafts-v1.json');
const manifest=read('v2/content/tourist-units-v1.json');
const queue=read('v2/content/tourist-native-review-queue-v1.json');
const blockers=read('v2/content/additional-speak-reference-blockers.json');
const protectedIds=new Set(['Conversation_1:24','Conversation_1:25',
  ...blockers.sourceBlockers.map(x=>x.itemId)]);
const sourceIds=['Basic_01R','Conversation_1','Conversation_-_shopping',
  'Conversation_-_restaurant','Grocery_store_very_basic_shopping'];
const sources=Object.fromEntries(sourceIds.map(id=>[id,read('docs/sets/'+id+'.json')]));
const clone=x=>structuredClone(x);
const run=(d=draft,m=manifest,q=queue,opts={})=>
  validateDialogueDrafts(d,m,q,sources,protectedIds,opts);

test('T02–T05 packet strictly separates 36 provisional turns and four Read drafts from eight real source-only units',()=>{
  const expected={draftUnits:4,candidateTurns:36,readDrafts:4,originalAnchors:13,
    approvedText:0,approvedAudio:0,attachedAudio:0,liveTouristUnits:8};
  assert.deepEqual(checkDialogueDrafts().report,expected);
  assert.deepEqual(run(),expected);
  assert.deepEqual(draft.units.map(u=>u.unitId),['T02','T03','T04','T05']);
  assert.deepEqual(draft.units.map(u=>u.candidateTurns.length),[8,8,10,10]);
  assert.ok(draft.units.every(u=>u.candidateTurns.every(t=>t.audio===null)));
  assert.equal(manifest.units.length,8);
  assert.deepEqual(queue.workItems.slice(0,4).map(x=>x.issue),[126,126,129,129]);
});

test('new native-review packet cannot claim approval, attach unverified audio, or smuggle runtime material',()=>{
 const mutate=[
  d=>{d.published=true;},
  d=>{d.status='native_approved';},
  d=>{d.units[0].stage='audio_approved';},
  d=>{d.units[0].review.nativePolish=true;},
  d=>{d.units[1].review.recordedAudio=true;},
  d=>{d.units[2].candidateTurns[3].audio='fake.mp3';},
  d=>{d.units[3].candidateRead.audio='fake.mp3';},
  d=>{d.units[0].candidateRead.source='verified_official_notice';},
  d=>{d.units[1].candidateRead.answer='nonsense price';},
  d=>{d.units[2].recordingAcceptance=[];},
  d=>{d.units[3].requiredLanguageReview=[];},
  d=>{d.units[1].candidateTurns.splice(3,1);},
  d=>{d.units[0].candidateTurns[1].draftId='Basic_01R:3';},
  d=>{d.units[2].candidateTurns[0].speaker='waiter';},
  d=>{d.units[0].candidateTurns[1].polish=' ';},
  d=>{d.units[1].candidateTurns[0].recordingUrl='https://example.com/fake.mp3';},
  d=>{d.units[0].review.fakeReviewer=true;},
  d=>{d.units[0].unitId='T09';},
  d=>{d.units[1].issue=999;},
  d=>{d.units[0].sourceAnchors[2].reviewUse='source_context';},
  d=>{d.units[1].sourceAnchors[0].itemId='Conversation_-_shopping:999';},
  d=>{d.units[2].sourceAnchors.pop();},
 ];
 for(const mutator of mutate){
  const copy=clone(draft);mutator(copy);
  assert.throws(()=>run(copy),/reviewer gate/,mutator.toString());
 }
 assert.throws(()=>run(draft,manifest,queue,{
  runtimeReferences:["import unreviewed from '../../content/tourist-t02-t05-dialogue-drafts-v1.json';"]
 }),/learner runtime/);
 const live=clone(manifest);live.units.push({id:'T09',order:9,journey:1,steps:[]});
 assert.throws(()=>run(draft,live),/unexpected live tourist units/);
 const alteredQueue=clone(queue);alteredQueue.workItems[0].approvedAudio=true;
 assert.throws(()=>run(draft,manifest,alteredQueue),/native issue, approval/);
});

test('original source anchors remain pinned to actual original data, protected speech cannot be laundered',()=>{
 const copies=clone(sources);
 copies.Basic_01R.passages[2].polish='';
 assert.throws(()=>validateDialogueDrafts(draft,manifest,queue,copies,protectedIds),
   /original source anchor not found/);
 const altered=new Set(protectedIds);altered.delete('Conversation_1:25');
 assert.throws(()=>validateDialogueDrafts(draft,manifest,queue,sources,altered),
   /protected source laundering/);
 assert.ok(draft.units[0].sourceAnchors.some(a=>a.itemId==='Conversation_1:25'&&
  a.reviewUse==='protected_source_reference'));
});

test('native reviewer can obtain a readable offline review sheet with fixed Polish, English and explicit missing recordings',()=>{
 const sheet=renderReviewSheet(draft);
 for(const name of ['T02','T03','T04','T05'])assert.ok(sheet.includes('## '+name));
 assert.ok(sheet.includes('36')===false || sheet.includes('UNAPPROVED'));
 assert.match(sheet,/UNAPPROVED DRAFT/);
 assert.match(sheet,/Mam na imię Ola/);
 assert.match(sheet,/Razem osiem złotych/);
 assert.match(sheet,/Poproszę zupę pomidorową i wodę/);
 assert.match(sheet,/kilogram czerwonych jabłek/);
 assert.match(sheet,/0\/8 submitted/);
 assert.match(sheet,/0\/10 submitted/);
 assert.match(sheet,/No native\/acoustic approvals/);
 assert.ok(!sheet.includes('audio approved'));
});
