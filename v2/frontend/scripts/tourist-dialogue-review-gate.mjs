/**
 * B-09: author drafts for human review only, never pronunciation references.
 * Runtime imports, voice claims, synthetic recordings and changed original IDs
 * fail closed; this module has no network, audio or file-writing paths.
 */
import {readFileSync,readdirSync} from 'node:fs';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const get=p=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const ids=['T02','T03','T04','T05'];
const expectedIssues=[126,126,129,129];
const expectedCounts=[8,8,10,10];
const expectedAnchors=[3,3,3,4];
const labels=[['Marek','Ola'],['customer','cashier'],['guest','waiter'],['shopper','seller']];
const isObj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const validText=x=>typeof x==='string'&&x.trim().length>=4;
const strict=(x,names,label)=>{
 if(!isObj(x)||Object.keys(x).sort().join('|')!==[...names].sort().join('|'))
  throw Error('B-09 reviewer gate: unexpected '+label+' fields');
};
const error=m=>{throw Error('B-09 reviewer gate: '+m);};
const turnFields=['draftId','speaker','polish','english','audio'];
const reviewerFields=['nativePolish','englishMeaning','readingComprehension','speakerRights',
  'recordedAudio','acousticListening'];
const scrub=s=>String(s).replaceAll('|','\\|').replaceAll('\n',' ');

export function validateDialogueDrafts(draft,manifest,queue,legacySources,protectedIds,{runtimeReferences=[]}={}){
 strict(draft,['schemaVersion','status','published','purpose','sourceState','units'],'draft packet');
 if(draft.schemaVersion!==1||draft.status!=='provisional_author_drafts_require_native_review'||
    draft.published!==false||!validText(draft.purpose)||
    draft.sourceState!=='original_26_legacy_lessons_unmodified;_drafts_have_no_audio'||
    !Array.isArray(draft.units)||draft.units.length!==4)
    error('draft may never become a live lesson, audio asset or approved language source');
 if(!isObj(manifest)||manifest.editorialStatus!=='source_refs_only_native_review_pending'||
    !Array.isArray(manifest.units)||manifest.units.length!==8||
    manifest.units.some((u,i)=>u.id!=='T0'+(i+1)||u.order!==i+1))
    error('unexpected live tourist units');
 if(!isObj(queue)||queue.published!==false||
    !Array.isArray(queue.workItems)||queue.workItems.length!==8)
    error('missing original pending native review queue');
 for(let i=0;i<ids.length;i++){
    const unit=draft.units[i],id=ids[i];
    strict(unit,['unitId','issue','stage','fictionalContext','sourceAnchors','speakerRoles',
      'candidateTurns','candidateRead','requiredLanguageReview','recordingAcceptance','review'],'unit');
    const item=queue.workItems[i];
    if(unit.unitId!==id||unit.issue!==expectedIssues[i]||
       item?.unitId!==id||item?.issue!==unit.issue||item?.approvedText!==false||
       item?.approvedAudio!==false||unit.stage!=='not_native_or_audio_approved'||
       !validText(unit.fictionalContext)||!Array.isArray(unit.speakerRoles)||
       JSON.stringify(unit.speakerRoles)!==JSON.stringify(labels[i]))
       error('native issue, approval, speaker or unit drift '+id);
    if(!Array.isArray(unit.sourceAnchors)||unit.sourceAnchors.length!==expectedAnchors[i]||
       new Set(unit.sourceAnchors.map(a=>a?.itemId)).size!==expectedAnchors[i])
       error('missing or duplicate original source anchors '+id);
    for(const anchor of unit.sourceAnchors){
       strict(anchor,['itemId','reviewUse'],'source anchor');
       if(!/^[a-zA-Z0-9_-]+:\\d+$/.test(anchor.itemId))error('invalid original source item ID');
       const split=anchor.itemId.lastIndexOf(':');
       const name=anchor.itemId.slice(0,split),index=Number(anchor.itemId.slice(split+1));
       const source=legacySources[name];
       const original=source&&(source.cards||source.passages)?.[index];
       if(!original||!validText(original.phrase??original.polish)||
          !validText(original.meaning??original.english))
          error('original source anchor not found '+anchor.itemId);
       const usage=protectedIds.has(anchor.itemId)?'protected_source_reference':'source_context';
       if(anchor.reviewUse!==usage)error('protected source laundering '+anchor.itemId);
    }
    if(id==='T02'&&
      !unit.sourceAnchors.some(a=>a.itemId==='Conversation_1:25'&&
        a.reviewUse==='protected_source_reference'))
      error('T02 unfinished reference must remain protected');
    if(!Array.isArray(unit.candidateTurns)||unit.candidateTurns.length!==expectedCounts[i])
      error('incorrect number of provisional turns '+id);
    unit.candidateTurns.forEach((t,j)=>{
       strict(t,turnFields,'draft turn');
       if(t.draftId!==id+'-D'+String(j+1).padStart(2,'0')||
          t.speaker!==labels[i][j%2]||!validText(t.polish)||
          !validText(t.english)||t.audio!==null||
          /(?:\\.mp3|https?:\\/\\/|generated\\/)/i.test(t.polish+' '+t.english))
          error('candidate turn is no longer an unrecorded fixed draft '+id+':'+j);
    });
    strict(unit.candidateRead,['polish','english','question','answer','source','audio'],'Read');
    const read=unit.candidateRead;
    if(read.source!=='fictional_unapproved_author_draft'||read.audio!==null||
       ![read.polish,read.english,read.question,read.answer].every(validText)||
       !read.polish.toLowerCase().includes(read.answer.toLowerCase()))
       error('provisional written Read must have traceable answer and no audio '+id);
    if(!Array.isArray(unit.requiredLanguageReview)||
       unit.requiredLanguageReview.length<3||
       unit.requiredLanguageReview.some(v=>!validText(v)||v.length<30))
       error('missing language reviewer prompts '+id);
    if(!Array.isArray(unit.recordingAcceptance)||unit.recordingAcceptance.length<4||
       unit.recordingAcceptance.some(v=>!validText(v)||v.length<35))
       error('missing separate native/audio review requirements '+id);
    strict(unit.review,reviewerFields,'review approvals');
    if(Object.values(unit.review).some(v=>v!==false))
       error('a draft is not a native or audio approval '+id);
 }
 if(runtimeReferences.some(s=>s.includes('tourist-t02-t05-dialogue-drafts-v1')))
    error('learner runtime imports private provisional Polish drafts');
 return {draftUnits:4,candidateTurns:36,readDrafts:4,originalAnchors:13,
    approvedText:0,approvedAudio:0,attachedAudio:0,liveTouristUnits:8};
}

export function renderReviewSheet(draft){
 const lines=[
 '# T02–T05 Polish native/editorial review sheet — UNAPPROVED DRAFT',
 '',
 'Provisional fictional language, NOT lesson audio or an official translation.',
 'Native Polish and English review, two-speaker licensing, acoustic checks and real recordings are required before production.',
 ''
 ];
 for(const u of draft.units){
    lines.push('## '+u.unitId+' — '+u.fictionalContext,
       '',
       'Issue: #'+u.issue+' · Original source anchors: '+u.sourceAnchors.map(x=>x.itemId).join(', '),
       '',
       '| Draft ID | Speaker | Candidate Polish (requires review) | Candidate English (requires review) |',
       '|---|---|---|---|');
    for(const t of u.candidateTurns)
       lines.push('| '+scrub(t.draftId)+' | '+scrub(t.speaker)+' | '+scrub(t.polish)+' | '+scrub(t.english)+' |');
    lines.push('','**Fictional written Read draft:** '+u.candidateRead.polish,
      '',
      '**Provisional question:** '+u.candidateRead.question,
      '',
      '**Candidate answer (must be checked):** '+u.candidateRead.answer,
      '',
      '**Review decisions needed:**');
    u.requiredLanguageReview.forEach((x,j)=>lines.push((j+1)+'. '+x));
    lines.push('','**Recording:** 0/'+u.candidateTurns.length+
      ' submitted. No native/acoustic approvals and no audio generated.','');
 }
 return lines.join('\n');
}

export function checkDialogueDrafts(){
 const draft=get('v2/content/tourist-t02-t05-dialogue-drafts-v1.json');
 const manifest=get('v2/content/tourist-units-v1.json');
 const queue=get('v2/content/tourist-native-review-queue-v1.json');
 const blockers=get('v2/content/additional-speak-reference-blockers.json');
 const protectedIds=new Set(['Conversation_1:24','Conversation_1:25',
    ...blockers.sourceBlockers.map(x=>x.itemId)]);
 const sources={};
 for(const u of draft.units)for(const a of u.sourceAnchors){
    const name=a.itemId.slice(0,a.itemId.lastIndexOf(':'));
    if(!Object.hasOwn(sources,name))sources[name]=get('docs/sets/'+name+'.json');
 }
 const src=resolve(root,'v2/frontend/src');
 const list=dir=>readdirSync(dir,{withFileTypes:true}).flatMap(entry=>
   entry.isDirectory()?list(join(dir,entry.name)):
   /\\.(ts|tsx|js|jsx)$/.test(entry.name)?
      [readFileSync(join(dir,entry.name),'utf8')]:[]);
 const report=validateDialogueDrafts(draft,manifest,queue,sources,protectedIds,
   {runtimeReferences:list(src)});
 return {report,draft};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 const {report,draft}=checkDialogueDrafts();
 if(process.argv.includes('--review-sheet'))process.stdout.write(renderReviewSheet(draft)+'\n');
 else process.stdout.write('B-09 T02–T05 unapproved dialogue review gate PASS: '+
   JSON.stringify(report)+'\n');
}
