import raw from '../../content/foundation-next-words-v1.json';
import type {Lesson,LessonItem} from './model';
import type {StarterGroup} from './foundation-first-expressions';

/** Exact original recorded whole-utterance anchors, separately pinned from
 * mutable source manifest. This is NOT independent native acoustic approval. */
const LOCK=[
  {
    "id": "everyday-replies",
    "title": "More everyday replies",
    "lessonId": "Conversation_1",
    "itemRefs": [
      {
        "id": "Conversation_1:16",
        "expectedPolish": "Może",
        "expectedEnglish": "Maybe"
      },
      {
        "id": "Conversation_1:17",
        "expectedPolish": "Jasne",
        "expectedEnglish": "Sure / Of course"
      },
      {
        "id": "Conversation_1:18",
        "expectedPolish": "Oczywiście",
        "expectedEnglish": "Of course"
      },
      {
        "id": "Conversation_1:19",
        "expectedPolish": "Mam pytanie",
        "expectedEnglish": "I have a question"
      },
      {
        "id": "Conversation_1:20",
        "expectedPolish": "Nie rozumiem",
        "expectedEnglish": "I don’t understand"
      }
    ]
  },
  {
    "id": "street-words",
    "title": "Street and place words",
    "lessonId": "Road_Terminology",
    "itemRefs": [
      {
        "id": "Road_Terminology:0",
        "expectedPolish": "ulica",
        "expectedEnglish": "Street"
      },
      {
        "id": "Road_Terminology:1",
        "expectedPolish": "aleja",
        "expectedEnglish": "Avenue / Boulevard"
      },
      {
        "id": "Road_Terminology:2",
        "expectedPolish": "plac",
        "expectedEnglish": "Square / Plaza"
      },
      {
        "id": "Road_Terminology:3",
        "expectedPolish": "droga",
        "expectedEnglish": "Road"
      },
      {
        "id": "Road_Terminology:8",
        "expectedPolish": "most",
        "expectedEnglish": "Bridge"
      },
      {
        "id": "Road_Terminology:9",
        "expectedPolish": "rondo",
        "expectedEnglish": "Roundabout"
      }
    ]
  },
  {
    "id": "transport-words",
    "title": "Getting around: first words",
    "lessonId": "Transit_1",
    "itemRefs": [
      {
        "id": "Transit_1:2",
        "expectedPolish": "Bilet",
        "expectedEnglish": "Ticket"
      },
      {
        "id": "Transit_1:5",
        "expectedPolish": "Metro",
        "expectedEnglish": "Metro / Subway"
      },
      {
        "id": "Transit_1:6",
        "expectedPolish": "Autobus",
        "expectedEnglish": "Bus"
      },
      {
        "id": "Transit_1:7",
        "expectedPolish": "Tramwaj",
        "expectedEnglish": "Tram"
      },
      {
        "id": "Transit_1:16",
        "expectedPolish": "Pociąg",
        "expectedEnglish": "Train"
      },
      {
        "id": "Transit_1:18",
        "expectedPolish": "Kierunek",
        "expectedEnglish": "Direction"
      }
    ]
  },
  {
    "id": "food-requests",
    "title": "Simple food requests",
    "lessonId": "Conversation_-_restaurant",
    "itemRefs": [
      {
        "id": "Conversation_-_restaurant:2",
        "expectedPolish": "Poproszę wodę",
        "expectedEnglish": "Water, please"
      },
      {
        "id": "Conversation_-_restaurant:3",
        "expectedPolish": "Poproszę kawę",
        "expectedEnglish": "Coffee, please"
      },
      {
        "id": "Conversation_-_restaurant:4",
        "expectedPolish": "Poproszę herbatę",
        "expectedEnglish": "Tea, please"
      },
      {
        "id": "Conversation_-_restaurant:12",
        "expectedPolish": "Zupa dnia",
        "expectedEnglish": "Soup of the day"
      },
      {
        "id": "Conversation_-_restaurant:14",
        "expectedPolish": "Deser",
        "expectedEnglish": "Dessert"
      }
    ]
  },
  {
    "id": "shopping-questions",
    "title": "Questions in a shop",
    "lessonId": "Conversation_-_shopping",
    "itemRefs": [
      {
        "id": "Conversation_-_shopping:0",
        "expectedPolish": "Ile to kosztuje?",
        "expectedEnglish": "How much does this cost?"
      },
      {
        "id": "Conversation_-_shopping:1",
        "expectedPolish": "Ile to razem?",
        "expectedEnglish": "How much is it altogether?"
      },
      {
        "id": "Conversation_-_shopping:2",
        "expectedPolish": "Czy mogę zapłacić kartą?",
        "expectedEnglish": "Can I pay by card?"
      },
      {
        "id": "Conversation_-_shopping:5",
        "expectedPolish": "Gdzie jest kasa?",
        "expectedEnglish": "Where is the checkout?"
      },
      {
        "id": "Conversation_-_shopping:8",
        "expectedPolish": "Poproszę paragon",
        "expectedEnglish": "Receipt, please"
      }
    ]
  },
  {
    "id": "location-questions",
    "title": "Asking where things are",
    "lessonId": "Getting_Around_1",
    "itemRefs": [
      {
        "id": "Getting_Around_1:0",
        "expectedPolish": "Gdzie jest przystanek?",
        "expectedEnglish": "Where is the bus/tram stop?"
      },
      {
        "id": "Getting_Around_1:2",
        "expectedPolish": "Gdzie jest metro?",
        "expectedEnglish": "Where is the metro?"
      },
      {
        "id": "Getting_Around_1:14",
        "expectedPolish": "Ile kosztuje bilet?",
        "expectedEnglish": "How much is the ticket?"
      },
      {
        "id": "Getting_Around_1:17",
        "expectedPolish": "Gdzie mogę kupić bilet?",
        "expectedEnglish": "Where can I buy a ticket?"
      },
      {
        "id": "Getting_Around_1:22",
        "expectedPolish": "Czy to daleko stąd?",
        "expectedEnglish": "Is it far from here?"
      }
    ]
  }
] as const;
const isRecord=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x);
const keys=(x:Record<string,unknown>,k:string[])=>Object.keys(x).sort().join('|')===[...k].sort().join('|');
const fail=():never=>{throw Error('Invalid C-06 inherited source first-word manifest');};

export function validateNextWordManifest(value:unknown):StarterGroup[]{
 if(!isRecord(value)||!keys(value,['schemaVersion','status','sourcePolicy','groups'])||
  value.schemaVersion!==1||
  value.status!=='source_only_original_recordings_not_independently_native_certified'||
  value.sourcePolicy!=='fixed_existing_whole_utterances_do_not_create_new_lessons_or_voice'||
  !Array.isArray(value.groups)||value.groups.length!==LOCK.length)return fail();
 const result:StarterGroup[]=[],seen=new Set<string>();
 for(let i=0;i<LOCK.length;i++){
  const fixed=LOCK[i],group=value.groups[i];
  if(!isRecord(group)||!keys(group,['id','title','lessonId','itemRefs'])||
   group.id!==fixed.id||group.title!==fixed.title||group.lessonId!==fixed.lessonId||
   !Array.isArray(group.itemRefs)||group.itemRefs.length!==fixed.itemRefs.length)return fail();
  const ids:string[]=[];
  for(let j=0;j<fixed.itemRefs.length;j++){
   const candidate=group.itemRefs[j],expected=fixed.itemRefs[j];
   if(!isRecord(candidate)||!keys(candidate,['id','expectedPolish','expectedEnglish'])||
      candidate.id!==expected.id||candidate.expectedPolish!==expected.expectedPolish||
      candidate.expectedEnglish!==expected.expectedEnglish||seen.has(expected.id))return fail();
   seen.add(expected.id);ids.push(expected.id);
  }
  result.push({id:fixed.id,title:fixed.title,lessonId:fixed.lessonId,itemIds:ids});
 }
 if(seen.size!==32)return fail();
 return result;
}
export const NEXT_WORD_GROUPS:readonly StarterGroup[]=validateNextWordManifest(raw);

/** A session is available ONLY when every original source row is exact and has
 * its own original recording, never an alias to another item or lesson. */
export function availableNextWordGroups(lessons:readonly Lesson[]):StarterGroup[]{
 const byId=new Map(lessons.filter(l=>l.source==='legacy'&&l.kind==='vocabulary').map(l=>[l.id,l]));
 return NEXT_WORD_GROUPS.filter(group=>{
  const origin=byId.get(group.lessonId),lock=LOCK.find(x=>x.id===group.id);
  return !!origin&&!!lock&&group.itemIds.every((id,index)=>{
   const item=origin.items.find(x=>x.id===id),expected=lock.itemRefs[index];
   return !!item&&item.polish===expected.expectedPolish&&
    item.english===expected.expectedEnglish&&item.referenceReview!=='practice_only'&&
    item.audio==='generated/audio/'+encodeURIComponent(group.lessonId)+'/'+
     id.slice(group.lessonId.length+1)+'.mp3';
  });
 });
}

/** Preserve ORIGINAL per-item IDs, XP, review state and audio references. */
export function nextWordSessionItems(lesson:Lesson,group:StarterGroup,mode:'learn'|'listen'|'speak'):LessonItem[]{
 if(lesson.id!==group.lessonId||lesson.kind!=='vocabulary'||
    !availableNextWordGroups([lesson]).some(x=>x.id===group.id))return [];
 return group.itemIds.map(id=>lesson.items.find(item=>item.id===id)!)
  .filter(item=>mode!=='listen'||!!item.audio&&item.referenceReview!=='practice_only');
}
