// V3 projection of V2 tourist application plan. No invented dialogues or XP.
import fs from 'node:fs';
import path from 'node:path';

const STATUS='source_refs_only_native_review_pending';
const MODES=['listen','speak','read'];
const fail=(detail)=>{throw Error('V3 tourist unit source rejected: '+detail)};
const text=(v,min=1)=>typeof v==='string' && v.trim().length>=min;

export function readTouristSource(repo){
  return JSON.parse(fs.readFileSync(path.join(repo,'v2/content/tourist-units-v1.json'),'utf8'));
}
export function compileTouristUnits(manifest,source){
  if (manifest?.schemaVersion!==1 || !Array.isArray(manifest.lessons) ||
      source?.schemaVersion!==1 || source.editorialStatus!==STATUS ||
      !Array.isArray(source.units)||source.units.length!==8) {
    fail('catalog/editorial schema');
  }
  const byLesson=new Map(manifest.lessons.map(x=>[x.id,x]));
  const units=[];
  for(let i=0;i<source.units.length;i++){
    const entry=source.units[i];
    if(!entry || entry.id!=='T0'+(i+1) || entry.journey!==1 ||
       entry.position!==(i<3?'beginning':'middle') ||
       entry.order!==i+1 || !text(entry.title,5) || !text(entry.outcome,12) ||
       !Array.isArray(entry.steps) || ![2,3].includes(entry.steps.length) ||
       (entry.gaps!==undefined && (!Array.isArray(entry.gaps) ||
         entry.gaps.some(g=>!text(g,12))))) fail('unit identity/order '+i);
    const steps=[];const encountered=new Set();
    for(let j=0;j<entry.steps.length;j++){
      const step=entry.steps[j];
      const expected=MODES[j];
      if(!step || step.mode!==expected || !text(step.lessonId) ||
         step.lessonId.startsWith('personal_') || step.lessonId==='speak_swietokrzyska' ||
         !Array.isArray(step.itemIds) || !step.itemIds.length ||
         new Set(step.itemIds).size!==step.itemIds.length) {
        fail('unit mode or item inventory '+entry.id);
      }
      const lesson=byLesson.get(step.lessonId);
      if(!lesson || lesson.source==='personal' ||
         (expected==='read'&&lesson.kind!=='reading') ||
         (expected==='speak'&&lesson.kind==='reading') ||
         (expected==='listen'&&!lesson.items.some(item=>
             item.audio && item.referenceReview!=='practice_only'))) {
        fail('unavailable lesson/mode '+entry.id+':'+expected);
      }
      let last=-1;
      const items=step.itemIds.map(id=>{
        if(typeof id!=='string' || !/^.+:\d+$/.test(id) ||
           !id.startsWith(lesson.id+':') || encountered.has(expected+':'+id)) {
          fail('invalid source item '+entry.id+':'+expected);
        }
        const index=lesson.items.findIndex(x=>x.id===id);
        const item=lesson.items[index];
        const lastToken=Number(id.slice(id.lastIndexOf(':')+1));
        const originalAudio='generated/audio/'+encodeURIComponent(lesson.id)+'/'+lastToken+'.mp3';
        if(index<=last || !item || item.referenceReview==='practice_only' ||
           item.audio!==originalAudio || !text(item.polish) || !text(item.english)) {
          fail('changed or unreviewed original recording '+entry.id+':'+id);
        }
        encountered.add(expected+':'+id);last=index;
        return {id:item.id,polish:item.polish,english:item.english,
          audio:item.audio,
          ...(item.comprehension?{comprehension:item.comprehension}:{})};
      });
      steps.push({mode:expected,lessonId:lesson.id,title:lesson.title,items});
    }
    units.push({id:entry.id,order:entry.order,journey:entry.journey,
      position:entry.position,title:entry.title,outcome:entry.outcome,
      steps,...(entry.gaps?{gaps:entry.gaps}:{})});
  }
  return {schemaVersion:1,editorialStatus:STATUS,units};
}
