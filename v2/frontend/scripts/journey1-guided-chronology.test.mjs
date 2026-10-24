import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {verifyGuidedChronology} from './journey1-guided-chronology.mjs';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const get=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),'utf8'));
const raw=get('v2/content/journey1-c16b-chronological-source-uses-v1.json');
const notes=get('v2/content/journey1-c16b-first-sentence-cues-v1.json');
const clone=x=>structuredClone(x);

test('C-16B 172-item audit follows actual foundation first use; optional Library is never counted as taught',()=>{
 const x=verifyGuidedChronology();
 assert.deepEqual(x,{
  guidedUnits:16,guidedRecordingUses:68,distinctGuidedSourceItems:55,
  guidedBasicSourceItems:48,legacyLibraryOnlyBasicRows:124,basicSourceRows:172,
  distinctChronologicalWrittenForms:74,guidedSentenceCues:15,nativeApproved:0
 });
 assert.equal(raw.guidedOrder[0].unitId,'simple-replies');
 assert.equal(raw.guidedOrder[6].unitId,'grammar:requests');
 assert.equal(raw.guidedOrder[12].unitId,'grammar:one-two');
 assert.equal(raw.guidedOrder[13].unitId,'food-requests');
 assert.equal(raw.basicSourceRows.filter(x=>x.firstGuidedUse===null).length,124);
 assert.equal(raw.firstWrittenFormsByUnit.length,16);
});
test('C-16B refuses hidden source order changes, incorrect first exposure or fake approval',()=>{
 for(const [edit,part] of [
  [(x)=>x.guidedOrder.reverse(),'actual guided unit order'],
  [(x)=>x.guidedOrder[0].recordedSourceItems[0].polish='Nie','guided source selection drift'],
  [(x)=>x.guidedOrder[13].recordedSourceItems.pop(),'guided source selection drift'],
  [(x)=>x.basicSourceRows[0].firstGuidedUse=null,'actual guided first introduction drift'],
  [(x)=>x.basicSourceRows[0].encounterStatus='approved','recorded_source_first_guided_use'],
  [(x)=>x.basicSourceRows.pop(),'172'],
  [(x)=>x.firstWrittenFormsByUnit[0].forms[0].newlyEncounteredWrittenForms=['made-up'],'actual first guided written forms drift'],
  [(x)=>x.status='native_certified','guided_chronological_source_trace_only'],
 ]){
  const changed=clone(raw);edit(changed);
  assert.throws(()=>verifyGuidedChronology(changed,notes,{checkAudio:false}),new RegExp(part));
 }
});
test('C-16B requires 15 complete original teaching notes but cannot silently claim native review',()=>{
 for(const [edit,part] of [
  [(x)=>x.entries.pop(),'15'],
  [(x)=>x.entries[0].id='fake:0','wrong guided sentence teaching item'],
  [(x)=>x.entries[0].polish='changed','teaching Polish source drift'],
  [(x)=>x.entries[0].english='changed','teaching English source drift'],
  [(x)=>x.entries[0].cue='Too short','draft teaching cue'],
  [(x)=>x.status='native_approved','source_anchored_draft'],
 ]){
  const changed=clone(notes);edit(changed);
  assert.throws(()=>verifyGuidedChronology(raw,changed,{checkAudio:false}),new RegExp(part));
 }
});
