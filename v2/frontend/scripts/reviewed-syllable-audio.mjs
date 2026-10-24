import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';

/** The source of truth for release is independent acoustic/native review.
 * Metadata strings are review REFERENCES, not proof that the review happened. */
const emptyStatus='blocked_pending_independent_native_syllable_and_acoustic_timing_review';
const releaseStatus='independent_review_documented_external_evidence_required';
const method='independently-reviewed-source-excerpts-v1';
const keys=(x,k)=>x&&typeof x==='object'&&!Array.isArray(x)&&
 Object.keys(x).sort().join('|')===k.slice().sort().join('|');
const sha=b=>createHash('sha256').update(b).digest('hex');
const ref=x=>typeof x==='string'&&/^[a-zA-Z][a-zA-Z0-9_.:/#-]{11,159}$/.test(x);
const hash=x=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x);
const validText=x=>typeof x==='string'&&x.length>0&&x.normalize('NFC')===x;
const error=x=>{throw Error('Unverified syllable audio: '+x);};

/** Validate a checked proposal, never guess timing from spelling.
 * Every segment MUST be an exact substring of the original fixed utterance,
 * time ordered, within an independently probed original sound recording. */
export function attachReviewedSyllableAudio(lessons,plan,{readAudio,probeDuration}={}){
 if(!keys(plan,['schemaVersion','status','notes','items'])||plan.schemaVersion!==1||
    !validText(plan.notes)||!Array.isArray(plan.items))error('bad document');
 if(plan.status===emptyStatus){
  if(plan.items.length!==0)error('blocked manifest contains timing claims');
  return {reviewedItems:0,reviewedSegments:0,awaitingNativeAcousticReview:true};
 }
 if(plan.status!==releaseStatus||typeof readAudio!=='function'||
   typeof probeDuration!=='function'||plan.items.length>1200)
   error('unauthorized release or missing audio verifier');
 const byId=new Map(lessons.flatMap(lesson=>lesson.items.map(item=>[item.id,item])));
 const seen=new Set(),updates=[];
 for(const entry of plan.items){
  if(!keys(entry,['itemId','polish','audio','audioSha256','durationMs','segments','evidence']))
    error('unexpected entry fields');
  const item=byId.get(entry.itemId);
  if(!item||seen.has(entry.itemId)||!item.audio||!item.polish||
    item.referenceReview==='practice_only'||item.id!==entry.itemId||
    item.polish!==entry.polish||item.audio!==entry.audio||
    !hash(entry.audioSha256)||!Number.isInteger(entry.durationMs)||entry.durationMs<400||
    entry.durationMs>30000)error('source utterance mismatch '+entry.itemId);
  seen.add(item.id);
  if(!keys(entry.evidence,[
   'nativeSyllabificationReview','audioBoundaryReview','voiceRightsReview','releaseAuthorization'])||
   !Object.values(entry.evidence).every(ref))
    error('missing independent review references '+item.id);
  // This is a whole original media asset. Untrusted runtime fragments or URLs
  // cannot be supplied as a new "source" for graded phonetic clips.
  if(!/^generated\/audio\/[a-zA-Z0-9_%.-]+\/[0-9]+\.mp3$/.test(entry.audio))
    error('untrusted original audio path');
  const audioBytes=readAudio(entry.audio);
  if(!Buffer.isBuffer(audioBytes)||audioBytes.length<1024||
    sha(audioBytes)!==entry.audioSha256)error('original MP3 hash mismatch '+item.id);
  const duration=probeDuration(entry.audio);
  if(!Number.isFinite(duration)||Math.abs(duration-entry.durationMs)>40)
    error('source clip duration not independently verified '+item.id);
  if(!Array.isArray(entry.segments)||entry.segments.length<2||entry.segments.length>24)
    error('missing multiple reviewed syllable intervals '+item.id);
  let previousEnd=0;
  const segments=entry.segments.map((part,i)=>{
   if(!keys(part,['polish','startMs','endMs'])||
     !validText(part.polish)||!Number.isInteger(part.startMs)||
     !Number.isInteger(part.endMs)||part.startMs<0||
     part.endMs<=part.startMs||part.endMs>entry.durationMs||
     part.endMs-part.startMs<45||
     (i>0&&(part.startMs<previousEnd||part.startMs-previousEnd>350))||
     (i===0&&part.startMs>350))
     error('unverified or overlapping audio boundary '+item.id);
   previousEnd=part.endMs;
   return {polish:part.polish,startMs:part.startMs,endMs:part.endMs};
  });
  if(entry.durationMs-previousEnd>350||segments.map(x=>x.polish).join('')!==item.polish)
    error('unaligned original syllable text/audio '+item.id);
  updates.push({item,syllableAudio:{method,audio:item.audio,
   sourceSha256:entry.audioSha256,durationMs:entry.durationMs,segments}});
 }
 // Atomic on validation failure: no earlier item is modified.
 for(const {item,syllableAudio} of updates)item.syllableAudio=syllableAudio;
 return {reviewedItems:updates.length,
   reviewedSegments:updates.reduce((n,x)=>n+x.syllableAudio.segments.length,0),
   awaitingNativeAcousticReview:false};
}

/** Browser/server only receives approved timing data in lesson JSON.
 * The production manifest is intentionally ZERO until external human evidence
 * is available; no generated syllable samples or inferred word timings. */
export function attachManifestSyllableAudio(lessons,manifest,publicDir,{probeDuration}={}){
 return attachReviewedSyllableAudio(lessons,manifest,{
   readAudio:relative=>{
    if(!/^generated\/audio\/[a-zA-Z0-9_%.-]+\/[0-9]+\.mp3$/.test(relative))error('invalid original path');
    const actual=path.resolve(publicDir,relative);
    if(!actual.startsWith(path.resolve(publicDir)+path.sep))error('path escape');
    return fs.readFileSync(actual);
   },
   probeDuration:probeDuration??(()=>NaN)
 });
}
