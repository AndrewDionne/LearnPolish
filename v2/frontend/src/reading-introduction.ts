import type {Lesson} from './model';
import firstDialogueCues from '../../content/journey1-c15-greetings-cues-v1.json';

export type ReadingIntroductionTurn={
 id:string;polish:string;english:string;audio:string;teachingCue?:string;
};
/** Source reading lessons, original complete dialogue recordings.
 * This is explicitly not a new translation, a generated phoneme,
 * independently approved voice, or a new progress track. */
export const READING_INTRO_COUNTS={
 Basic_01R:6,
 Grocery_store_very_basic_shopping:9,
 'H_M_clothes_shop_trying_on_a_T-shirt':10,
 On_the_tram_talking_to_another_passenger:9,
 Asking_the_tram_driver_for_directions:8,
 Museum_buying_tickets_and_basic_info:9
} as const;
type ReadingSourceId=keyof typeof READING_INTRO_COUNTS;

/** First-dialogue instruction is an optional editorial draft tied to the EXACT original
 * source line; it is not an audio regeneration or a native-certified grammar grade.
 * A changed utterance simply loses its cue, never the underlying Read lesson. */
export function firstDialogueTeachingCue(id:string,index:number,polish:string):string|undefined{
 if(id!=='Basic_01R'||firstDialogueCues.schemaVersion!==1||
    firstDialogueCues.lesson!==id||
    firstDialogueCues.status!=='source_anchored_draft_learning_cues_not_native_editorial_signoff'||
    firstDialogueCues.lines.length!==6)return undefined;
 const entry=firstDialogueCues.lines[index];
 return entry?.id===id+':'+index && entry.polish===polish &&
        typeof entry.cue==='string' && entry.cue.trim().length>40 ? entry.cue : undefined;
}

/** All-or-nothing for each original reading source: missing original text,
 * English meaning, item ID or exact MP3 disables its optional preparation.
 * The underlying original lesson is NEVER changed or hidden. */
export function recordedReadingIntroduction(lesson:Lesson):ReadingIntroductionTurn[]{
 if(lesson.source!=='legacy'||lesson.kind!=='reading'||
    !Object.hasOwn(READING_INTRO_COUNTS,lesson.id))return [];
 const id=lesson.id as ReadingSourceId;
 if(lesson.items.length!==READING_INTRO_COUNTS[id])return [];
 const turns:ReadingIntroductionTurn[]=[];
 for(let i=0;i<lesson.items.length;i++){
  const item=lesson.items[i];
  const audio='generated/audio/'+encodeURIComponent(id)+'/'+i+'.mp3';
  if(item.id!==id+':'+i||!item.polish.trim()||!item.english.trim()||
     item.audio!==audio||item.referenceReview==='practice_only')return [];
  turns.push({id:item.id,polish:item.polish,english:item.english,audio,
   ...(firstDialogueTeachingCue(id,i,item.polish)?
     {teachingCue:firstDialogueTeachingCue(id,i,item.polish)}:{})});
 }
 return turns;
}
