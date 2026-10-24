import {describe,it,expect} from 'vitest';
import raw from '../../content/foundation-next-words-v1.json';
import conversation from '../../../docs/sets/Conversation_1.json';
import road from '../../../docs/sets/Road_Terminology.json';
import transit from '../../../docs/sets/Transit_1.json';
import restaurant from '../../../docs/sets/Conversation_-_restaurant.json';
import shopping from '../../../docs/sets/Conversation_-_shopping.json';
import gettingAround from '../../../docs/sets/Getting_Around_1.json';
import type {Lesson} from './model';
import {NEXT_WORD_GROUPS,availableNextWordGroups,nextWordSessionItems,
  validateNextWordManifest} from './foundation-next-words';
import {FIRST_EXPRESSION_GROUPS} from './foundation-first-expressions';

const sourceRows=[
 ['Conversation_1',conversation],
 ['Road_Terminology',road],
 ['Transit_1',transit],
 ['Conversation_-_restaurant',restaurant],
 ['Conversation_-_shopping',shopping],
 ['Getting_Around_1',gettingAround]
] as const;
const lessons=sourceRows.map(([id,data]):Lesson=>({
 schemaVersion:1,id,title:id,kind:'vocabulary',source:'legacy',
 items:data.cards.map((x,i)=>({id:id+':'+i,polish:x.phrase,english:x.meaning,
  audio:'generated/audio/'+encodeURIComponent(id)+'/'+i+'.mp3'}))
}));
const clone=<T,>(x:T):T=>structuredClone(x);
describe('C-06 source-recorded and source-validated everyday Polish',()=>{
 it('offers six meaningful ordered groups, 32 distinct original items, no fake stages',()=>{
  expect(NEXT_WORD_GROUPS).toHaveLength(6);
  expect(NEXT_WORD_GROUPS.map(g=>g.itemIds.length)).toEqual([5,6,6,5,5,5]);
  const ids=NEXT_WORD_GROUPS.flatMap(g=>g.itemIds);
  expect(ids).toHaveLength(32);
  expect(new Set(ids).size).toBe(32);
  expect(new Set([...ids,...FIRST_EXPRESSION_GROUPS.flatMap(g=>g.itemIds)]).size).toBe(40);
  expect(validateNextWordManifest(raw)).toEqual(NEXT_WORD_GROUPS);
 });
 it('anchors every word AND English gloss to the original separate, recorded whole phrase',()=>{
  expect(availableNextWordGroups(lessons)).toEqual(NEXT_WORD_GROUPS);
  for(const group of NEXT_WORD_GROUPS){
   const original=sourceRows.find(([id])=>id===group.lessonId)![1];
   const lesson=lessons.find(l=>l.id===group.lessonId)!;
   for(const id of group.itemIds){
    const index=Number(id.slice(group.lessonId.length+1));
    const actual=lesson.items.find(x=>x.id===id)!;
    expect(actual.polish).toEqual(original.cards[index].phrase);
    expect(actual.english).toEqual(original.cards[index].meaning);
    expect(actual.audio).toBe('generated/audio/'+encodeURIComponent(group.lessonId)+'/'+index+'.mp3');
   }
   for(const mode of ['learn','listen','speak'] as const){
    const selected=nextWordSessionItems(lesson,group,mode);
    expect(selected.map(x=>x.id)).toEqual(group.itemIds);
    expect(selected.every(x=>lesson.items.includes(x))).toBe(true);
   }
  }
 });
 it('suppresses only the affected group if text, translation, audio or reference is untrusted',()=>{
  const chosen=NEXT_WORD_GROUPS[2],source=lessons.find(l=>l.id===chosen.lessonId)!;
  const modifications=[
   (x:Lesson)=>{x.items.find(i=>i.id===chosen.itemIds[0])!.polish='not actual Polish';},
   (x:Lesson)=>{x.items.find(i=>i.id===chosen.itemIds[0])!.english='Different English';},
   (x:Lesson)=>{x.items.find(i=>i.id===chosen.itemIds[0])!.audio=undefined;},
   (x:Lesson)=>{x.items.find(i=>i.id===chosen.itemIds[0])!.audio='https://other-site/fake.mp3';},
   (x:Lesson)=>{x.items.find(i=>i.id===chosen.itemIds[0])!.referenceReview='practice_only';},
   (x:Lesson)=>{x.source='personal';},
   (x:Lesson)=>{x.kind='reading';}
  ];
  for(const mutate of modifications){
   const changed=clone(lessons);
   const target=changed.find(l=>l.id===source.id)!;
   mutate(target);
   expect(availableNextWordGroups(changed).some(g=>g.id===chosen.id)).toBe(false);
   expect(nextWordSessionItems(target,chosen,'learn')).toEqual([]);
   expect(availableNextWordGroups(changed)).toHaveLength(5);
  }
 });
 it('never opens a foreign item or fabricated group',()=>{
  const group=NEXT_WORD_GROUPS[0];
  const source=lessons[0];
  expect(nextWordSessionItems({...source,id:'other'},group,'learn')).toEqual([]);
  expect(nextWordSessionItems(source,{...group,id:'unknown'},'listen')).toEqual([]);
  expect(availableNextWordGroups([])).toEqual([]);
 });
 it('fails closed on modified group titles, source IDs, Polish, English, count and extra certification',()=>{
  const changed=clone(raw);changed.groups[0].itemRefs[0].expectedPolish='Zupełnie coś innego';
  expect(()=>validateNextWordManifest(changed)).toThrow();
  const mistranslated=clone(raw);mistranslated.groups[1].itemRefs[0].expectedEnglish='Wrong';
  expect(()=>validateNextWordManifest(mistranslated)).toThrow();
  const title=clone(raw);title.groups[0].title='Other topic';
  expect(()=>validateNextWordManifest(title)).toThrow();
  const wrongId=clone(raw);wrongId.groups[0].itemRefs[0].id='Conversation_1:25';
  expect(()=>validateNextWordManifest(wrongId)).toThrow();
  const missing=clone(raw);missing.groups[0].itemRefs.pop();
  expect(()=>validateNextWordManifest(missing)).toThrow();
  const extra=clone(raw);Object.assign(extra,{nativeApproved:true});
  expect(()=>validateNextWordManifest(extra)).toThrow();
 });
});
