import raw from '../../content/foundation-first-expressions-v1.json';
import type {Lesson} from './model';

export type StarterGroup={id:string;title:string;lessonId:string;itemIds:string[]};
const ORIGINAL='Conversation_1';
const EXPECTED=[
 ['greetings','Conversation_1:0','Dzień dobry'],
 ['greetings','Conversation_1:2','Cześć'],
 ['greetings','Conversation_1:4','Do widzenia'],
 ['politeness','Conversation_1:10','Proszę'],
 ['politeness','Conversation_1:8','Dziękuję'],
 ['politeness','Conversation_1:12','Przepraszam'],
 ['simple-replies','Conversation_1:14','Tak'],
 ['simple-replies','Conversation_1:15','Nie'],
] as const;
const TITLES=['Hello and goodbye','Polite essentials','Yes and no'] as const;
const GROUPS=['greetings','politeness','simple-replies'] as const;

export function validateStarterManifest(value:unknown):StarterGroup[]{
 const bad=()=>{throw Error('Invalid source-only first expressions manifest');};
 if(!value||typeof value!=='object'||Array.isArray(value))return bad();
 const x=value as Record<string,unknown>;
 if(Object.keys(x).sort().join('|')!==['schemaVersion','status','sourceLessonId','sourcePolicy','groups'].sort().join('|')||
   x.schemaVersion!==1||x.sourceLessonId!==ORIGINAL||
   x.status!=='source_only_existing_recordings_not_independently_native_certified'||
   x.sourcePolicy!=='use_full_original_recorded_utterances_exact_item_ids_no_new_audio_or_review_claims'||
   !Array.isArray(x.groups)||x.groups.length!==3)return bad();
 let pos=0;
 const result:StarterGroup[]=[];
 for(let g=0;g<3;g++){
   const group=x.groups[g] as Record<string,unknown>;
   if(!group||typeof group!=='object'||Array.isArray(group)||
     Object.keys(group).sort().join('|')!==['id','title','itemRefs'].sort().join('|')||
     group.id!==GROUPS[g]||group.title!==TITLES[g]||
     !Array.isArray(group.itemRefs)||group.itemRefs.length!==(g===2?2:3))return bad();
   const ids:string[]=[];
   for(const ref of group.itemRefs){
     const item=ref as Record<string,unknown>;
     const expected=EXPECTED[pos++];
     if(!item||typeof item!=='object'||Array.isArray(item)||
       Object.keys(item).sort().join('|')!==['id','expectedPolish'].sort().join('|')||
       item.id!==expected[1]||item.expectedPolish!==expected[2])return bad();
     ids.push(item.id as string);
   }
   result.push({id:group.id as string,title:group.title as string,lessonId:ORIGINAL,itemIds:ids});
 }
 if(pos!==8||new Set(result.flatMap(x=>x.itemIds)).size!==8)return bad();
 return result;
}

export const FIRST_EXPRESSION_GROUPS:readonly StarterGroup[]=validateStarterManifest(raw);

/** Whole original item/audio pairs only; do not infer native/acoustic approval
 * from presence of MP3 or from authors' expected orthography. */
export function availableStarterGroups(lessons:readonly Lesson[]):StarterGroup[]{
 const origin=lessons.find(x=>x.id===ORIGINAL&&x.kind==='vocabulary'&&x.source==='legacy');
 if(!origin)return [];
 return FIRST_EXPRESSION_GROUPS.filter(group=>group.itemIds.every(id=>{
  const item=origin.items.find(x=>x.id===id);
  const expected=EXPECTED.find(x=>x[1]===id);
  return !!item&&!!expected&&item.polish===expected[2]&&
   item.referenceReview!== 'practice_only'&&
   item.audio==='generated/audio/Conversation_1/'+id.split(':')[1]+'.mp3';
 }));
}

export function starterSessionItems(lesson:Lesson,group:StarterGroup,mode:'learn'|'listen'|'speak'){
 if(lesson.id!==group.lessonId||lesson.kind!=='vocabulary'||
    !availableStarterGroups([lesson]).some(g=>g.id===group.id))
   return [];
 const ids=new Set(group.itemIds);
 return group.itemIds.map(id=>lesson.items.find(item=>item.id===id)!)
  .filter(item=>ids.has(item.id)&&
   (mode!=='listen'||(!!item.audio&&item.referenceReview!=='practice_only')));
}
