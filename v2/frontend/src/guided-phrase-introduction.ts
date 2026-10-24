import type {Lesson,LessonItem} from './model';
import type {StarterGroup} from './foundation-first-expressions';
import {READING_INTRO_COUNTS} from './reading-introduction';
import type {ReadingIntroductionTurn} from './reading-introduction';
import chronology from '../../content/journey1-c16b-chronological-source-uses-v1.json';
import firstSentenceCues from '../../content/journey1-c16b-first-sentence-cues-v1.json';

const DRAFT='source_anchored_draft_guided_sentence_teaching_not_native_certified';
const STATUS='guided_chronological_source_trace_only_not_native_lexical_or_morphology_approval';
const GROUPS=['simple-replies','politeness','greetings','street-words','transport-words',
  'everyday-replies','food-requests','shopping-questions','location-questions'];

/** Distinct from the optional original library and the Read lesson's own
 * existing intro. This guided *Listen* intro cannot grade or grant XP.
 * It teaches full original audio + meaning before first comprehension;
 * each focused first-sentence application also gets a draft pattern note.
 *
 * All-or-nothing at GROUP granularity to avoid attaching notes to altered
 * original content. Nothing here marks human-native grammar as approved. */
export function guidedPhraseIntroduction(
 lesson:Lesson,group:StarterGroup,sessionItems:readonly LessonItem[]
):ReadingIntroductionTurn[]{
 if(lesson.kind!=='vocabulary'||lesson.source!=='legacy'||
    chronology.schemaVersion!==1||chronology.status!==STATUS||
    firstSentenceCues.schemaVersion!==1||firstSentenceCues.status!==DRAFT||
    !GROUPS.includes(group.id)||group.lessonId!==lesson.id||
    !group.itemIds.length||sessionItems.length!==group.itemIds.length||
    Object.hasOwn(READING_INTRO_COUNTS,lesson.id))return [];
 const step=chronology.guidedOrder.find(x=>x.unitId===group.id);
 if(!step||step.recordedSourceItems.length!==sessionItems.length)return [];
 const isSentence=['food-requests','shopping-questions','location-questions'].includes(group.id);
 const intro:ReadingIntroductionTurn[]=[];
 for(let i=0;i<sessionItems.length;i++){
  const expected=step.recordedSourceItems[i],item=sessionItems[i];
  const audio='generated/audio/'+encodeURIComponent(lesson.id)+'/'+item.id.split(':')[1]+'.mp3';
  const cue=firstSentenceCues.entries.find(x=>x.id===item.id);
  if(group.itemIds[i]!==item.id||item.id!==expected.id||
     item.polish!==expected.polish||item.english!==expected.english||
     item.audio!==audio||item.referenceReview==='practice_only'||
     (isSentence&&(!cue||cue.polish!==item.polish||cue.english!==item.english||
       cue.cue.trim().length<70))||
     (!isSentence&&!!cue))return [];
  intro.push({id:item.id,polish:item.polish,english:item.english,audio,
    ...(isSentence&&cue?{teachingCue:cue.cue}:{})});
 }
 return intro;
}
