import raw from '../../content/foundation-sentence-patterns-v1.json';
import type {Lesson} from './model';

export type RecordedSentenceExample={
 itemId:string;polish:string;english:string;focus:string;audio:string;
};
export type SentencePattern={
 id:string;title:string;cue:string;explanation:string;examples:RecordedSentenceExample[];
};
type SourceExample={sourceLesson:string;index:number;polish:string;english:string;focus:string};
type SourceGroup={id:string;title:string;cue:string;explanation:string;examples:SourceExample[]};

const EXPECTED=['requests','where','permission','negative','one-two'];
const STATUS='source_only_recorded_utterances_grammar_not_independently_native_reviewed';
const isRecord=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==='object'&&!Array.isArray(x);
const exactKeys=(x:Record<string,unknown>,expected:string[])=>
 Object.keys(x).sort().join('|')===expected.slice().sort().join('|');
const fail=():never=>{throw Error('Invalid source-only Polish sentence pattern corpus');};
const uniqueFocus=(word:string,focus:string)=>word.split(focus).length===2;

export function validateSentencePatternSource(value:unknown):SourceGroup[]{
 if(!isRecord(value)||!exactKeys(value,['schemaVersion','status','notes','groups'])||
   value.schemaVersion!==1||value.status!==STATUS||
   typeof value.notes!=='string'||value.notes.length<100||
   !Array.isArray(value.groups)||value.groups.length!==EXPECTED.length)return fail();
 const seen=new Set<string>();
 return value.groups.map((g,i)=>{
  if(!isRecord(g)||!exactKeys(g,['id','title','cue','explanation','examples'])||
    g.id!==EXPECTED[i]||typeof g.title!=='string'||g.title.length<9||
    typeof g.cue!=='string'||!g.cue||typeof g.explanation!=='string'||
    g.explanation.length<50||!Array.isArray(g.examples)||g.examples.length!==4)return fail();
  const examples=g.examples.map(entry=>{
   if(!isRecord(entry)||!exactKeys(entry,['sourceLesson','index','polish','english','focus'])||
     typeof entry.sourceLesson!=='string'||!/^[a-zA-Z0-9_-]+$/.test(entry.sourceLesson)||
     !Number.isSafeInteger(entry.index)||Number(entry.index)<0||
     typeof entry.polish!=='string'||!entry.polish||
     typeof entry.english!=='string'||!entry.english||
     typeof entry.focus!=='string'||!entry.focus||
     !uniqueFocus(entry.polish,entry.focus)||
     entry.polish!==entry.polish.normalize('NFC')||
     entry.focus!==entry.focus.normalize('NFC')||
     seen.has(entry.sourceLesson+':'+entry.index))return fail();
   seen.add(entry.sourceLesson+':'+entry.index);
   return {sourceLesson:entry.sourceLesson,index:Number(entry.index),
    polish:entry.polish,english:entry.english,focus:entry.focus};
  });
  return {id:g.id,title:g.title,cue:g.cue,explanation:g.explanation,examples};
 });
}
export const SENTENCE_PATTERN_SOURCE=validateSentencePatternSource(raw);

/** Each recorded complete utterance/English meaning MUST exactly match the
 * original lesson. No piecing words together to fake a matching recording. */
export function availableSentencePatterns(lessons:readonly Lesson[]):SentencePattern[]{
 const sources=new Map(lessons.filter(x=>x.kind==='vocabulary'&&x.source==='legacy').map(x=>[x.id,x]));
 return SENTENCE_PATTERN_SOURCE.flatMap(group=>{
  const examples:RecordedSentenceExample[]=[];
  for(const row of group.examples){
   const original=sources.get(row.sourceLesson);
   const itemId=row.sourceLesson+':'+row.index;
   const item=original?.items.find(x=>x.id===itemId);
   const expectedAudio='generated/audio/'+encodeURIComponent(row.sourceLesson)+'/'+row.index+'.mp3';
   if(!item||item.polish!==row.polish||item.english!==row.english||
     item.referenceReview==='practice_only'||item.audio!==expectedAudio)return [];
   examples.push({itemId,polish:item.polish,english:item.english,
    audio:expectedAudio,focus:row.focus});
  }
  return [{id:group.id,title:group.title,cue:group.cue,
    explanation:group.explanation,examples}];
 });
}
