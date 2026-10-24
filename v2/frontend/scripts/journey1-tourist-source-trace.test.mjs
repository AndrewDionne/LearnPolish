import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {verifyTouristSourceTrace} from './journey1-tourist-source-trace.mjs';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const RAW=JSON.parse(fs.readFileSync(path.join(ROOT,
 'v2/content/journey1-c16c-tourist-catalogue-use-v1.json'),'utf8'));
const copy=()=>structuredClone(RAW);

test('C-16C all 8 tourist units and 22 source-backed steps have honest first mentions',()=>{
 const actual=verifyTouristSourceTrace();
 assert.deepEqual(actual,{
  touristUnits:8,stepCount:22,totalItemMentions:129,
  distinctItemsAcrossTourists:85,guidedReferencedMentions:28,
  outsideGuidedMentions:101,firstTouristManifestMentions:85,nativeApproved:0
 });
 assert.equal(RAW.units[0].id,'T01');
 assert.equal(RAW.units[7].id,'T08');
 assert.ok(RAW.units.some(x=>x.originalOpenGaps.length>0));
});
test('C-16C source drift, catalogue order and faux mastery never pass',()=>{
 for(const [edit,pattern] of [
  [(x)=>{x.units[0].id='T77';},/tourist ID\/order mismatch/],
  [(x)=>{x.units[0].steps[0].sourceItems[0].polish='changed';},/Polish source drift/],
  [(x)=>{x.units[0].steps[0].sourceItems[0].english='changed';},/English source drift/],
  [(x)=>{x.units[0].steps[0].sourceItems[0].id='Fake:0';},/tourist item source/],
  [(x)=>{x.units[0].steps[0].sourceItems[0].guidedFirstUse={unitId:'fake',stepOrder:1};},/guided first-use position/],
  [(x)=>{x.units[0].steps[0].sourceItems[0].firstTouristManifestMention=false;},/tourist catalogue first-mention/],
  [(x)=>{x.units[0].originalOpenGaps.push('invented');},/original missing dialogue gaps/],
  [(x)=>{x.units[0].steps.pop();},/2/],
  [(x)=>{x.units[0].counts.mentions=50;},/tourist item coverage/],
  [(x)=>{x.status='native-approved';},/source_provenance_and_catalogue_order_trace_only/]
 ]){
  const x=copy();edit(x);
  assert.throws(()=>verifyTouristSourceTrace(x,{checkAudio:false}),pattern);
 }
});
