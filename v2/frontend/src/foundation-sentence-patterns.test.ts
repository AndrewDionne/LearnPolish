import {describe,expect,it} from 'vitest';
import raw from '../../content/foundation-sentence-patterns-v1.json';
import requests from '../../../docs/sets/Conversation_-_restaurant.json';
import shopping from '../../../docs/sets/Conversation_-_shopping.json';
import travel from '../../../docs/sets/Getting_Around_1.json';
import health from '../../../docs/sets/Emergencies_and_Health.json';
import conversation from '../../../docs/sets/Conversation_1.json';
import food from '../../../docs/sets/Food_and_Dinning.json';
import road from '../../../docs/sets/Road_Terminology.json';
import type {Lesson} from './model';
import {SENTENCE_PATTERN_SOURCE,availableSentencePatterns,validateSentencePatternSource} from './foundation-sentence-patterns';

const originals=[
 ['Conversation_-_restaurant',requests],
 ['Conversation_-_shopping',shopping],
 ['Getting_Around_1',travel],
 ['Emergencies_and_Health',health],
 ['Conversation_1',conversation],
 ['Food_and_Dinning',food],
 ['Road_Terminology',road],
] as const;
const lessons:Lesson[]=originals.map(([id,data])=>({
 schemaVersion:1,id,title:id,kind:'vocabulary',source:'legacy',
 items:data.cards.map((card,index)=>({
  id:id+':'+index,polish:card.phrase,english:card.meaning,
  audio:'generated/audio/'+encodeURIComponent(id)+'/'+index+'.mp3'
 }))
}));
const copy=<T,>(value:T):T=>structuredClone(value);

describe('C-13 prerequisite-complete sentence patterns with 28 original Polish recordings',()=>{
 it('declares seven progressive patterns and 28 exact full original recordings',()=>{
  expect(validateSentencePatternSource(raw)).toEqual(SENTENCE_PATTERN_SOURCE);
  expect(SENTENCE_PATTERN_SOURCE.map(group=>group.id)).toEqual([
   'requests','where','permission','prices','yes-no-questions','negative','one-two'
  ]);
  expect(SENTENCE_PATTERN_SOURCE.map(group=>group.examples.length)).toEqual([4,5,4,3,4,4,4]);
  const all=SENTENCE_PATTERN_SOURCE.flatMap(group=>group.examples);
  expect(new Set(all.map(x=>x.sourceLesson+':'+x.index)).size).toBe(28);
 });
 it('pins each full Polish sentence AND original English meaning AND original word audio',()=>{
  const available=availableSentencePatterns(lessons);
  expect(available).toHaveLength(7);
  for(const group of available){
   expect(group.examples.length).toBeGreaterThanOrEqual(3);
   for(const example of group.examples){
    const item=lessons.flatMap(l=>l.items).find(x=>x.id===example.itemId);
    expect(item).toBeDefined();
    expect(example.polish).toBe(item?.polish);
    expect(example.english).toBe(item?.english);
    expect(example.audio).toBe(item?.audio);
    expect(example.polish.split(example.focus)).toHaveLength(2);
   }
  }
  expect(available[0].examples[0].polish).toBe('Poproszę wodę');
  expect(available[1].examples[0].polish).toBe('Gdzie jest przystanek?');
  expect(available[2].examples[0].polish).toBe('Czy mogę zapłacić kartą?');
  expect(available[3].examples[0].polish).toBe('Ile to kosztuje?');
  expect(available[4].examples[0].polish).toBe('Czy to pociąg do Warszawy?');
  expect(available[5].examples[0].polish).toBe('Nie rozumiem');
  expect(available[6].examples[0].polish).toBe('Jeden bilet, proszę');
 });
 it('withholds affected group on any mismatched source text, translation, recording or blocker',()=>{
  for(const mutate of [
   (l:Lesson)=>{l.items[2].polish='Bad';},
   (l:Lesson)=>{l.items[2].english='Wrong translation';},
   (l:Lesson)=>{l.items[2].audio=undefined;},
   (l:Lesson)=>{l.items[2].audio='generated/audio/Conversation_-_restaurant/0.mp3';},
   (l:Lesson)=>{l.items[2].referenceReview='practice_only';},
   (l:Lesson)=>{l.source='personal';},
   (l:Lesson)=>{l.kind='reading';}
  ]){
   const changed=copy(lessons);
   mutate(changed[0]);
   expect(availableSentencePatterns(changed).some(g=>g.id==='requests')).toBe(false);
   expect(availableSentencePatterns(changed)).toHaveLength(6);
  }
  expect(availableSentencePatterns([])).toHaveLength(0);
 });
 it('does not silently accept fake certification, reordered examples or extra rows',()=>{
  const fake=copy(raw);
  Object.assign(fake,{nativePolishReviewed:true});
  expect(()=>validateSentencePatternSource(fake)).toThrow();
  const missing=copy(raw);
  missing.groups[0].examples.pop();
  expect(()=>validateSentencePatternSource(missing)).toThrow();
  const duplicate=copy(raw);
  duplicate.groups[0].examples[1]=copy(duplicate.groups[0].examples[0]);
  expect(()=>validateSentencePatternSource(duplicate)).toThrow();
  const changed=copy(raw);
  changed.groups[0].examples[0].focus='kawa';
  expect(()=>validateSentencePatternSource(changed)).toThrow();
  const moved=copy(raw);
  moved.groups[1].id='wrong';
  expect(()=>validateSentencePatternSource(moved)).toThrow();
 });
});
