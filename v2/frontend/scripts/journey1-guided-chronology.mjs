import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const read=relative=>JSON.parse(fs.readFileSync(path.join(ROOT,relative),'utf8'));
const LEDGER='v2/content/journey1-c16b-chronological-source-uses-v1.json';
const NOTES='v2/content/journey1-c16b-first-sentence-cues-v1.json';
const SOURCE_AUDIT='v2/content/journey1-item-prerequisite-audit-v1.json';
const ORDER=[
 'simple-replies','politeness','greetings','street-words','transport-words',
 'everyday-replies','grammar:requests','grammar:where','grammar:permission',
 'grammar:prices','grammar:yes-no-questions','grammar:negative','grammar:one-two',
 'food-requests','shopping-questions','location-questions'
];
const categories=['first-words','basic-vocabulary','grammar-explanation','first-sentence-practice'];
const tokens=value=>(value.match(/[\p{L}]+/gu)||[]).map(x=>x.toLocaleLowerCase('pl').normalize('NFC'));
const sameKeys=(actual,keys)=>assert.deepEqual(Object.keys(actual).sort(),keys.slice().sort());
const sourceLesson=id=>read('docs/sets/'+id+'.json');
const original=(id,cache)=>{
 const [lesson,index]=id.split(':');assert.ok(/^\d+$/.test(index),'not indexed: '+id);
 if(!cache.has(lesson))cache.set(lesson,sourceLesson(lesson));
 const c=cache.get(lesson).cards[Number(index)];
 assert.ok(c,'original source missing '+id);
 return {polish:c.phrase,english:c.meaning,audio:'generated/audio/'+encodeURIComponent(lesson)+'/'+index+'.mp3'};
};

/** Audits original whole recordings + chronological reference positions.
 * Orthographic first appearance NEVER certifies morphological or lexical knowledge. */
export function verifyGuidedChronology(
 ledger=read(LEDGER),cues=read(NOTES),{checkAudio=true}={}
){
 sameKeys(ledger,['schemaVersion','status','notes','guidedOrder','basicSourceRows',
  'firstWrittenFormsByUnit','counts']);
 assert.equal(ledger.schemaVersion,1);
 assert.equal(ledger.status,'guided_chronological_source_trace_only_not_native_lexical_or_morphology_approval');
 assert.ok(ledger.notes.includes('NOT lemmas or verified knowledge'));
 assert.equal(ledger.guidedOrder.length,16);
 assert.equal(ledger.firstWrittenFormsByUnit.length,16);
 const firstManifest=read('v2/content/foundation-first-expressions-v1.json');
 const laterManifest=read('v2/content/foundation-next-words-v1.json');
 const patterns=read('v2/content/foundation-sentence-patterns-v1.json');
 const groups=new Map([...firstManifest.groups,...laterManifest.groups].map(g=>[g.id,g]));
 const cache=new Map(),first=new Map(),all=new Map(),written=new Set(),audioCache=new Map();
 let appearances=0;
 for(const [i,step] of ledger.guidedOrder.entries()){
  sameKeys(step,['order','unitId','category','recordedSourceItems']);
  const unitId=ORDER[i];
  assert.equal(step.order,i+1);
  assert.equal(step.unitId,unitId,'actual guided unit order changed');
  assert.equal(step.category,categories[i<3?0:i<6?1:i<13?2:3]);
  const authored=unitId.startsWith('grammar:')?
    patterns.groups.find(x=>'grammar:'+x.id===unitId).examples.map(e=>({
      id:e.sourceLesson+':'+e.index,polish:e.polish,english:e.english,source:'grammar'
    })):
    groups.get(unitId).itemRefs.map(e=>({
      id:e.id,polish:e.expectedPolish,
      english:e.expectedEnglish??sourceLesson(e.id.split(':')[0]).cards[Number(e.id.split(':')[1])].meaning,
      source:'group'
    }));
  assert.deepEqual(step.recordedSourceItems,authored,'guided source selection drift '+unitId);
  const observations=[];
  for(const [j,item] of authored.entries()){
   const source=original(item.id,cache);
   assert.equal(item.polish,source.polish,'original Polish drift '+item.id);
   assert.equal(item.english,source.english,'original English drift '+item.id);
   const [lesson,index]=item.id.split(':');
   if(checkAudio){
    if(!audioCache.has(lesson))
      audioCache.set(lesson,new Set(fs.readdirSync(path.join(ROOT,'docs/static',lesson,'audio'))));
    const mp3=audioCache.get(lesson);
    assert.ok(mp3.has(index+'.mp3')||[...mp3].some(x=>x.startsWith(index+'_')&&x.endsWith('.mp3')),
      'missing source complete audio '+item.id);
   }
   if(!first.has(item.id))first.set(item.id,{unitId,stepOrder:i+1,unitItemIndex:j});
   if(!all.has(item.id))all.set(item.id,[]);
   all.get(item.id).push({unitId,stepOrder:i+1,unitItemIndex:j});
   const newWords=[...new Set(tokens(item.polish))].filter(form=>!written.has(form));
   tokens(item.polish).forEach(form=>written.add(form));
   observations.push({sourceItemId:item.id,newlyEncounteredWrittenForms:newWords});
   appearances++;
  }
  assert.deepEqual(ledger.firstWrittenFormsByUnit[i],
    {unitId,forms:observations},'actual first guided written forms drift '+unitId);
 }
 const originalBasic=read(SOURCE_AUDIT).rows.filter(row=>row.kind==='basic');
 assert.equal(originalBasic.length,172);
 assert.equal(ledger.basicSourceRows.length,172);
 let guidedBasic=0;
 for(const [index,source] of originalBasic.entries()){
  const row=ledger.basicSourceRows[index];
  sameKeys(row,['id','firstGuidedUse','allGuidedUses','encounterStatus']);
  assert.equal(row.id,source.id);
  const expectedFirst=first.get(row.id)??null,expectedAll=all.get(row.id)??[];
  assert.deepEqual(row.firstGuidedUse,expectedFirst,'actual guided first introduction drift '+row.id);
  assert.deepEqual(row.allGuidedUses,expectedAll,'source replay drift '+row.id);
  assert.equal(row.encounterStatus,expectedFirst?
   'recorded_source_first_guided_use_not_native_reviewed':
   'legacy_library_only_no_guided_instruction_claim');
  if(expectedFirst)guidedBasic++;
 }
 const result={
  guidedUnits:16,guidedRecordingUses:appearances,
  distinctGuidedSourceItems:first.size,guidedBasicSourceItems:guidedBasic,
  legacyLibraryOnlyBasicRows:172-guidedBasic,basicSourceRows:172,
  distinctChronologicalWrittenForms:written.size
 };
 assert.deepEqual(ledger.counts,result);
 sameKeys(cues,['schemaVersion','status','notes','entries']);
 assert.equal(cues.schemaVersion,1);
 assert.equal(cues.status,'source_anchored_draft_guided_sentence_teaching_not_native_certified');
 assert.equal(cues.entries.length,15);
 const guidedSentences=ledger.guidedOrder.slice(13).flatMap(x=>x.recordedSourceItems);
 assert.equal(guidedSentences.length,15);
 cues.entries.forEach((row,i)=>{
  sameKeys(row,['id','polish','english','cue']);
  assert.equal(row.id,guidedSentences[i].id,'wrong guided sentence teaching item');
  assert.equal(row.polish,guidedSentences[i].polish,'teaching Polish source drift');
  assert.equal(row.english,guidedSentences[i].english,'teaching English source drift');
  assert.ok(typeof row.cue==='string'&&row.cue.length>70&&row.cue.length<350,
    'draft teaching cue missing or excessive');
 });
 return {...result,guidedSentenceCues:15,nativeApproved:0};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))
 console.log('C-16B actual guided chronology:',JSON.stringify(verifyGuidedChronology()));
