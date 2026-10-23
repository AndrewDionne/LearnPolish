import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {checkTouristEditorialPacket,validateTouristEditorialPacket} from './tourist-editorial-gate.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const read=(path)=>JSON.parse(readFileSync(resolve(root,path),'utf8'));
const packet=read('v2/content/tourist-editorial-review-v1.json');
const units=read('v2/content/tourist-units-v1.json');
const blocker=read('v2/content/additional-speak-reference-blockers.json');
const protectedIds=new Set(['Conversation_1:24','Conversation_1:25',...blocker.sourceBlockers.map(x=>x.itemId)]);
const sources={
  Basic_01R:read('docs/sets/Basic_01R.json'),
  Conversation_1:read('docs/sets/Conversation_1.json'),
  'Conversation_-_shopping':read('docs/sets/Conversation_-_shopping.json')
};
const clone=(value)=>JSON.parse(JSON.stringify(value));
const validate=(data=packet,manifest=units)=>validateTouristEditorialPacket(data,sources,protectedIds,manifest);

test('B-03 review packet is precisely source-referenced and strictly unpublished',()=>{
  assert.deepEqual(checkTouristEditorialPacket(),{
    workItems:2,sourceAnchors:6,approvedItems:0,livePilotUnchanged:true
  });
  assert.equal(packet.workItems[0].sourceAnchors[2].itemId,'Conversation_1:25');
  assert.equal(packet.workItems[1].sourceAnchors.length,3);
});

test('draft must never be promoted by toggling publication, adding unreviewed text/audio or status',()=>{
  for(const mutation of [
    p=>{p.published=true;},
    p=>{p.reviewStatus='approved';},
    p=>{p.workItems[0].reviewStatus='approved';},
    p=>{p.workItems[1].sourceAnchors[0].recordedAudio='generated.mp3';}
  ]){
    const copy=clone(packet);mutation(copy);
    assert.throws(()=>validate(copy));
  }
});

test('transcript mismatch, missing source or protected-status laundering fails closed',()=>{
  for(const mutation of [
    p=>{p.workItems[0].sourceAnchors[1].polish='Mam inne imię.';},
    p=>{p.workItems[1].sourceAnchors[0].english='Different translation';},
    p=>{p.workItems[0].sourceAnchors[2].expectedUse='source_context';},
    p=>{p.workItems[0].sourceAnchors[0].itemId='Basic_01R:999';},
    p=>{p.workItems[1].sourceAnchors[1].itemId=p.workItems[1].sourceAnchors[0].itemId;}
  ]){
    const copy=clone(packet);mutation(copy);
    assert.throws(()=>validate(copy));
  }
});

test('source-only T04–T06 extension cannot re-scope original B-03 review',()=>{
  assert.equal(units.units.length,6);
  assert.deepEqual(units.units.slice(0,3).map(x=>x.id),['T01','T02','T03']);
  assert.deepEqual(validate().approvedItems,0);
  const reordered=clone(units);
  [reordered.units[0],reordered.units[1]]=[reordered.units[1],reordered.units[0]];
  assert.throws(()=>validate(packet,reordered),/Tourist pilot baseline changed/);
  const wrongPosition=clone(units);
  wrongPosition.units[2].position='middle';
  assert.throws(()=>validate(packet,wrongPosition),/Tourist pilot baseline changed/);
  const differentStatus=clone(units);
  differentStatus.editorialStatus='native_approved';
  assert.throws(()=>validate(packet,differentStatus),/Tourist pilot baseline changed/);
});

test('current user-facing pilot cannot quietly add T03 reading or blocked T02 Speak',()=>{
  const bogusRead=clone(units);
  bogusRead.units[2].steps.push({mode:'read',lessonId:'Basic_01R',itemIds:['Basic_01R:3']});
  assert.throws(()=>validate(packet,bogusRead),/T03/);
  const bogusSpoken=clone(units);
  bogusSpoken.units[1].steps[1].itemIds.push('Conversation_1:25');
  assert.throws(()=>validate(packet,bogusSpoken),/T02/);
});
