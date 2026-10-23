/**
 * B-08 human-editorial work is NOT learner data.
 * This gate is intentionally fail-closed: future approval/release needs a
 * separately reviewed source/audio integration PR, not editing an "approved"
 * boolean or adding a ninth tourist unit.
 */
import {readFileSync,readdirSync} from 'node:fs';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const read=p=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const record=x=>!!x&&typeof x==='object'&&!Array.isArray(x);
const keys=(x,expected,label)=>{
  if(!record(x)||Object.keys(x).sort().join('|')!==[...expected].sort().join('|'))
    throw Error('Unexpected '+label+' fields');
};
const text=x=>typeof x==='string'&&x.trim().length>0;
const fail=m=>{throw Error('Native review draft gate: '+m);};
const units=['T02','T03','T04','T05','T06','T07','T08','T09'];
const issueByUnit={T02:126,T03:126,T04:129,T05:129,T06:132,T07:134,T08:136,T09:137};
const sourceStatus=id=>id==='T09'?'no_recorded_source':'existing_source_only';

export function validateNativeReviewQueue(queue,draft,manifest,{runtimeReferences=[]}={}){
  keys(queue,['schemaVersion','status','published','scope','workItems'],'queue');
  if(queue.schemaVersion!==1||queue.status!=='editorial_queue_unapproved_not_for_runtime'||
      queue.published!==false||JSON.stringify(queue.scope)!==JSON.stringify(units)||
      !Array.isArray(queue.workItems)||queue.workItems.length!==8)fail('review queue is not eight unapproved work items');
  for(let i=0;i<units.length;i++){
    const unit=units[i],item=queue.workItems[i];
    keys(item,['unitId','issue','sourceState','status','approvedText','approvedAudio','shortfall','deliverables'],'work item');
    if(item.unitId!==unit||item.issue!==issueByUnit[unit]||
      item.sourceState!==sourceStatus(unit)||
      item.status!=='awaiting_native_text_and_audio_review'||
      item.approvedText!==false||item.approvedAudio!==false||
      !text(item.shortfall)||!Array.isArray(item.deliverables)||
      item.deliverables.length<3||item.deliverables.some(x=>!text(x)||x.length<20))
      fail('unapproved deliverable/status drift: '+unit);
  }

  keys(manifest,['schemaVersion','editorialStatus','units'],'tourist manifest');
  if(manifest.schemaVersion!==1||
      manifest.editorialStatus!=='source_refs_only_native_review_pending'||
      !Array.isArray(manifest.units)||manifest.units.length!==8||
      manifest.units.some((item,i)=>item?.id!==('T0'+(i+1))||
        item?.order!==i+1||item?.journey!==1))
      fail('T09 must never enter the learner-facing tourist manifest');
  if(runtimeReferences.some(s=>s.includes('tourist-t09-accommodation-draft-v1')||
    s.includes('tourist-native-review-queue-v1')))
      fail('private editorial files referenced by learner runtime');
  validateT09Candidate(draft);
  return {reviewItems:8,pendingItems:8,approvedItems:0,candidateTurns:16,
    publishedUnits:8,t09Live:false,recordedDraftAudio:0};
}

export function validateT09Candidate(draft){
  keys(draft,['schemaVersion','unitId','status','published','sourceStatus','fictionalContext',
    'language','candidateTurns','recordingPlan','requiredReadArtifact','review'],'T09 draft');
  if(draft.schemaVersion!==1||draft.unitId!=='T09'||
     draft.status!=='provisional_author_draft_requires_native_review'||
     draft.published!==false||
     draft.sourceStatus!=='no_existing_source_audio_or_approved_transcript'||
     draft.language!=='pl-PL'||!text(draft.fictionalContext)||
     !/fictional|imaginary/i.test(draft.fictionalContext)||
     !Array.isArray(draft.candidateTurns)||draft.candidateTurns.length!==16)
     fail('T09 must remain an unrecorded fictional author draft');
  draft.candidateTurns.forEach((turn,i)=>{
    keys(turn,['draftId','speaker','polish','english','audio'],'T09 turn');
    const speaker=i%2===0?'guest':'receptionist';
    if(turn.draftId!=='T09-D'+String(i+1).padStart(2,'0')||turn.speaker!==speaker||
      typeof turn.polish!=='string'||turn.polish.trim().length<8||
      typeof turn.english!=='string'||turn.english.trim().length<8||
      /(?:https?:\/\/|\.mp3|generated\/)/i.test(turn.polish+' '+turn.english)||
      turn.audio!==null)
      fail('T09 author-draft role/transcript or audio drift at turn '+(i+1));
  });
  keys(draft.recordingPlan,['speakerRoles','voiceApproval','expectedRecordings',
    'fileNamingRule','audioAcceptance'],'recording plan');
  const plan=draft.recordingPlan;
  if(JSON.stringify(plan.speakerRoles)!=='["guest","receptionist"]'||
    plan.voiceApproval!=='not_reviewed_or_authorized'||plan.expectedRecordings!==16||
    !text(plan.fileNamingRule)||!Array.isArray(plan.audioAcceptance)||
    plan.audioAcceptance.length<5||plan.audioAcceptance.some(x=>!text(x)))
      fail('T09 audio plan requires two unapproved speakers and line-level QA');
  if(!Array.isArray(draft.requiredReadArtifact)||draft.requiredReadArtifact.length<3||
    draft.requiredReadArtifact.some(x=>!text(x)))
      fail('Missing native-reviewed booking notice and Read source plan');
  keys(draft.review,['nativeTextApproved','translationsApproved','speakerAndRightsApproved',
    'audioMatchedAndApproved','readApproved'],'human approval');
  if(Object.values(draft.review).some(x=>x!==false))
    fail('No T09 text/audio/Read approval can be represented by a draft');
  return true;
}

export function checkNativeReviewQueue(){
  const q=read('v2/content/tourist-native-review-queue-v1.json');
  const draft=read('v2/content/tourist-t09-accommodation-draft-v1.json');
  const manifest=read('v2/content/tourist-units-v1.json');
  const src=resolve(root,'v2/frontend/src');
  const list=dir=>readdirSync(dir,{withFileTypes:true}).flatMap(entry=>
    entry.isDirectory()?list(join(dir,entry.name)):
    /\.(ts|tsx|js|jsx)$/.test(entry.name)?[readFileSync(join(dir,entry.name),'utf8')]:[]);
  const audit=validateNativeReviewQueue(q,draft,manifest,{runtimeReferences:list(src)});
  // A plan is not a source lesson: no published original set named T09 and
  // no pre-baked replacement audio file masquerading as a real recording.
  const sourceFiles=readdirSync(resolve(root,'docs/sets'));
  if(sourceFiles.some(x=>/^(?:T09|tourist.t09|accommodation|hotel|lodging)[._-]/i.test(x)))
    fail('T09 new source detected: new integration and human review required');
  return audit;
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  process.stdout.write('B-08 native review queue DRAFT-ONLY PASS: '+
    JSON.stringify(checkNativeReviewQueue())+'\n');
}
