import type {Lesson} from './model';

export type ReadingIntroductionTurn={
 id:string;polish:string;english:string;audio:string;
};
/** Source reading lessons, original complete dialogue recordings.
 * This is explicitly not a new translation, a generated phoneme,
 * independently approved voice, or a new progress track. */
export const READING_INTRO_COUNTS={
 Basic_01R:6,
 Grocery_store_very_basic_shopping:9,
 H_M_clothes_shop_trying_on_a_T-shirt:10,
 On_the_tram_talking_to_another_passenger:9,
 Asking_the_tram_driver_for_directions:8,
 Museum_buying_tickets_and_basic_info:9
} as const;
type ReadingSourceId=keyof typeof READING_INTRO_COUNTS;

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
  turns.push({id:item.id,polish:item.polish,english:item.english,audio});
 }
 return turns;
}
