import {describe,expect,it} from 'vitest';
import raw from '../../content/journey1-foundation-guide-v1.json';
import catalog from '../../content/library-catalog.json';
import type {Lesson} from './model';
import {JOURNEY1_GUIDE,availableJourney1Guide,validateJourney1Guide}
  from './journey1-guide';
import {TOURIST_UNITS} from './tourist-units';
import {CORE_JOURNEY_PLACEMENTS,nextCoreLesson} from './core-journey';

const all=catalog.lessons.map(x=>({
 schemaVersion:1,id:x.id,title:x.title,
 kind:(x.curriculum.stage==='learning'?'reading':
       x.id.startsWith('contrast_')?'sounds':'vocabulary'),
 source:x.id.startsWith('contrast_')?'curated':'legacy',
 curriculum:x.curriculum,items:[{id:x.id+':0',polish:'Dzień dobry',english:'Hello'}]
})) as Lesson[];
const copy=<T,>(data:T):T=>structuredClone(data);

describe('C-01 80/20 foundations-first source-backed Journey 1 guide',()=>{
 it('sets 80% of guided session slots to actual foundations, not proficiency or estimated time',()=>{
  expect(JOURNEY1_GUIDE).toHaveLength(20);
  expect(JOURNEY1_GUIDE.filter(x=>x.type==='foundation')).toHaveLength(16);
  expect(JOURNEY1_GUIDE.filter(x=>x.type==='application')).toHaveLength(4);
  expect(16/20).toBe(0.8);
  expect(raw.allocation.metric).toBe('guided_session_slots_not_minutes_or_mastery');
  expect(JOURNEY1_GUIDE.filter(x=>x.type==='application').map(x=>x.type==='application'&&x.unitId))
   .toEqual(['T01','T03','T05','T08']);
  expect(validateJourney1Guide(raw)).toEqual(JOURNEY1_GUIDE);
 });
 it('links only to existing, unique lessons and visible original scene IDs',()=>{
  const source=JOURNEY1_GUIDE.filter(x=>x.type==='foundation');
  expect(source.every(x=>x.type==='foundation'&&catalog.lessons.some(l=>l.id===x.lessonId))).toBe(true);
  expect(new Set(source.map(x=>x.type==='foundation'&&x.lessonId)).size).toBe(16);
  expect(source.find(x=>x.type==='foundation'&&x.lessonId==='numbers_1-20')).toBeDefined();
  expect(availableJourney1Guide(all,TOURIST_UNITS)).toHaveLength(20);
  expect(availableJourney1Guide(all,TOURIST_UNITS.slice(0,2))).toHaveLength(17);
  expect(availableJourney1Guide(all.filter(l=>l.id!=='numbers_1-20'),TOURIST_UNITS)).toHaveLength(19);
  // Guide launches entire existing numbered lesson, never manufactured 1–8/9–20 subsets.
  expect(source.some(x=>x.type==='foundation'&&'itemIds' in x)).toBe(false);
  expect(CORE_JOURNEY_PLACEMENTS).toHaveLength(21);
  expect(CORE_JOURNEY_PLACEMENTS.filter(x=>x.journey===1)).toHaveLength(19);
  const order=CORE_JOURNEY_PLACEMENTS.filter(x=>x.journey===1)
   .sort((a,b)=>['beginning','middle','end'].indexOf(a.position)-
                ['beginning','middle','end'].indexOf(b.position)||a.order-b.order);
  expect(order.slice(0,16).map(x=>x.lessonId))
   .toEqual(source.map(x=>x.type==='foundation'?x.lessonId:''));
  expect(nextCoreLesson(all,'Conversation_1')?.id).toBe('contrast_l_lstroked');
  expect(nextCoreLesson(all,'numbers_1-20')?.id).toBe('Basic_01R');
 });
 it('fails closed on wrong ratio, unexpected tiers, changed source and invented applications',()=>{
  for(const mutate of [
   (v:typeof raw)=>{v.allocation.foundationSharePercent=70;},
   (v:typeof raw)=>{v.allocation.metric='proficiency_earned';},
   (v:typeof raw)=>{v.steps.pop();},
   (v:typeof raw)=>{v.steps[0].id='F02';},
   (v:typeof raw)=>{v.steps[3].type='application';},
   (v:typeof raw)=>{v.steps[1].lessonId=v.steps[0].lessonId;},
   (v:typeof raw)=>{v.steps[5].lessonId='personal_wrong';},
   (v:typeof raw)=>{v.steps[5].lessonId='speak_swietokrzyska';},
   (v:typeof raw)=>{v.steps[10].group='end';},
   (v:typeof raw)=>{v.steps[16].unitId='T09';},
   (v:typeof raw)=>{Object.assign(v.steps[0],{itemIds:['Conversation_1:0']});},
  ]){
   const value=copy(raw);mutate(value);
   expect(()=>validateJourney1Guide(value)).toThrow();
  }
 });
 it('does not count personal lessons or silent trial data as approved guide material',()=>{
  const fake=copy(all.find(x=>x.id==='Conversation_1')!);
  fake.source='personal';
  expect(availableJourney1Guide(all.map(x=>x.id===fake.id?fake:x),TOURIST_UNITS))
   .toHaveLength(19);
  const empty=copy(all.find(x=>x.id==='Road_Terminology')!);
  empty.items=[];
  expect(availableJourney1Guide(all.map(x=>x.id===empty.id?empty:x),TOURIST_UNITS))
   .toHaveLength(19);
 });
});
