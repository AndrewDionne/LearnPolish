import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const FILE=path.join(ROOT,'v2/content/journey1-c16-reading-context-cues-v1.json');
export const C16_READING_SCENES=[
 ['Grocery_store_very_basic_shopping',9],
 ['H_M_clothes_shop_trying_on_a_T-shirt',10],
 ['On_the_tram_talking_to_another_passenger',9],
 ['Asking_the_tram_driver_for_directions',8],
 ['Museum_buying_tickets_and_basic_info',9]
];
const exactly=(actual,expected)=>assert.deepEqual(Object.keys(actual).sort(),expected.slice().sort());

/** Source certification here means identity and MP3 existence ONLY.
 * It makes no claim about language pedagogy, correct sounds, or native signoff. */
export function verifyReadingContextCues(
 draft=JSON.parse(fs.readFileSync(FILE,'utf8')),{checkAudio=true}={}
){
 exactly(draft,['schemaVersion','status','notes','lessons']);
 assert.equal(draft.schemaVersion,1);
 assert.equal(draft.status,'source_anchored_editorial_draft_not_native_language_reviewed');
 assert.ok(draft.notes.includes('NOT Polish-native grammatical verification'));
 assert.equal(draft.lessons.length,5);
 let total=0;
 const ids=new Set();
 for(const [index,[id,count]] of C16_READING_SCENES.entries()){
  const entry=draft.lessons[index];
  exactly(entry,['lesson','lines']);
  assert.equal(entry.lesson,id,'unexpected source lesson or scene order');
  assert.equal(entry.lines.length,count,id+': all original turns must be covered');
  const source=JSON.parse(fs.readFileSync(path.join(ROOT,'docs/sets',id+'.json'),'utf8'));
  assert.equal(source.passages.length,count,id+': original source length changed');
  const recordings=checkAudio?
    new Set(fs.readdirSync(path.join(ROOT,'docs/static',id,'reading'))):new Set();
  for(let i=0;i<count;i++){
   const row=entry.lines[i],passage=source.passages[i];
   exactly(row,['id','polish','english','cue']);
   assert.equal(row.id,id+':'+i,'wrong original item ID');
   assert.ok(!ids.has(row.id),'duplicate original line');
   ids.add(row.id);
   assert.equal(row.polish,passage.polish,'source Polish drift '+row.id);
   assert.equal(row.english,passage.english,'source English drift '+row.id);
   assert.ok(typeof row.cue==='string'&&row.cue.trim().length>40 &&
     row.cue.length<360,'missing/oversized contextual instruction '+row.id);
   if(checkAudio)assert.ok(recordings.has(i+'.mp3'),
     'missing original complete Polish MP3 '+row.id);
   total++;
  }
 }
 assert.equal(total,45);
 return {scenes:5,wholeRecordedTurns:45,nativeApproved:0};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 console.log('C-16A full-source contextual Read checks:',JSON.stringify(verifyReadingContextCues()));
}
