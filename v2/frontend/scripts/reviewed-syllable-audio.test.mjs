import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {attachReviewedSyllableAudio} from './reviewed-syllable-audio.mjs';

const bytes=Buffer.alloc(4096,23);
const hash=createHash('sha256').update(bytes).digest('hex');
const reference='generated/audio/Road_Terminology/0.mp3';
const base=()=>[{id:'Road_Terminology',source:'legacy',kind:'vocabulary',items:[
 {id:'Road_Terminology:0',polish:'ulica',english:'Street',audio:reference,
  pronunciationSegments:{method:'editorial-draft-v1',segments:['u','li','ca']}},
 {id:'Road_Terminology:1',polish:'aleja',english:'Avenue',audio:'generated/audio/Road_Terminology/1.mp3'}]}];
const sample=()=>({schemaVersion:1,
 status:'independent_review_documented_external_evidence_required',
 notes:'Synthetically exercised release-validation contract; no real Polish or audio certified',
 items:[{
  itemId:'Road_Terminology:0',polish:'ulica',audio:reference,audioSha256:hash,durationMs:1200,
  segments:[{polish:'u',startMs:0,endMs:360},{polish:'li',startMs:360,endMs:700},
            {polish:'ca',startMs:700,endMs:1200}],
  evidence:{
   nativeSyllabificationReview:'review:polish-syllable-0001',
   audioBoundaryReview:'review:audio-boundary-0002',
   voiceRightsReview:'review:source-rights-0003',
   releaseAuthorization:'release:owner-approval-0004'
  }
 }]});
const verify={readAudio:()=>bytes,probeDuration:()=>1200};
const clone=x=>structuredClone(x);
test('blocked manifest ships zero syllable audio without claiming any approved recordings',()=>{
 const lessons=base();
 const report=attachReviewedSyllableAudio(lessons,{
  schemaVersion:1,status:'blocked_pending_independent_native_syllable_and_acoustic_timing_review',
  notes:'No real syllable audio evidence',items:[]});
 assert.deepEqual(report,{reviewedItems:0,reviewedSegments:0,awaitingNativeAcousticReview:true});
 assert.equal(lessons[0].items[0].syllableAudio,undefined);
});
test('source-confirmed future excerpt data is copied atomically and no source content changes',()=>{
 const lessons=base(),original=clone(lessons);
 const outcome=attachReviewedSyllableAudio(lessons,sample(),verify);
 assert.deepEqual(outcome,{reviewedItems:1,reviewedSegments:3,awaitingNativeAcousticReview:false});
 assert.deepEqual(lessons[0].items[0].syllableAudio.segments.map(x=>x.polish),['u','li','ca']);
 assert.equal(lessons[0].items[0].syllableAudio.sourceSha256,hash);
 assert.deepEqual(lessons[0].items[1],original[0].items[1]);
 assert.equal(lessons[0].items[0].audio,reference);
 assert.equal(lessons[0].items[0].pronunciationSegments.method,'editorial-draft-v1');
});
test('block any attempt to sneak source audio timings into the empty production contract',()=>{
 const value=sample();value.status='blocked_pending_independent_native_syllable_and_acoustic_timing_review';
 assert.throws(()=>attachReviewedSyllableAudio(base(),value),/blocked manifest contains/);
});
test('guard against unmatched source text/voice, right-to-use, reviewed timing and hash',()=>{
 const mutations=[
  item=>item.polish='Wrong',
  item=>item.audio='https://untrusted.example/a.mp3',
  item=>item.audioSha256='0'.repeat(64),
  item=>item.evidence.audioBoundaryReview='',
  item=>item.evidence.voiceRightsReview='',
  item=>item.evidence.nativeSyllabificationReview='',
  item=>item.evidence.releaseAuthorization='',
  item=>item.segments[0].polish='foo',
  item=>item.segments[1].startMs=200,
  item=>item.segments[1].startMs=800,
  item=>item.segments[2].endMs=680,
  item=>item.segments[2].endMs=1600,
  item=>item.segments[2].endMs=849, // 351 ms unaccounted tail exceeds 350 ms limit
  item=>item.segments[0].startMs=410,
 ];
 for(const mutate of mutations){
  const plan=sample(),lessons=base();mutate(plan.items[0]);
  assert.throws(()=>attachReviewedSyllableAudio(lessons,plan,verify));
  assert.equal(lessons[0].items[0].syllableAudio,undefined);
 }
 assert.throws(()=>attachReviewedSyllableAudio(base(),sample(),
  {...verify,readAudio:()=>Buffer.alloc(4096,8)}),/hash mismatch/);
 assert.throws(()=>attachReviewedSyllableAudio(base(),sample(),
  {...verify,probeDuration:()=>1850}),/duration not independently verified/);
 assert.throws(()=>attachReviewedSyllableAudio(base(),sample(),{}),/missing audio verifier/);
});
test('one bad final item cannot partially publish earlier approved syllable excerpts',()=>{
 const plan=sample();plan.items.push({...clone(plan.items[0]),itemId:'Road_Terminology:1',polish:'aleja'});
 const lessons=base();
 assert.throws(()=>attachReviewedSyllableAudio(lessons,plan,verify));
 assert.equal(lessons[0].items[0].syllableAudio,undefined);
});
