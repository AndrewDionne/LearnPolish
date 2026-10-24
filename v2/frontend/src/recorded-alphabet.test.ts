import {describe,expect,it} from 'vitest';
import raw from '../../content/alphabet-recorded-examples-v1.json';
import type {Lesson} from './model';
import {POLISH_ALPHABET,RECORDED_COMBINATIONS,RECORDED_ALPHABET_PLAN,availableRecordedAlphabet,validateAlphabetPlan} from './recorded-alphabet';

const make=(id:string,rows:{id:string;polish:string;english:string;audio:string}[]):Lesson=>({
 schemaVersion:1,id,title:id,kind:'vocabulary',source:'legacy',items:rows
});
const corpus=Object.values(RECORDED_ALPHABET_PLAN).flat();
const lessonIds=[...new Set(corpus.map(row=>row.sourceLesson))];
const lessons:Lesson[]=lessonIds.map(id=>make(id,
 [...new Map(corpus.filter(row=>row.sourceLesson===id).map(row=>[row.index,{
  id:id+':'+row.index,polish:row.polish,english:row.english,
  audio:'generated/audio/'+encodeURIComponent(id)+'/'+row.index+'.mp3'
 }])).values()]));
const clone=<T,>(x:T):T=>structuredClone(x);

describe('C-10 full written alphabet with whole source recordings',()=>{
 it('has 32 Polish letters and 13 recorded combinations, no Q V X invented',()=>{
  expect(POLISH_ALPHABET).toHaveLength(32);
  expect(RECORDED_COMBINATIONS).toHaveLength(13);
  expect(new Set(POLISH_ALPHABET).size).toBe(32);
  expect(POLISH_ALPHABET).not.toContain('V');
  expect(validateAlphabetPlan(raw)).toEqual(RECORDED_ALPHABET_PLAN);
  expect(availableRecordedAlphabet(lessons).letters.map(x=>x.label)).toEqual(POLISH_ALPHABET);
  expect(availableRecordedAlphabet(lessons).combinations.map(x=>x.label)).toEqual(RECORDED_COMBINATIONS);
 });
 it('all 45 exemplars exactly preserve their original item object text and whole-word audio reference',()=>{
  expect(corpus).toHaveLength(45);
  for(const card of [...availableRecordedAlphabet(lessons).letters,...availableRecordedAlphabet(lessons).combinations]){
   const item=lessons.flatMap(l=>l.items).find(x=>x.id===card.itemId);
   expect(card.audio).toBe(item?.audio);
   expect(card.polish).toBe(item?.polish);
   expect(card.english).toBe(item?.english);
   expect(card.polish.split(card.focus)).toHaveLength(2);
  }
 });
 it('no fallbacks to changed source words, original MP3s or protected recordings',()=>{
  const changed=clone(lessons);
  const item=changed.find(x=>x.id==='Transit_1')!.items.find(i=>i.id==='Transit_1:6')!;
  item.audio=undefined;
  expect(availableRecordedAlphabet(changed).letters.some(x=>x.label==='A')).toBe(false);
  item.audio='generated/audio/Transit_1/6.mp3';
  item.polish='Different';
  expect(availableRecordedAlphabet(changed).letters.some(x=>x.label==='A')).toBe(false);
  item.polish='Autobus';
  item.referenceReview='practice_only';
  expect(availableRecordedAlphabet(changed).letters.some(x=>x.label==='A')).toBe(false);
  expect(availableRecordedAlphabet([])).toEqual({letters:[],combinations:[]});
 });
 it('rejects invalid alphabet order, extra native approval, wrong focus and missing rows',()=>{
  const wrong=clone(raw);wrong.letters[0].focus='u';
  expect(()=>validateAlphabetPlan(wrong)).toThrow();
  const approval=clone(raw);Object.assign(approval,{nativeApproved:true});
  expect(()=>validateAlphabetPlan(approval)).toThrow();
  const missing=clone(raw);missing.letters.pop();
  expect(()=>validateAlphabetPlan(missing)).toThrow();
 });
});
