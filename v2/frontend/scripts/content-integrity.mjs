/**
 * DPT-05: exact source and byte-provenance audit of the existing V2 library.
 * Editorial titles and metadata may be refined, but never silently rewrite
 * original Polish, translations, card IDs, source audio, or review exclusions.
 * This is a deterministic build-time audit, NOT a linguistic/audio approval.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {migrateLesson} from './prepare-content.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const sourceDir=path.join(root,'docs/sets');
const audioDir=path.join(root,'docs/static');
const publicDir=path.join(root,'v2/frontend/public');
const contentDir=path.join(root,'v2/content');
const retired=new Set(['letter_recognition_1','letter_recognition_2','letter_recognition_3']);
const load=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const fail=message=>{throw new Error('Content integrity: '+message);};
const requireMatch=(condition,message)=>{if(!condition)fail(message);};
const compare=(a,b)=>JSON.stringify(a)===JSON.stringify(b);

export function auditContentIntegrity({
  lessons=load(path.join(publicDir,'generated/lessons.json')).lessons,
  catalog=load(path.join(contentDir,'library-catalog.json')),
  sounds=load(path.join(contentDir,'sound-contrasts.json')),
  voice=load(path.join(contentDir,'voice-production.json')),
  otherBlockers=load(path.join(contentDir,'additional-speak-reference-blockers.json')),
  assetBytes=(file)=>fs.readFileSync(file),
}={}){
  requireMatch(Array.isArray(lessons)&&lessons.length===26,'expected exactly 26 lessons');
  requireMatch(Array.isArray(catalog.lessons)&&catalog.lessons.length===26,'editorial inventory is not 26');
  const byId=new Map(lessons.map(lesson=>[lesson.id,lesson]));
  const catalogById=new Map(catalog.lessons.map(lesson=>[lesson.id,lesson]));
  requireMatch(byId.size===26&&catalogById.size===26,'duplicate lesson IDs');
  requireMatch(compare([...byId.keys()].sort(),[...catalogById.keys()].sort()),'editorial/build lesson IDs differ');
  const allItems=lessons.flatMap(lesson=>lesson.items||[]);
  const ids=new Set(allItems.map(item=>item.id));
  requireMatch(allItems.length===482&&ids.size===482,'item inventory changed or IDs duplicated');
  const stages={fundamentals:0,basic:0,learning:0,practice:0};
  const tracks=new Map();
  const titles=new Set();
  for(const [id,meta] of catalogById){
    const lesson=byId.get(id);
    requireMatch(lesson?.title===meta.title&&lesson?.description===meta.description&&
      compare(lesson?.curriculum,meta.curriculum),'editorial mismatch: '+id);
    requireMatch(typeof meta.title==='string'&&meta.title.trim().length>=3&&
      !titles.has(meta.title.toLowerCase()),'missing/duplicate title: '+id);
    requireMatch(typeof meta.description==='string'&&meta.description.trim().length>=18,
      'missing description: '+id);
    titles.add(meta.title.toLowerCase());
    const {stage,track,order}=meta.curriculum||{};
    requireMatch(Object.hasOwn(stages,stage)&&typeof track==='string'&&
      Number.isInteger(order)&&order>0,'invalid stage/track/order: '+id);
    stages[stage]++;
    const key=stage+':'+track;
    tracks.set(key,[...(tracks.get(key)||[]),order]);
  }
  requireMatch(compare(stages,{fundamentals:12,basic:7,learning:6,practice:1}),
    'three-stage lesson counts changed');
  for(const [track,orders] of tracks){
    const ordered=[...orders].sort((a,b)=>a-b);
    requireMatch(ordered.every((n,i)=>n===i+1),'gapped/duplicate track order: '+track);
  }
  requireMatch(byId.get('numbers_1-20')?.items.length===20&&
    byId.get('numbers_1-20')?.curriculum.track==='first-words',
    'Numbers 1–20 must remain one 20-item lesson');

  let sourceLessons=0,originalAudio=0;
  for(const filename of fs.readdirSync(sourceDir).filter(name=>name.endsWith('.json')).sort()){
    const id=path.basename(filename,'.json');
    if(retired.has(id))continue;
    const migrated=migrateLesson(filename,load(path.join(sourceDir,filename)));
    const lesson=byId.get(id);
    requireMatch(lesson?.source==='legacy'&&lesson?.kind===migrated.kind&&
      lesson.items.length===migrated.items.length,'legacy source mapping: '+id);
    sourceLessons++;
    const recorded=path.join(audioDir,id,lesson.kind==='reading'?'reading':'audio');
    const audioFiles=fs.existsSync(recorded)?
      fs.readdirSync(recorded).filter(name=>name.toLowerCase().endsWith('.mp3')):[];
    for(const [index,original] of migrated.items.entries()){
      const built=lesson.items[index];
      requireMatch(built.id===original.id&&built.polish===original.polish&&
        built.english===original.english,'original Polish/English/ID drift: '+original.id);
      const originalFile=audioFiles.find(name=>name===index+'.mp3'||name.startsWith(index+'_'));
      if(!originalFile){
        requireMatch(!built.audio,'audio attached without original source: '+original.id);
        continue;
      }
      const expected='generated/audio/'+encodeURIComponent(id)+'/'+index+'.mp3';
      requireMatch(built.audio===expected,'audio path drift: '+original.id);
      const from=assetBytes(path.join(recorded,originalFile));
      const to=assetBytes(path.join(publicDir,'generated/audio',id,index+'.mp3'));
      requireMatch(Buffer.isBuffer(from)&&Buffer.isBuffer(to)&&from.equals(to),
        'audio bytes differ from original: '+original.id);
      originalAudio++;
    }
  }
  requireMatch(sourceLessons===20&&originalAudio===455,'original source/audio inventory changed');

  let curatedReferences=0;
  requireMatch(Array.isArray(sounds)&&sounds.length===5,'curated sound inventory changed');
  for(const definition of sounds){
    const lesson=byId.get(definition.id);
    requireMatch(lesson?.kind==='sounds'&&lesson.source==='curated'&&lesson.needsReview===true,
      'curated sound metadata mismatch: '+definition.id);
    const expectedIds=[];
    for(const group of definition.groups){
      const actual=lesson.soundGroups?.find(g=>g.id===group.id);
      requireMatch(actual?.itemIds.length===group.examples.length,
        'sound group missing: '+definition.id+':'+group.id);
      for(const [i,example] of group.examples.entries()){
        const source=byId.get(example.set)?.items?.[example.index];
        const id=definition.id+':'+group.id+':'+i;
        const item=lesson.items.find(x=>x.id===id);
        requireMatch(source&&source.polish===example.expected&&item?.polish===source.polish&&
          item.english===source.english&&item.audio===source.audio&&
          item.soundFocus===example.focus,
          'curated source/audio mapping drift: '+id);
        expectedIds.push(id);curatedReferences++;
      }
      requireMatch(compare(actual.itemIds,expectedIds.slice(-group.examples.length)),
        'sound group item ordering drift: '+definition.id+':'+group.id);
    }
    requireMatch(compare(lesson.items.map(x=>x.id),expectedIds),
      'sound lesson card inventory drift: '+definition.id);
  }
  requireMatch(curatedReferences===26,'unexpected number of original-audio sound references');
  const lab=byId.get('speak_swietokrzyska');
  requireMatch(lab?.curriculum.stage==='practice'&&lab.items.length===1&&
    lab.items[0].polish==='Świętokrzyska'&&!lab.items[0].audio,
    'unverified diagnostic lab must not receive synthetic audio');

  const protectedIds=new Set([...voice.sourceBlockers,...otherBlockers.sourceBlockers]
    .map(b=>b.itemId));
  requireMatch(protectedIds.size===14,'Speak blocker inventory changed');
  for(const lesson of lessons){
    for(const item of lesson.items){
      const guarded=protectedIds.has(item.id);
      requireMatch((item.referenceReview==='practice_only')===guarded,
        'unexpected scored/practice-only source: '+item.id);
      if(item.audio){
        requireMatch(item.audio.startsWith('generated/audio/')&&
          !item.audio.includes('..')&&!item.audio.includes('\\'),
          'unsafe audio asset reference: '+item.id);
        requireMatch(fs.existsSync(path.join(publicDir,decodeURIComponent(item.audio))),
          'missing audio asset: '+item.id);
      }
    }
  }
  return {
    lessons:lessons.length,items:allItems.length,stages,
    sourceLessons,originalAudioCopies:originalAudio,
    curatedSoundLessons:sounds.length,curatedAudioReferences:curatedReferences,
    practiceOnlyReferences:protectedIds.size,
    unrecordedDiagnosticItems:lab.items.length,
    status:'source_mapping_and_bytes_verified_not_native_speaker_approved'
  };
}
