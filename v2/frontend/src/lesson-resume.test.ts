import {describe,expect,test} from 'vitest';
import type {Lesson} from './model';
import type {Progress} from './progress';
import {nextLessonResume} from './lesson-resume';

const vocabulary:Lesson={
  schemaVersion:1,id:'Conversation_1',title:'Greetings',kind:'vocabulary',source:'legacy',
  items:[
    {id:'Conversation_1:0',polish:'Dzień dobry',english:'Good morning'},
    {id:'Conversation_1:1',polish:'Dobry wieczór',english:'Good evening'},
    {id:'Conversation_1:2',polish:'Cześć',english:'Hi'},
    {id:'Conversation_1:3',polish:'Hej',english:'Hey'},
  ],
};
const attempt=(lastSeen='2026-10-23T00:00:00.000Z')=>({
  seen:1,remembered:1,needsPractice:0,lastSeen,
});
const numbers:Lesson={
  ...vocabulary,id:'numbers_1-20',title:'Numbers 1–20',
  items:Array.from({length:20},(_,i)=>({
    id:`numbers_1-20:${i}`,
    polish:({0:'Jeden',9:'Dziesięć',10:'Jedenaście',19:'Dwadścia'} as Record<number,string>)[i]??`Word ${i}`,
    english:`Number ${i+1}`,audio:`generated/audio/numbers_1-20/${i}.mp3`,
  })),
};
numbers.items[19].polish='Dwadzieścia';

describe('home Continue location from saved learner progress',()=>{
  test('starts at first unseen Learn card and moves forward after an honest attempt',()=>{
    expect(nextLessonResume(vocabulary,{},{})).toEqual({
      batchIndex:0,index:0,overallIndex:0,hasNewItem:true,
    });
    const progress:Progress={'Conversation_1:0':attempt(),'Conversation_1:1':attempt()};
    expect(nextLessonResume(vocabulary,progress,{})).toEqual({
      batchIndex:0,index:2,overallIndex:2,hasNewItem:true,
    });
    expect(progress['Conversation_1:0'].seen).toBe(1);
  });
  test('Listen and Speak alone never imply a Learn card is completed',()=>{
    const progress:Progress={
      'listen:Conversation_1:0':attempt(),
      'speak:Conversation_1:1':attempt(),
      'Conversation_1:2':attempt(),
    };
    expect(nextLessonResume(vocabulary,progress,{}).index).toBe(0);
  });
  test('all already-seen words explicitly restart for genuine revision without XP',()=>{
    const done=Object.fromEntries(vocabulary.items.map(item=>[item.id,attempt()]));
    expect(nextLessonResume(vocabulary,done,{})).toEqual({
      batchIndex:0,index:0,overallIndex:0,hasNewItem:false,
    });
  });
  test('Numbers 1–20 remains one lesson but resumes at the first new word within approved 1–10/11–20 sections',()=>{
    const completed=Object.fromEntries(numbers.items.slice(0,12).map(item=>[item.id,attempt()]));
    expect(nextLessonResume(numbers,completed,{})).toEqual({
      batchIndex:1,index:2,overallIndex:12,hasNewItem:true,
    });
    const all=Object.fromEntries(numbers.items.map(item=>[item.id,attempt()]));
    expect(nextLessonResume(numbers,all,{})).toEqual({
      batchIndex:0,index:0,overallIndex:0,hasNewItem:false,
    });
  });
  test('reading keeps the existing bounded saved-passage position',()=>{
    const reading:Lesson={...vocabulary,id:'reading_one',kind:'reading'};
    expect(nextLessonResume(reading,{}, {reading_one:2})).toEqual({
      batchIndex:0,index:2,overallIndex:2,hasNewItem:true,
    });
    expect(nextLessonResume(reading,{}, {reading_one:999}).index).toBe(3);
  });
  test('different or missing progress cannot move a personal lesson outside its cards',()=>{
    const personal:Lesson={...vocabulary,id:'mine',source:'personal',
      items:[{id:'mine:1',polish:'Dom',english:'Home'}]};
    expect(nextLessonResume(personal,{'Conversation_1:0':attempt()},{}).index).toBe(0);
  });
});
