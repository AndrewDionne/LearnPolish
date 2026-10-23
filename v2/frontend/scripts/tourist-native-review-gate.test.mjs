import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {checkNativeReviewQueue,validateNativeReviewQueue,validateT09Candidate}
  from './tourist-native-review-gate.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const read=p=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const clone=x=>structuredClone(x);
const originalQueue=read('v2/content/tourist-native-review-queue-v1.json');
const originalT09=read('v2/content/tourist-t09-accommodation-draft-v1.json');
const originalUnits=read('v2/content/tourist-units-v1.json');
const validate=(q=originalQueue,d=originalT09,u=originalUnits,options)=>
  validateNativeReviewQueue(q,d,u,options);

test('T02–T09 are a durable eight-item native-review backlog; no ninth live tourist unit',()=>{
  assert.deepEqual(checkNativeReviewQueue(),{
    reviewItems:8,pendingItems:8,approvedItems:0,candidateTurns:16,
    publishedUnits:8,t09Live:false,recordedDraftAudio:0
  });
  assert.deepEqual(originalQueue.scope,Array.from({length:8},(_,i)=>'T'+String(i+2).padStart(2,'0')));
  assert.deepEqual(originalQueue.workItems.map(x=>x.issue),[126,126,129,129,132,134,136,137]);
  assert.equal(originalUnits.units.length,8);
  assert.equal(originalUnits.units.some(x=>x.id==='T09'),false);
  assert.equal(originalT09.review.nativeTextApproved,false);
  assert.equal(originalT09.candidateTurns.every(x=>x.audio===null),true);
});

test('no native-signoff, approval, scope change or quiet removal of unresolved issue can pass',()=>{
  for(const mutate of [
    q=>{q.published=true;},
    q=>{q.status='native_approved';},
    q=>{q.scope.push('T10');},
    q=>{q.workItems.pop();},
    q=>{q.workItems[0].approvedText=true;},
    q=>{q.workItems[1].approvedAudio=true;},
    q=>{q.workItems[3].issue=126;},
    q=>{q.workItems[7].sourceState='existing_source_only';},
    q=>{q.workItems[5].deliverables=[];},
    q=>{q.workItems[0].nativeReviewer='fictional';},
  ]){
    const bad=clone(originalQueue);mutate(bad);
    assert.throws(()=>validate(bad),/Native review draft gate|Unexpected/);
  }
});

test('cannot accidentally make the hotel scene available as a source lesson',()=>{
  const live=clone(originalUnits);
  live.units.push({id:'T09',title:'Hotel',order:9,journey:1,steps:[]});
  assert.throws(()=>validate(originalQueue,originalT09,live),/T09 must never/);
  const replaced=clone(originalUnits);
  replaced.units[7].id='T09';
  assert.throws(()=>validate(originalQueue,originalT09,replaced),/T09 must never/);
  assert.throws(()=>validate(originalQueue,originalT09,originalUnits,{
    runtimeReferences:["import hotel from '../../content/tourist-t09-accommodation-draft-v1.json';"]
  }),/editorial files referenced/);
  assert.throws(()=>validate(originalQueue,originalT09,originalUnits,{
    runtimeReferences:["tourist-native-review-queue-v1"]
  }),/editorial files referenced/);
});

test('fictional hotel text must remain unapproved and unrecorded with fixed 16 canonical draft IDs',()=>{
  const base=clone(originalT09);
  assert.equal(validateT09Candidate(base),true);
  for(const mutate of [
    d=>{d.published=true;},
    d=>{d.sourceStatus='existing_recorded_and_approved';},
    d=>{d.status='native_approved';},
    d=>{d.review.nativeTextApproved=true;},
    d=>{d.review.audioMatchedAndApproved=true;},
    d=>{d.candidateTurns[0].audio='generated/audio/T09/0.mp3';},
    d=>{d.candidateTurns[0].approved=true;},
    d=>{d.candidateTurns[2].draftId='T09:2';},
    d=>{d.candidateTurns[2].speaker='receptionist';},
    d=>{d.candidateTurns[7].english=' ';},
    d=>{d.candidateTurns.pop();},
    d=>{d.recordingPlan.voiceApproval='approved';},
    d=>{d.recordingPlan.expectedRecordings=15;},
    d=>{d.recordingPlan.audioAcceptance=[];},
    d=>{d.requiredReadArtifact=[];},
    d=>{d.fictionalContext='real Warsaw hotel';},
  ]){
    const bad=clone(base);mutate(bad);
    assert.throws(()=>validateT09Candidate(bad),/Native review draft gate|Unexpected/);
  }
});

test('separate editorial queue does not modify B-03 source anchors or T01–T08 built-in source units',()=>{
  const existing=read('v2/content/tourist-editorial-review-v1.json');
  assert.deepEqual(existing.scope,['T02','T03']);
  assert.equal(existing.published,false);
  assert.equal(existing.workItems[0].sourceAnchors[2].itemId,'Conversation_1:25');
  assert.equal(originalUnits.units[7].steps[0].lessonId,'Museum_buying_tickets_and_basic_info');
  assert.equal(originalUnits.units[7].steps[1].lessonId,'Getting_Around_1');
});
