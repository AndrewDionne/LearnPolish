import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {auditProductionArtifact} from './release-asset-preflight.mjs';

function fixture(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'ptp-release-'));
 const write=(relative,value)=>{
  const target=path.join(root,relative);
  fs.mkdirSync(path.dirname(target),{recursive:true});
  fs.writeFileSync(target,value);
 };
 write('index.html', '<!doctype html><div id="root"></div><script type="module" src="/assets/app.js"></script><link rel="stylesheet" href="./assets/app.css">');
 write('assets/app.js','import "./app.css";');
 write('assets/app.css','body {display:block}');
 write('sw.js','const VERSION = "test";\nconst PRECACHE = ["./","index.html","generated/lessons.json","assets/app.js","assets/app.css"];\n');
 write('generated/lessons.json',JSON.stringify({
  schemaVersion:1,lessons:[{id:'a',kind:'vocabulary',items:[
   {id:'a:0',polish:'Cześć',english:'Hello',audio:'generated/audio/a/0.mp3'},
   {id:'a:1',polish:'Tak',english:'Yes'}
  ]}]
 }));
 write('generated/audio/a/0.mp3',Buffer.alloc(500,0x7a));
 return {root,write,cleanup:()=>fs.rmSync(root,{force:true,recursive:true})};
}
test('read-only V2 release preflight validates real shell, precache, source audio and English',()=>{
 const f=fixture();
 try{
  const receipt=auditProductionArtifact(f.root,{canonical:false});
  assert.deepEqual([receipt.lessonCount,receipt.itemCount,receipt.distinctAudioFiles,
    receipt.entrypointCount,receipt.precacheCount],[1,2,1,2,5]);
  assert.equal(receipt.familyAccountSignoff,false);
  assert.equal(receipt.physicalSafariSignoff,false);
  assert.equal(receipt.pronunciationAccuracySignoff,false);
  assert.throws(()=>auditProductionArtifact(f.root),/canonical lesson or full recording inventory/);
 }finally{f.cleanup();}
});
test('release must fail if hashed JS, CSS, service worker cache or one MP3 is absent',()=>{
 const cases=[
  f=>fs.unlinkSync(path.join(f.root,'assets/app.js')),
  f=>fs.unlinkSync(path.join(f.root,'assets/app.css')),
  f=>fs.unlinkSync(path.join(f.root,'generated/audio/a/0.mp3')),
  f=>fs.unlinkSync(path.join(f.root,'sw.js')),
  f=>f.write('sw.js','const PRECACHE = ["./","index.html","generated/lessons.json","assets/app.css"];'),
  f=>f.write('index.html','<div id="root"></div><script type="module" src="/src/main.tsx"></script>'),
  f=>f.write('sw.js','const PRECACHE = ["./","index.html","generated/lessons.json","assets/app.js","assets/app.js"];'),
  f=>f.write('assets/app.js',''),
  f=>{fs.unlinkSync(path.join(f.root,'assets/app.js'));fs.symlinkSync(path.join(f.root,'sw.js'),path.join(f.root,'assets/app.js'));},
 ];
 for(const mutate of cases){
  const f=fixture();
  try{mutate(f);assert.throws(()=>auditProductionArtifact(f.root,{canonical:false}),/preflight:/);}
  finally{f.cleanup();}
 }
});
test('rejects malicious or tampered catalog: missing original meaning, duplicate ID, path escape or audio URL',()=>{
 const cases=[
  c=>{c.lessons[0].items[0].english=' ';},
  c=>{c.lessons[0].items[1].id='a:0';},
  c=>{c.lessons[0].items[0].audio='../secrets';},
  c=>{c.lessons[0].items[0].audio='https://example.com/test.mp3';},
  c=>{c.lessons[0].items[0].audio='generated/audio/a/../../secret.mp3';},
  c=>{c.lessons[0].id='';},
  c=>{c.schemaVersion=2;}
 ];
 for(const mutate of cases){
  const f=fixture();
  try{
   const c=JSON.parse(fs.readFileSync(path.join(f.root,'generated/lessons.json'),'utf8'));
   mutate(c);f.write('generated/lessons.json',JSON.stringify(c));
   assert.throws(()=>auditProductionArtifact(f.root,{canonical:false}),/preflight:/);
  }finally{f.cleanup();}
 }
});
test('read-only preflight does not touch mutable progress, environment or external services',()=>{
 const f=fixture();
 try{
  const before=fs.readFileSync(path.join(f.root,'generated/lessons.json'));
  const result=auditProductionArtifact(f.root,{canonical:false});
  assert.equal(result.status,'local_artifact_verified_not_live_or_physical');
  assert.deepEqual(fs.readFileSync(path.join(f.root,'generated/lessons.json')),before);
  assert.equal(fs.existsSync(path.join(f.root,'user-data')),false);
 }finally{f.cleanup();}
});
