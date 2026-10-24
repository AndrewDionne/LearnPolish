import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {verifyReadingContextCues,C16_READING_SCENES} from './reading-context-cues.mjs';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const BASE=JSON.parse(fs.readFileSync(
 path.join(ROOT,'v2/content/journey1-c16-reading-context-cues-v1.json'),'utf8'));
const clone=()=>structuredClone(BASE);

test('C-16A exactly maps five real complete reading sources, 45 original lines and MP3 files',()=>{
 assert.deepEqual(C16_READING_SCENES.map(x=>x[1]),[9,10,9,8,9]);
 assert.deepEqual(verifyReadingContextCues(),{scenes:5,wholeRecordedTurns:45,nativeApproved:0});
 assert.ok(BASE.lessons.every(x=>x.lines.every(line=>!line.cue.includes('native-approved'))));
});
test('C-16A fails closed on original transcription, meaning, item and draft review status drift',()=>{
 for(const [edit,signal] of [
  [(x)=>x.lessons[0].lines[0].polish='changed','source Polish drift'],
  [(x)=>x.lessons[0].lines[0].english='changed','source English drift'],
  [(x)=>x.lessons[0].lines[0].id='wrong:0','wrong original item ID'],
  [(x)=>x.lessons[0].lines[0].cue='ok','contextual instruction'],
  [(x)=>x.lessons[0].lines.pop(),'all original turns must be covered'],
  [(x)=>x.lessons.pop(),'5'],
  [(x)=>x.lessons.reverse(),'unexpected source lesson'],
  [(x)=>x.status='native_approved','source_anchored_editorial_draft'],
 ]){
  const x=clone();edit(x);
  assert.throws(()=>verifyReadingContextCues(x,{checkAudio:false}),new RegExp(signal));
 }
});
test('C-16A introduction retains short contextual instruction but no assessment, XP or artificial audio fields',()=>{
 assert.ok(BASE.notes.includes('same original MP3'));
 assert.ok(BASE.notes.includes('NOT Polish-native grammatical verification'));
 for(const scene of BASE.lessons){
  for(const line of scene.lines){
   assert.deepEqual(Object.keys(line).sort(),['cue','english','id','polish']);
   assert.ok(line.cue.length>40&&line.cue.length<360);
  }
 }
});
