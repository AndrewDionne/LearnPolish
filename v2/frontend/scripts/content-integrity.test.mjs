import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildContent} from './prepare-content.mjs';
import {auditContentIntegrity} from './content-integrity.mjs';

const project=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
let fixture;
function built(){
  if(!fixture){
    buildContent();
    fixture=JSON.parse(fs.readFileSync(path.join(project,'public/generated/lessons.json'),'utf8')).lessons;
  }
  return structuredClone(fixture);
}
function mutate(id,fn){
  const lessons=built();
  const item=lessons.find(x=>x.id===id);
  assert.ok(item,'expected lesson '+id);
  fn(item);
  return lessons;
}

test('DPT-05: all 26 lessons and 482 items map to unedited source and MP3 bytes',()=>{
  const report=auditContentIntegrity({lessons:built()});
  assert.deepEqual(report,{
    lessons:26,items:482,
    stages:{fundamentals:12,basic:7,learning:6,practice:1},
    sourceLessons:20,originalAudioCopies:455,curatedSoundLessons:5,
    curatedAudioReferences:26,practiceOnlyReferences:14,
    unrecordedDiagnosticItems:1,
    status:'source_mapping_and_bytes_verified_not_native_speaker_approved',
  });
  console.log('DPT05_SOURCE_INTEGRITY '+JSON.stringify(report));
});

test('DPT-05 rejects editorial title changes and non-contiguous course orders',()=>{
  assert.throws(()=>auditContentIntegrity({lessons:mutate('Conversation_1',lesson=>{
    lesson.title='Surprise renamed lesson';
  })}),/editorial mismatch/);
  assert.throws(()=>auditContentIntegrity({lessons:mutate('Conversation_1',lesson=>{
    lesson.curriculum.order=4;
  })}),/editorial mismatch/);
});

test('DPT-05 rejects changed original Polish/English and stable IDs',()=>{
  for(const [field,value] of [['polish','Dzień inny'],['english','Different meaning'],['id','Conversation_1:surprise']]){
    assert.throws(()=>auditContentIntegrity({lessons:mutate('Conversation_1',lesson=>{
      lesson.items[0][field]=value;
    })}),/original Polish\/English\/ID drift|item inventory changed/);
  }
});

test('DPT-05 rejects curated sound and protected reference drift',()=>{
  assert.throws(()=>auditContentIntegrity({lessons:mutate('contrast_c_cz_cie',lesson=>{
    lesson.items[0].audio='generated/audio/a-different-lesson/0.mp3';
  })}),/curated source\/audio mapping drift/);
  assert.throws(()=>auditContentIntegrity({lessons:mutate('Conversation_1',lesson=>{
    lesson.items[24].referenceReview=undefined;
  })}),/unexpected scored\/practice-only source/);
  assert.throws(()=>auditContentIntegrity({lessons:mutate('speak_swietokrzyska',lesson=>{
    lesson.items[0].audio='generated/audio/fake/0.mp3';
  })}),/unverified diagnostic lab/);
});

test('DPT-05 detects source MP3 mutation, even when paths and UI metadata match',()=>{
  assert.throws(()=>auditContentIntegrity({
    lessons:built(),
    assetBytes:file=>file.includes(path.join('docs','static'))
      ?Buffer.from('tampered-original-recording'):fs.readFileSync(file),
  }),/audio bytes differ from original/);
});

test('DPT-05 rejects invented lesson, duplicate IDs and arbitrary Numbers 1–20 split',()=>{
  assert.throws(()=>auditContentIntegrity({lessons:mutate('numbers_1-20',lesson=>{
    lesson.items=lesson.items.slice(0,10);
  })}),/legacy source mapping|Numbers 1–20|item inventory changed/);
  assert.throws(()=>auditContentIntegrity({lessons:[...built(),built()[0]]}),/expected exactly 26 lessons/);
  assert.throws(()=>auditContentIntegrity({lessons:mutate('Conversation_1',lesson=>{
    lesson.items[1].id=lesson.items[0].id;
  })}),/item inventory changed|original Polish\/English\/ID drift/);
});
