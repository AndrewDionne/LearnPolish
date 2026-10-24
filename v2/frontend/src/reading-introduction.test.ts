import {describe,expect,it} from 'vitest';
import type {Lesson} from './model';
import {READING_INTRO_COUNTS,recordedReadingIntroduction,firstDialogueTeachingCue} from './reading-introduction';
import basic from '../../../docs/sets/Basic_01R.json';
import grocery from '../../../docs/sets/Grocery_store_very_basic_shopping.json';
import clothes from '../../../docs/sets/H_M_clothes_shop_trying_on_a_T-shirt.json';
import tram from '../../../docs/sets/On_the_tram_talking_to_another_passenger.json';
import driver from '../../../docs/sets/Asking_the_tram_driver_for_directions.json';
import museum from '../../../docs/sets/Museum_buying_tickets_and_basic_info.json';
const sources=[
 ['Basic_01R',basic],
 ['Grocery_store_very_basic_shopping',grocery],
 ['H_M_clothes_shop_trying_on_a_T-shirt',clothes],
 ['On_the_tram_talking_to_another_passenger',tram],
 ['Asking_the_tram_driver_for_directions',driver],
 ['Museum_buying_tickets_and_basic_info',museum],
] as const;
const lessons:Lesson[]=sources.map(([id,source])=>({
 schemaVersion:1,id,kind:'reading',source:'legacy',title:id,
 items:source.passages.map((line,i)=>({
  id:id+':'+i,polish:line.polish,english:line.english,
  audio:'generated/audio/'+encodeURIComponent(id)+'/'+i+'.mp3'
 }))
}));
const copy=<T,>(x:T):T=>structuredClone(x);

describe('C-14 reading source turn introductions before comprehension',()=>{
 it('covers all six complete original reading dialogues and 51 exact unchanged recorded utterances',()=>{
  expect(Object.keys(READING_INTRO_COUNTS)).toHaveLength(6);
  const introductions=lessons.map(recordedReadingIntroduction);
  expect(introductions.map(rows=>rows.length)).toEqual([6,9,10,9,8,9]);
  expect(introductions.flat()).toHaveLength(51);
  for(const [i,lesson] of lessons.entries()){
   const original=sources[i][1].passages;
   for(const [j,turn] of introductions[i].entries()){
    expect(turn.id).toBe(lesson.id+':'+j);
    expect(turn.polish).toBe(original[j].polish);
    expect(turn.english).toBe(original[j].english);
    expect(turn.audio).toBe('generated/audio/'+encodeURIComponent(lesson.id)+'/'+j+'.mp3');
   }
  }
 });
 it('preserves the original recorded phrase and translation for beginner and later dialogues',()=>{
  const beginning=recordedReadingIntroduction(lessons[0]);
  expect(beginning[0].polish).toBe('Cześć! Jak się masz?');
  expect(beginning[0].english).toBe('Hi! How are you?');
  const grocery=recordedReadingIntroduction(lessons[1]);
  expect(grocery[2].polish).toBe('Jakie jabłka pan lubi? Czerwone czy zielone?');
  const directions=recordedReadingIntroduction(lessons[4]);
  expect(directions[3].polish).toBe('Na którym przystanku powinienem wysiąść?');
 });
 it('C-15 teaches six distinct introductory grammar cues anchored to the original complete recording',()=>{
  const beginning=recordedReadingIntroduction(lessons[0]);
  expect(beginning.map(row=>row.teachingCue?.length>40)).toEqual([true,true,true,true,true,true]);
  expect(beginning[0].teachingCue).toContain('Jak się masz?');
  expect(beginning[2].teachingCue).toContain('masz');
  expect(beginning[3].teachingCue).toContain('Mam na imię');
  expect(beginning[5].teachingCue).toContain('Nie before rozumiem');
  expect(firstDialogueTeachingCue('Basic_01R',0,'Cześć! Jak się masz?')).toBe(beginning[0].teachingCue);
  expect(firstDialogueTeachingCue('Basic_01R',0,'changed line')).toBeUndefined();
  expect(firstDialogueTeachingCue('Basic_01R',6,'anything')).toBeUndefined();
  expect(recordedReadingIntroduction(lessons[1]).every(row=>row.teachingCue===undefined)).toBe(true);
  const drift=copy(lessons[0]);drift.items[0].polish='Changed source line';
  expect(recordedReadingIntroduction(drift)[0].teachingCue).toBeUndefined();
  expect(recordedReadingIntroduction(drift)[1].teachingCue).toBeTruthy();
 });
 it('withholds only the extra preparation if original full-recording/audio/meaning is missing or protected',()=>{
  for(const edit of [
   (l:Lesson)=>{l.items[0].polish='';},
   (l:Lesson)=>{l.items[0].english='';},
   (l:Lesson)=>{l.items[0].audio='generated/audio/Basic_01R/1.mp3';},
   (l:Lesson)=>{l.items[0].audio=undefined;},
   (l:Lesson)=>{l.items[0].id='fake:0';},
   (l:Lesson)=>{l.items[0].referenceReview='practice_only';},
   (l:Lesson)=>{l.source='personal';},
   (l:Lesson)=>{l.kind='vocabulary';},
   (l:Lesson)=>{l.items.pop();}
  ]){
   const altered=copy(lessons[0]);edit(altered);
   expect(recordedReadingIntroduction(altered)).toEqual([]);
   expect(recordedReadingIntroduction(lessons[1])).toHaveLength(9);
  }
  expect(recordedReadingIntroduction({...lessons[0],id:'new_unreviewed_reading'})).toEqual([]);
 });
});
