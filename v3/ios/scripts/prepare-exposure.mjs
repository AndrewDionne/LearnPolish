// Source-first whole-recording teaching before graded Listen or Read.
// Reuses V2 C14/C15/C16 authoritative source/audit without minting progress.
import fs from 'node:fs';
import path from 'node:path';

const READ_COUNTS={
  Basic_01R:6,
  Grocery_store_very_basic_shopping:9,
  'H_M_clothes_shop_trying_on_a_T-shirt':10,
  On_the_tram_talking_to_another_passenger:9,
  Asking_the_tram_driver_for_directions:8,
  Museum_buying_tickets_and_basic_info:9
};
const AUDIT_STATUS='223_source_rows_traced_individually_linguistic_prerequisites_open';
const FIRST_CUES_STATUS='source_anchored_draft_learning_cues_not_native_editorial_signoff';
const CONTEXT_CUES_STATUS='source_anchored_editorial_draft_not_native_language_reviewed';
const fail=m=>{throw Error('V3 source-first unavailable: '+m);};

export function readExposureSources(repo){
  const load=n=>JSON.parse(fs.readFileSync(path.join(repo,'v2/content',n),'utf8'));
  return {
    audit:load('journey1-item-prerequisite-audit-v1.json'),
    first:load('journey1-c15-greetings-cues-v1.json'),
    later:load('journey1-c16-reading-context-cues-v1.json')
  };
}

export function compileExposure(manifest,source){
  const {audit,first,later}=source;
  if(manifest?.schemaVersion!==1||!Array.isArray(manifest.lessons)||
     audit?.schemaVersion!==1||audit.status!==AUDIT_STATUS||
     audit.counts?.total!==223||audit.counts?.basic!==172||audit.counts?.reading!==51||
     !Array.isArray(audit.rows)||audit.rows.length!==223||
     !Array.isArray(audit.basicSourceLessonIds)||audit.basicSourceLessonIds.length!==7||
     !Array.isArray(audit.readingSourceLessonIds)||audit.readingSourceLessonIds.length!==6||
     first?.schemaVersion!==1||first.status!==FIRST_CUES_STATUS||
     first.lesson!=='Basic_01R'||!Array.isArray(first.lines)||first.lines.length!==6||
     later?.schemaVersion!==1||later.status!==CONTEXT_CUES_STATUS||
     !Array.isArray(later.lessons)||later.lessons.length!==5){
    fail('editorial audit or cue status changed');
  }
  const allLessons=new Map(manifest.lessons.map(x=>[x.id,x]));
  const auditRows=new Map();
  for(const row of audit.rows){
    if(auditRows.has(row.id)||!row.id||!row.sourceLesson)fail('repeated audit row');
    auditRows.set(row.id,row);
  }
  const sourceLesson=(id,expectedKind)=>{
    const lesson=allLessons.get(id);
    if(!lesson||lesson.kind!==expectedKind||lesson.source!=='legacy'||!lesson.items?.length){
      fail('original source missing: '+id);
    }
    const rows=audit.rows.filter(x=>x.sourceLesson===id);
    if(rows.length!==lesson.items.length)fail('audit source count: '+id);
    return lesson;
  };
  const validate=(lesson,item,index)=>{
    const id=lesson.id+':'+index;
    const row=auditRows.get(id);
    const audio='generated/audio/'+encodeURIComponent(lesson.id)+'/'+index+'.mp3';
    if(item.id!==id||!row||row.sourceLesson!==lesson.id||
       row.sourceIndex!==index||row.id!==id||
       item.polish!==row.polish||item.english!==row.english||
       (item.referenceReview!=='practice_only' && item.audio!==audio)||
       row.existingWholeRecording!==audio){
       fail('source text/audio drift: '+id);
    }
    return row;
  };

  const reading=audit.readingSourceLessonIds.map(id=>{
    const lesson=sourceLesson(id,'reading');
    if(!Object.hasOwn(READ_COUNTS,id)||lesson.items.length!==READ_COUNTS[id]){
      fail('read source count: '+id);
    }
    const noteSource=id==='Basic_01R'
       ?{lines:first.lines}
       :later.lessons.find(x=>x.lesson===id);
    if(!noteSource||noteSource.lines?.length!==lesson.items.length)fail('reading cues missing: '+id);
    const items=lesson.items.map((item,i)=>{
      validate(lesson,item,i);
      const cue=noteSource.lines[i];
      const safe=cue?.id===item.id && cue.polish===item.polish &&
        (id==='Basic_01R'||cue.english===item.english) &&
        typeof cue.cue==='string'&&cue.cue.trim().length>40;
      return {id:item.id,polish:item.polish,english:item.english,audio:item.audio,
        ...(safe?{teachingCue:cue.cue}:{})};
    });
    return {lessonId:id,mode:'read',title:lesson.title,items};
  });
  if(reading.reduce((n,s)=>n+s.items.length,0)!==51)fail('read total drift');

  // Only source-verified, unblocked recorded Listen items become first-exposure.
  // This is NOT a new graded lesson or a new learner mastery pathway.
  const listening=audit.basicSourceLessonIds.map(id=>{
    const lesson=sourceLesson(id,'vocabulary');
    const items=lesson.items.flatMap((item,i)=>{
      validate(lesson,item,i);
      return item.referenceReview==='practice_only'?[]:[{
        id:item.id,polish:item.polish,english:item.english,audio:item.audio
      }];
    });
    return {lessonId:id,mode:'listen',title:lesson.title,items};
  });
  if(listening.reduce((n,s)=>n+s.items.length,0)>172||listening.some(x=>!x.items.length)){
    fail('listen original recording inventory');
  }
  return {schemaVersion:1,editorialStatus:'source_only_original_recorded_turns_not_native_reviewed',
    reading,listening};
}
