import {describe,expect,it} from 'vitest';
import raw from '../../content/foundation-first-expressions-v1.json';
import legacy from '../../../docs/sets/Conversation_1.json';
import type {Lesson} from './model';
import {FIRST_EXPRESSION_GROUPS,availableStarterGroups,starterSessionItems,
  validateStarterManifest} from './foundation-first-expressions';

const source:Lesson={
 schemaVersion:1,id:'Conversation_1',title:'Greetings and everyday words',
 kind:'vocabulary',source:'legacy',
 items:legacy.cards.map((c,i)=>({
  id:'Conversation_1:'+i,polish:c.phrase,english:c.meaning,
  audio:'generated/audio/Conversation_1/'+i+'.mp3'
 }))
};
const copy=<T,>(x:T):T=>structuredClone(x);

describe('C-05 eight authentic source-backed expressions in three usable groups',()=>{
 it('retains eight exact original bilingual phrases and full original source IDs',()=>{
  const ids=FIRST_EXPRESSION_GROUPS.flatMap(group=>group.itemIds);
  expect(ids).toEqual(['Conversation_1:0','Conversation_1:2','Conversation_1:4',
   'Conversation_1:10','Conversation_1:8','Conversation_1:12','Conversation_1:14',
   'Conversation_1:15']);
  expect(new Set(ids).size).toBe(8);
  expect(legacy.cards[0].phrase).toBe('Dzień dobry');
  expect(legacy.cards[15].phrase).toBe('Nie');
  expect(validateStarterManifest(raw)).toEqual(FIRST_EXPRESSION_GROUPS);
  expect(FIRST_EXPRESSION_GROUPS.map(x=>x.itemIds.length)).toEqual([3,3,2]);
 });
 it('opens genuine original IDs in all three existing learning modes without copying items',()=>{
  const available=availableStarterGroups([source]);
  expect(available).toHaveLength(3);
  for(const group of available){
   for(const mode of ['learn','listen','speak'] as const){
    const selected=starterSessionItems(source,group,mode);
    expect(selected.map(x=>x.id)).toEqual(group.itemIds);
    expect(selected.every(x=>source.items.includes(x))).toBe(true);
    expect(selected.every(x=>x.audio?.startsWith('generated/audio/Conversation_1/'))).toBe(true);
    expect(selected.every(x=>x.referenceReview===undefined)).toBe(true);
   }
  }
 });
 it('fails closed when any original text, audio, reference or source kind changes',()=>{
  for(const itemId of FIRST_EXPRESSION_GROUPS.flatMap(x=>x.itemIds)){
   const wrong=copy(source);const entry=wrong.items.find(x=>x.id===itemId)!;
   entry.polish='Changed text';
   expect(availableStarterGroups([wrong]).some(x=>x.itemIds.includes(itemId))).toBe(false);
   const noAudio=copy(source);noAudio.items.find(x=>x.id===itemId)!.audio=undefined;
   expect(availableStarterGroups([noAudio]).some(x=>x.itemIds.includes(itemId))).toBe(false);
   const blocker=copy(source);blocker.items.find(x=>x.id===itemId)!.referenceReview='practice_only';
   expect(availableStarterGroups([blocker]).some(x=>x.itemIds.includes(itemId))).toBe(false);
  }
  expect(availableStarterGroups([{...source,source:'personal'}])).toEqual([]);
  expect(availableStarterGroups([{...source,kind:'reading'}])).toEqual([]);
  expect(availableStarterGroups([])).toEqual([]);
 });
 it('rejects manifest drift, duplicate ID, invented lesson, alternate Polish or hidden stage text',()=>{
  const bad=copy(raw);bad.groups[0].itemRefs[0].expectedPolish='Dzień Dobry';
  expect(()=>validateStarterManifest(bad)).toThrow();
  const swapped=copy(raw);swapped.groups[0].itemRefs[0].id='Conversation_1:15';
  expect(()=>validateStarterManifest(swapped)).toThrow();
  const unreviewed=copy(raw);unreviewed.groups[0].itemRefs[0].id='Conversation_1:25';
  expect(()=>validateStarterManifest(unreviewed)).toThrow();
  const extra=copy(raw);Object.assign(extra,{nativeCertified:true});
  expect(()=>validateStarterManifest(extra)).toThrow();
  const missing=copy(raw);missing.groups[1].itemRefs.pop();
  expect(()=>validateStarterManifest(missing)).toThrow();
 });
 it('never accepts a selected item from an unrelated lesson or arbitrary group',()=>{
  expect(starterSessionItems({...source,id:'personal_wrong'},FIRST_EXPRESSION_GROUPS[0],'learn')).toEqual([]);
  expect(starterSessionItems(source,{...FIRST_EXPRESSION_GROUPS[0],id:'wrong'},'listen')).toEqual([]);
 });
});
