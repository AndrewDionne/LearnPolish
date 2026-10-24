import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const AUDIT=path.join(ROOT,'v2/content/journey1-item-prerequisite-audit-v1.json');
export const BASIC=[
 'Conversation_1','Conversation_-_shopping','Conversation_-_restaurant',
 'Food_and_Dinning','Getting_Around_1','Transit_1','Emergencies_and_Health'
];
export const READING=[
 'Basic_01R','Grocery_store_very_basic_shopping',
 'H_M_clothes_shop_trying_on_a_T-shirt','On_the_tram_talking_to_another_passenger',
 'Asking_the_tram_driver_for_directions','Museum_buying_tickets_and_basic_info'
];
const HINTS=[
 ['question-form',/[?]/u],
 ['polite-address',/\b(?:pan|pani|państwo|państwa|panu)\b/iu],
 ['negation',/\bnie\b/iu],
 ['request-poprosze',/\bpoproszę\b/iu],
 ['yes-no-czy',/\bczy\b/iu],
 ['quantity-ile',/\bile\b/iu],
 ['place-gdzie',/\bgdzie\b/iu],
 ['ability-and-permission',/\b(?:mogę|możesz|można|może)\b/iu],
 ['numbers-and-quantities',/\b(?:jeden|jedna|jedno|dwa|dwie|trzy|cztery|pięć|kilogram)\b/iu],
 ['verb-or-person-form',/\b(?:mam|masz|ma|jest|są|chciałbym|chciałabym|lubi|rozumiem|mówi)\b/iu]
];
const sourcePath=id=>path.join(ROOT,'docs/sets',id+'.json');
const recordingDir=(id,kind)=>path.join(ROOT,'docs/static',id,kind==='basic'?'audio':'reading');
const exactKeys=(obj,keys)=>assert.deepEqual(Object.keys(obj).sort(),keys.slice().sort());

/** An auditable inventory of *written forms*, NOT a grammar completion detector.
 * Explicitly refuses to promote any of 223 untouched native-review rows to approved. */
export function verifyItemAudit(ledger=JSON.parse(fs.readFileSync(AUDIT,'utf8')),{checkAudio=true}={}){
 assert.equal(ledger.schemaVersion,1);
 assert.equal(ledger.status,'223_source_rows_traced_individually_linguistic_prerequisites_open');
 assert.deepEqual(ledger.basicSourceLessonIds,BASIC);
 assert.deepEqual(ledger.readingSourceLessonIds,READING);
 assert.ok(ledger.method.includes('NOT claimed to be the actual guided curriculum sequence'));
 assert.ok(ledger.method.includes('not verified grammatical classifications'));
 assert.equal(ledger.rows.length,223);
 const seenIds=new Set(),seenForms=new Set();
 const totals={basic:0,reading:0};
 let cursor=0;
 for(const [kind,ids] of [['basic',BASIC],['reading',READING]]){
  for(const id of ids){
   const source=JSON.parse(fs.readFileSync(sourcePath(id),'utf8'));
   const original=kind==='basic'?source.cards:source.passages;
   assert.ok(Array.isArray(original),id+': original records absent');
   const audioDir=recordingDir(id,kind);
   const recordings=checkAudio?fs.readdirSync(audioDir):[];
   for(const [i,item] of original.entries()){
    const row=ledger.rows[cursor++];
    const polish=(kind==='basic'?item.phrase:item.polish).trim();
    const english=(kind==='basic'?item.meaning:item.english).trim();
    exactKeys(row,['id','sourceLesson','sourceIndex','kind','polish','english',
      'existingWholeRecording','firstObservedWrittenForms','structuralReviewPrompts',
      'lexicalAndGrammarReview']);
    assert.equal(row.id,id+':'+i);
    assert.ok(!seenIds.has(row.id),'duplicate source row '+row.id);
    seenIds.add(row.id);
    assert.equal(row.sourceLesson,id);
    assert.equal(row.sourceIndex,i);
    assert.equal(row.kind,kind);
    assert.equal(row.polish,polish,'original Polish text drift '+row.id);
    assert.equal(row.english,english,'original English text drift '+row.id);
    assert.equal(row.existingWholeRecording,
      'generated/audio/'+encodeURIComponent(id)+'/'+i+'.mp3');
    if(checkAudio){
     assert.ok(recordings.some(name=>name===i+'.mp3'||name.startsWith(i+'_')&&name.endsWith('.mp3')),
       'missing exact original whole-line MP3 '+row.id);
    }
    const forms=(polish.match(/[\p{L}]+/gu)||[])
      .map(word=>word.toLocaleLowerCase('pl').normalize('NFC'));
    const first=[...new Set(forms)].filter(form=>!seenForms.has(form));
    assert.deepEqual(row.firstObservedWrittenForms,first,
      'written-form first occurrence drift '+row.id);
    forms.forEach(form=>seenForms.add(form));
    assert.deepEqual(row.structuralReviewPrompts,
      HINTS.filter(([,rx])=>rx.test(polish)).map(([name])=>name),
      'review prompt drift '+row.id);
    assert.equal(row.lexicalAndGrammarReview,'open_not_native_certified',
      'individual item was silently approved '+row.id);
    totals[kind]++;
   }
  }
 }
 assert.equal(cursor,ledger.rows.length);
 assert.deepEqual(totals,{basic:172,reading:51});
 assert.deepEqual(ledger.counts,{
  basic:172,reading:51,total:223,
  distinctObservedWordForms:seenForms.size,openReviewRows:223
 });
 return {...totals,total:cursor,firstObservedWordForms:seenForms.size,
  grammarReviewApproved:0};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 console.log('C-15 original source-by-source item prerequisite inventory:',JSON.stringify(verifyItemAudit()));
}
