import {describe,it,expect} from 'vitest';
import type {Lesson} from './model';
import {guidedPhraseIntroduction} from './guided-phrase-introduction';
import {FIRST_EXPRESSION_GROUPS} from './foundation-first-expressions';
import {NEXT_WORD_GROUPS} from './foundation-next-words';
import {orderedFoundationGroups} from './foundation-progression';
import greetings from '../../../docs/sets/Conversation_1.json';
import road from '../../../docs/sets/Road_Terminology.json';
import transit from '../../../docs/sets/Transit_1.json';
import restaurant from '../../../docs/sets/Conversation_-_restaurant.json';
import shopping from '../../../docs/sets/Conversation_-_shopping.json';
import gettingAround from '../../../docs/sets/Getting_Around_1.json';

const sources=[
 ['Conversation_1',greetings],
 ['Road_Terminology',road],
 ['Transit_1',transit],
 ['Conversation_-_restaurant',restaurant],
 ['Conversation_-_shopping',shopping],
 ['Getting_Around_1',gettingAround]
] as const;
const lessons:Lesson[]=sources.map(([id,raw])=>({
 id,title:id,source:'legacy',kind:'vocabulary',schemaVersion:1,
 items:raw.cards.map((card,i)=>({
  id:id+':'+i,polish:card.phrase,english:card.meaning,
  audio:'generated/audio/'+encodeURIComponent(id)+'/'+i+'.mp3'
 }))
}));
const all=orderedFoundationGroups(FIRST_EXPRESSION_GROUPS,NEXT_WORD_GROUPS);
const groups=[...all.firstWords,...all.basicVocabulary,...all.firstSentences];
const copy=<T,>(value:T):T=>structuredClone(value);

describe('C-16B true guided first-listen teaching from full original recordings',()=>{
 it('previews exactly 40 ordered source-backed guided expressions, including 15 with grammar cues',()=>{
  expect(groups.map(x=>x.id)).toEqual([
   'simple-replies','politeness','greetings','street-words','transport-words',
   'everyday-replies','food-requests','shopping-questions','location-questions'
  ]);
  const sessions=groups.map(group=>{
   const lesson=lessons.find(x=>x.id===group.lessonId)!;
   const subset=group.itemIds.map(id=>lesson.items.find(x=>x.id===id)!);
   return guidedPhraseIntroduction(lesson,group,subset);
  });
  expect(sessions.map(x=>x.length)).toEqual([2,3,3,6,6,5,5,5,5]);
  expect(sessions.flat()).toHaveLength(40);
  expect(sessions.slice(0,6).flat().every(x=>x.teachingCue===undefined)).toBe(true);
  expect(sessions.slice(6).flat().every(x=>(x.teachingCue?.length??0)>70)).toBe(true);
  expect(sessions[6][0].polish).toBe('Poproszę wodę');
  expect(sessions[7][2].teachingCue).toContain('zapłacić means to pay');
  expect(sessions[8][3].teachingCue).toContain('Gdzie means where');
  for(const session of sessions)for(const row of session){
   expect(row.audio).toBe('generated/audio/'+encodeURIComponent(row.id.split(':')[0])+'/'+row.id.split(':')[1]+'.mp3');
   expect(row.english.length).toBeGreaterThan(1);
  }
 });
 it('refuses wrong phrase, meaning, original voice, identity and fabricated course group',()=>{
  const group=all.firstSentences[1],source=lessons.find(x=>x.id===group.lessonId)!;
  const items=group.itemIds.map(id=>source.items.find(x=>x.id===id)!);
  expect(guidedPhraseIntroduction(source,group,items)).toHaveLength(5);
  for(const edit of [
   (x:Lesson)=>{x.items[0].polish='other';},
   (x:Lesson)=>{x.items[0].english='other';},
   (x:Lesson)=>{x.items[0].audio='generated/audio/other/0.mp3';},
   (x:Lesson)=>{x.items[0].id='other:0';},
   (x:Lesson)=>{x.items[0].referenceReview='practice_only';},
   (x:Lesson)=>{x.source='personal';},
  ]){
   const drift=copy(source);edit(drift);
   const subset=group.itemIds.map(id=>drift.items.find(x=>x.id===id)).filter(
    (x):x is NonNullable<typeof x>=>!!x);
   expect(guidedPhraseIntroduction(drift,group,subset)).toEqual([]);
  }
  expect(guidedPhraseIntroduction(source,{...group,id:'unlisted'},items)).toEqual([]);
  expect(guidedPhraseIntroduction(source,group,items.slice(1))).toEqual([]);
 });
});
