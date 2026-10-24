import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {verifyItemAudit} from './journey1-item-audit.mjs';
import {verifyGuidedChronology} from './journey1-guided-chronology.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const data=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),'utf8'));
const reportFile='v2/content/journey1-c16c-tourist-catalogue-use-v1.json';
const sourceTourists='v2/content/tourist-units-v1.json';
const sourceLedger='v2/content/journey1-item-prerequisite-audit-v1.json';
const guidedFile='v2/content/journey1-c16b-chronological-source-uses-v1.json';
const numbersFile='docs/sets/numbers_1-20.json';
const sameKeys=(row,expected)=>assert.deepEqual(Object.keys(row).sort(),expected.slice().sort());
const STATUS='source_provenance_and_catalogue_order_trace_only_not_native_or_prerequisite_certification';

/** Independent exact source identity/corpus comparison for tourist catalogue
 * mentions. A prior entry in the MANIFEST does not imply that a learner
 * actually encountered the language. Protected rows never become certified. */
export function verifyTouristSourceTrace(report=data(reportFile),{checkAudio=true}={}){
 const actualItems=verifyItemAudit(undefined,{checkAudio});
 const guidedCounts=verifyGuidedChronology(undefined,undefined,{checkAudio});
 assert.equal(actualItems.grammarReviewApproved,0);
 assert.equal(guidedCounts.nativeApproved,0);
 sameKeys(report,['schemaVersion','status','notes','units','counts']);
 assert.equal(report.schemaVersion,1);
 assert.equal(report.status,STATUS);
 assert.ok(report.notes.includes('NOT constitute proof'));
 const manifest=data(sourceTourists);
 assert.equal(manifest.editorialStatus,'source_refs_only_native_review_pending');
 assert.equal(manifest.units.length,8);
 const ledger=data(sourceLedger);
 const sourceRows=new Map(ledger.rows.map(row=>[row.id,row]));
 const numbers=data(numbersFile).cards;
 assert.equal(numbers.length,20);
 numbers.forEach((row,i)=>sourceRows.set('numbers_1-20:'+i,{
  id:'numbers_1-20:'+i,polish:row.phrase,english:row.meaning
 }));
 const guided=data(guidedFile);
 const firstGuided=new Map();
 for(const unit of guided.guidedOrder)for(const row of unit.recordedSourceItems){
  if(!firstGuided.has(row.id))
   firstGuided.set(row.id,{unitId:unit.unitId,stepOrder:unit.order});
 }
 assert.equal(guidedCounts.distinctGuidedSourceItems,firstGuided.size);
 assert.equal(report.units.length,8);
 const seen=new Set(),recordings=new Map();
 let steps=0,mentions=0,guidedMentions=0;
 for(const [u,sourceUnit] of manifest.units.entries()){
  const unit=report.units[u];
  sameKeys(unit,['id','title','steps','originalOpenGaps','counts']);
  assert.equal(unit.id,sourceUnit.id,'tourist ID/order mismatch');
  assert.equal(unit.title,sourceUnit.title,'tourist title drift');
  assert.deepEqual(unit.originalOpenGaps,sourceUnit.gaps??[],'original missing dialogue gaps drift');
  assert.equal(unit.steps.length,sourceUnit.steps.length);
  let local=0,withinGuided=0,withinNew=0;
  const localDistinct=new Set();
  for(const [j,sourceStep] of sourceUnit.steps.entries()){
   const step=unit.steps[j];
   sameKeys(step,['mode','sourceLesson','sourceItems']);
   assert.equal(step.mode,sourceStep.mode);
   assert.equal(step.sourceLesson,sourceStep.lessonId);
   assert.equal(step.sourceItems.length,sourceStep.itemIds.length);
   steps++;
   for(const [index,id] of sourceStep.itemIds.entries()){
    const row=step.sourceItems[index];
    sameKeys(row,['id','polish','english','guidedFirstUse','firstTouristManifestMention']);
    assert.equal(row.id,id,'tourist item source/sequence drift');
    const original=sourceRows.get(id);
    assert.ok(original,'missing audited complete source '+id);
    assert.equal(row.polish,original.polish,'Polish source drift '+id);
    assert.equal(row.english,original.english,'English source drift '+id);
    assert.deepEqual(row.guidedFirstUse,firstGuided.get(id)??null,
      'guided first-use position drift '+id);
    const isNew=!seen.has(id);
    assert.equal(row.firstTouristManifestMention,isNew,
      'tourist catalogue first-mention drift '+id);
    if(checkAudio){
     const [lesson,idx]=id.split(':');
     if(!recordings.has(lesson)){
      const folder=path.join(ROOT,'docs/static',lesson,
       ledger.readingSourceLessonIds.includes(lesson)?'reading':'audio');
      recordings.set(lesson,fs.readdirSync(folder));
     }
     assert.ok(recordings.get(lesson).some(x=>x===idx+'.mp3'||
       x.startsWith(idx+'_')&&x.endsWith('.mp3')),
       'missing exact whole source MP3 '+id);
    }
    seen.add(id);localDistinct.add(id);
    if(isNew)withinNew++;
    if(firstGuided.has(id)){withinGuided++;guidedMentions++;}
    mentions++;local++;
   }
  }
  assert.deepEqual(unit.counts,{
   mentions:local,distinctSourceItems:localDistinct.size,
   guidedReferencedMentions:withinGuided,outsideGuidedMentions:local-withinGuided,
   newInTouristManifest:withinNew
  },'tourist item coverage mismatch '+unit.id);
 }
 const actual={touristUnits:8,stepCount:steps,totalItemMentions:mentions,
  distinctItemsAcrossTourists:seen.size,guidedReferencedMentions:guidedMentions,
  outsideGuidedMentions:mentions-guidedMentions,firstTouristManifestMentions:seen.size};
 assert.deepEqual(report.counts,actual);
 return {...actual,nativeApproved:0};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 console.log('C-16C eight source-only tourist unit provenance:',JSON.stringify(verifyTouristSourceTrace()));
}
