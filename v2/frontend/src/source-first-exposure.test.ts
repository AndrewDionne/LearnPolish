import {describe,expect,it} from 'vitest';
import type {Lesson} from './model';
import {originalLibraryListenIntroduction,touristListenIntroduction} from './source-first-exposure';
import {TOURIST_UNITS} from './tourist-units';
import conversation from '../../../docs/sets/Conversation_1.json';
import shopping from '../../../docs/sets/Conversation_-_shopping.json';
import restaurant from '../../../docs/sets/Conversation_-_restaurant.json';
import food from '../../../docs/sets/Food_and_Dinning.json';
import getting from '../../../docs/sets/Getting_Around_1.json';
import transit from '../../../docs/sets/Transit_1.json';
import emergencies from '../../../docs/sets/Emergencies_and_Health.json';
import basicReading from '../../../docs/sets/Basic_01R.json';
import groceryReading from '../../../docs/sets/Grocery_store_very_basic_shopping.json';
import numbers from '../../../docs/sets/numbers_1-20.json';
const cardSources=[['Conversation_1',conversation],['Conversation_-_shopping',shopping],
 ['Conversation_-_restaurant',restaurant],['Food_and_Dinning',food],
 ['Getting_Around_1',getting],['Transit_1',transit],
 ['Emergencies_and_Health',emergencies],['numbers_1-20',numbers]] as const;
const readings=[['Basic_01R',basicReading],['Grocery_store_very_basic_shopping',groceryReading]] as const;
const asLesson=(id:string,kind:'vocabulary'|'reading',data:{cards?:readonly {phrase:string;meaning:string}[];passages?:readonly {polish:string;english:string}[]}):Lesson=>({
 schemaVersion:1,source:'legacy',kind,id,title:id,
 items:(kind==='reading'?data.passages!:data.cards!).map((row,i)=>{
  const pol=kind==='reading'?(row as {polish:string}).polish:(row as {phrase:string}).phrase;
  const eng=kind==='reading'?(row as {english:string}).english:(row as {meaning:string}).meaning;
  return {id:id+':'+i,polish:pol,english:eng,
   audio:'generated/audio/'+encodeURIComponent(id)+'/'+i+'.mp3'};
 })
});
const lessons:Lesson[]=[
 ...cardSources.map(([id,data])=>asLesson(id,'vocabulary',data)),
 ...readings.map(([id,data])=>asLesson(id,'reading',data))
];
const get=(id:string)=>lessons.find(x=>x.id===id)!;
const copy=<T,>(v:T)=>structuredClone(v);

describe('C-16C honest whole-recording instruction for original Library and source-only tourists',()=>{
 it('covers the original 172 basic items across all seven Library sets with unmodified whole audio',()=>{
  const intro=cardSources.slice(0,7).map(([id])=>originalLibraryListenIntroduction(get(id),get(id).items));
  expect(intro.map(x=>x.length)).toEqual([26,25,25,25,26,20,25]);
  expect(intro.flat()).toHaveLength(172);
  for(const row of intro.flat()){
   expect(row.audio).toBe('generated/audio/'+encodeURIComponent(row.id.split(':')[0])+'/'+row.id.split(':')[1]+'.mp3');
   expect(row.english.length).toBeGreaterThan(0);
  }
  expect(intro[1][0].teachingCue).toContain('Ile asks how much');
  // 15 curated first-sentence cues, but no blanket grammatical/native approval.
  expect(intro.flat().filter(x=>x.teachingCue)).toHaveLength(15);
 });
 it('tourist Listen turns pre-teach exact original recorded subset before selected source checks',()=>{
  const t01=TOURIST_UNITS[0].steps[0],r01=get(t01.lessonId);
  const listen01=touristListenIntroduction(r01,t01,r01.items.filter(x=>t01.itemIds.includes(x.id)));
  expect(listen01.map(x=>x.polish)).toEqual(['Cześć! Jak się masz?','Dziękuję, mam się dobrze.']);
  expect(listen01[0].teachingCue).toContain('informal');
  const t03=TOURIST_UNITS[2].steps[0],n=get(t03.lessonId);
  const listen03=touristListenIntroduction(n,t03,n.items.filter(x=>t03.itemIds.includes(x.id)));
  expect(listen03).toHaveLength(10);
  expect(listen03[0].polish).toBe('Jeden');
  expect(listen03[9].polish).toBe('Dziesięć');
  const t04=TOURIST_UNITS[3].steps[0],l=get(t04.lessonId);
  expect(touristListenIntroduction(l,t04,l.items.filter(x=>t04.itemIds.includes(x.id)))).toHaveLength(9);
  const t05=TOURIST_UNITS[4].steps[0],g=get(t05.lessonId);
  const listen05=touristListenIntroduction(g,t05,g.items.filter(x=>t05.itemIds.includes(x.id)));
  expect(listen05).toHaveLength(6);
  expect(listen05[1].teachingCue).toContain('Kilogram jabłek');
 });
 it('fails shut on altered Polish, English, original MP3, blocked reference or foreign source',()=>{
  const source=get('Conversation_-_shopping');
  const selected=source.items.slice(0,3);
  expect(originalLibraryListenIntroduction(source,selected)).toHaveLength(3);
  for(const mutate of [
   (l:Lesson)=>{l.items[0].polish='tampered';},
   (l:Lesson)=>{l.items[0].english='tampered';},
   (l:Lesson)=>{l.items[0].audio='generated/audio/fake/0.mp3';},
   (l:Lesson)=>{l.items[0].referenceReview='practice_only';},
   (l:Lesson)=>{l.items[3].english='tampered';},
   (l:Lesson)=>{l.items.pop();},
   (l:Lesson)=>{l.source='personal';}
  ]){
   const changed=copy(source);mutate(changed);
   const subset=selected.map(x=>changed.items.find(y=>y.id===x.id)??x);
   expect(originalLibraryListenIntroduction(changed,subset)).toEqual([]);
  }
  expect(originalLibraryListenIntroduction(source,[...selected].reverse())).toEqual([]);
  const t01=TOURIST_UNITS[0].steps[0],read=get(t01.lessonId);
  const subset=read.items.filter(x=>t01.itemIds.includes(x.id));
  expect(touristListenIntroduction(read,{...t01,mode:'speak'},subset)).toEqual([]);
  expect(touristListenIntroduction(read,{...t01,itemIds:['fake:0',t01.itemIds[1]]},subset)).toEqual([]);
  expect(touristListenIntroduction(read,t01,[...subset].reverse())).toEqual([]);
 });
});
