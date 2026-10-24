import raw from '../../content/sound-listening-v1.json';
import type {Lesson,LessonItem} from './model';

export type SoundListeningCard={item:LessonItem;groupId:string};
type PlanEntry={lessonId:string;questions:{itemId:string;groupId:string;expectedPolish:string;expectedFocus:string}[]};

const SOURCE_STATUS='existing_recorded_whole_word_sound_examples_editorial_not_native_certified';
const isObject=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v);
const exactKeys=(v:Record<string,unknown>,fields:string[])=>
 Object.keys(v).sort().join('|')===[...fields].sort().join('|');
const fail=():never=>{throw Error('Invalid source-only Polish sound listening plan');};

export function validateSoundListeningPlan(value:unknown):PlanEntry[]{
 if(!isObject(value)||!exactKeys(value,['schemaVersion','status','notes','lessons'])||
    value.schemaVersion!==1||value.status!==SOURCE_STATUS||
    typeof value.notes!=='string'||value.notes.length<40||
    !Array.isArray(value.lessons)||value.lessons.length!==5)return fail();
 const ids=new Set<string>();
 let total=0;
 const plan:PlanEntry[]=[];
 for(const entry of value.lessons){
  if(!isObject(entry)||!exactKeys(entry,['lessonId','questions'])||
    typeof entry.lessonId!=='string'||!entry.lessonId.startsWith('contrast_')||
    ids.has(entry.lessonId)||!Array.isArray(entry.questions)||
    entry.questions.length<4||entry.questions.length>8)return fail();
  ids.add(entry.lessonId);
  const seen=new Set<string>(),groups=new Set<string>();
  const questions:PlanEntry['questions']=[];
  for(const q of entry.questions){
   if(!isObject(q)||!exactKeys(q,['itemId','groupId','expectedPolish','expectedFocus'])||
      typeof q.itemId!=='string'||typeof q.groupId!=='string'||
      typeof q.expectedPolish!=='string'||typeof q.expectedFocus!=='string'||
      !q.itemId.startsWith(entry.lessonId+':'+q.groupId+':')||
      !q.expectedFocus||q.expectedFocus.length>8||
      !q.expectedPolish||q.expectedPolish.indexOf(q.expectedFocus)<0||
      seen.has(q.itemId))return fail();
   seen.add(q.itemId);groups.add(q.groupId);
   questions.push({
    itemId:q.itemId,groupId:q.groupId,
    expectedPolish:q.expectedPolish,expectedFocus:q.expectedFocus
   });
  }
  if(groups.size<2)return fail();
  total+=questions.length;
  plan.push({lessonId:entry.lessonId,questions});
 }
 if(total!==25)return fail();
 return plan;
}
export const SOUND_LISTENING_PLAN:readonly PlanEntry[]=validateSoundListeningPlan(raw);

/** Fail closed per lesson. Preserve existing recorded Polish originals rather
 * than inventing stand-alone sounds, guesses, new item IDs or progress. */
export function soundListeningCards(lesson:Lesson):SoundListeningCard[]{
 if(lesson.kind!=='sounds'||lesson.source!=='curated'||!lesson.soundGroups||
    lesson.soundGroups.length<2)return [];
 const plan=SOUND_LISTENING_PLAN.find(p=>p.lessonId===lesson.id);
 if(!plan)return [];
 const source=new Map(lesson.items.map(item=>[item.id,item]));
 const groups=new Map(lesson.soundGroups.map(group=>[group.id,group]));
 const result:SoundListeningCard[]=[];
 for(const record of plan.questions){
  const item=source.get(record.itemId),group=groups.get(record.groupId);
  if(!item||!group||!group.itemIds.includes(item.id)||
    item.soundGroupId!==record.groupId||
    item.polish!==record.expectedPolish||
    item.soundFocus!==record.expectedFocus||
    item.referenceReview==='practice_only'||
    !item.audio||!/^generated\/audio\/[a-zA-Z0-9_%.-]+\/[0-9]+\.mp3$/.test(item.audio)||
    item.polish.indexOf(item.soundFocus)!==item.polish.lastIndexOf(item.soundFocus))
      return [];
  result.push({item,groupId:record.groupId});
 }
 return result;
}
