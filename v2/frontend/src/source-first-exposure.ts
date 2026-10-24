import type {Lesson,LessonItem} from './model';
import type {TouristUnitStep} from './tourist-units';
import type {ReadingIntroductionTurn} from './reading-introduction';
import {contextualReadingCue} from './reading-introduction';
import rows from '../../content/journey1-item-prerequisite-audit-v1.json';
import sourceTourists from '../../content/tourist-units-v1.json';
import numbers from '../../../docs/sets/numbers_1-20.json';
import sentenceCues from '../../content/journey1-c16b-first-sentence-cues-v1.json';

const C15_STATUS='223_source_rows_traced_individually_linguistic_prerequisites_open';
const DRAFT_STATUS='source_anchored_draft_guided_sentence_teaching_not_native_certified';
const TOURIST_STATUS='source_refs_only_native_review_pending';
const bySource=new Map<string,typeof rows.rows>();
for(const row of rows.rows){
 const group=bySource.get(row.sourceLesson)??[];
 group.push(row);bySource.set(row.sourceLesson,group);
}
const recordedAudio=(id:string,index:number)=>
 'generated/audio/'+encodeURIComponent(id)+'/'+index+'.mp3';

/** Only source-anchored complete recordings and English, never synthesized
 * words/fragments. An original protected Speak row cannot be promoted by a preview. */
function originalFullLine(lesson:Lesson,item:LessonItem,index:number):boolean{
 const id=lesson.id;
 if(item.id!==id+':'+index||
    item.audio!==recordedAudio(id,index)||
    item.referenceReview==='practice_only')return false;
 if(id==='numbers_1-20'){
  const row=numbers.cards[index];
  return !!row&&item.polish===row.phrase&&item.english===row.meaning;
 }
 const row=bySource.get(id)?.[index];
 return !!row&&row.id===item.id&&row.polish===item.polish&&row.english===item.english;
}
function verifiedSource(lesson:Lesson):boolean{
 if(lesson.source!=='legacy'||rows.schemaVersion!==1||rows.status!==C15_STATUS)return false;
 const originalCount=lesson.id==='numbers_1-20'?numbers.cards.length:bySource.get(lesson.id)?.length;
 if(originalCount===undefined||lesson.items.length!==originalCount)return false;
 return lesson.items.every((item,index)=>{
  const id=lesson.id;
  if(item.id!==id+':'+index)return false;
  if(id==='numbers_1-20'){
   const row=numbers.cards[index];
   return !!row&&item.polish===row.phrase&&item.english===row.meaning;
  }
  const row=bySource.get(id)?.[index];
  return !!row&&row.id===item.id&&item.polish===row.polish&&item.english===row.english;
 });
}
function toIntro(lesson:Lesson,selected:readonly LessonItem[]):ReadingIntroductionTurn[]{
 if(!verifiedSource(lesson)||!selected.length)return [];
 const chosen=new Set(selected.map(x=>x.id));
 if(chosen.size!==selected.length)return [];
 const result:ReadingIntroductionTurn[]=[];
 for(const [i,item] of lesson.items.entries()){
  if(!chosen.has(item.id))continue;
  if(!originalFullLine(lesson,item,i))return [];
  const record=selected.find(x=>x.id===item.id);
  if(record!==item && (!record||record.polish!==item.polish||record.english!==item.english||
     record.audio!==item.audio||record.referenceReview!==item.referenceReview))return [];
  const readingNote=lesson.kind==='reading'?contextualReadingCue(lesson.id,i,item.polish,item.english):undefined;
  const guidedNote=sentenceCues.status===DRAFT_STATUS?
    sentenceCues.entries.find(x=>x.id===item.id&&x.polish===item.polish&&x.english===item.english)?.cue:undefined;
  result.push({id:item.id,polish:item.polish,english:item.english,audio:item.audio!,
    ...((readingNote||guidedNote)?{teachingCue:readingNote??guidedNote}:{})});
 }
 return result.length===selected.length&&selected.every((x,i)=>result[i].id===x.id)?result:[];
}

/** The seven independently browsable legacy basic sources are NOT a course.
 * Teach their intact Listen subset before its graded meaning questions.
 * Normal Speak already includes the complete original target, English and
 * playable full reference before optional recording (no duplicate Speak UI). */
export function originalLibraryListenIntroduction(
 lesson:Lesson,selected:readonly LessonItem[]
):ReadingIntroductionTurn[]{
 if(lesson.kind!=='vocabulary'||!rows.basicSourceLessonIds.includes(lesson.id))return [];
 return toIntro(lesson,selected);
}

/** Tourist listening often precedes the source Read introduction; attach
 * first-use learning to the precise selected source subset, not the entire
 * dialogue and never infer earlier mastery of independently available units. */
export function touristListenIntroduction(
 lesson:Lesson,step:TouristUnitStep,selected:readonly LessonItem[]
):ReadingIntroductionTurn[]{
 if(step.mode!=='listen'||step.lessonId!==lesson.id||
    sourceTourists.editorialStatus!==TOURIST_STATUS||
    !sourceTourists.units.some(unit=>unit.steps.some(s=>
      s.mode===step.mode&&s.lessonId===step.lessonId&&
      s.itemIds.length===step.itemIds.length&&
      s.itemIds.every((id,i)=>id===step.itemIds[i]))))return [];
 if(step.itemIds.length!==selected.length||
    !step.itemIds.every((id,i)=>selected[i]?.id===id))return [];
 return toIntro(lesson,selected);
}
