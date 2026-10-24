import {describe,expect,it} from 'vitest';
import definitions from '../../content/sound-contrasts.json';
import raw from '../../content/sound-listening-v1.json';
import type {Lesson} from './model';
import {SOUND_LISTENING_PLAN,soundListeningCards,validateSoundListeningPlan,focusedPolishParts} from './sound-listening';

const soundLessons:Lesson[]=definitions.map(def=>({
 schemaVersion:1,id:def.id,title:def.title,kind:'sounds',source:'curated',
 items:def.groups.flatMap(g=>g.examples.map((e,i)=>({
   id:def.id+':'+g.id+':'+i,polish:e.expected,english:'Original meaning',
   audio:'generated/audio/'+encodeURIComponent(e.set)+'/'+e.index+'.mp3',
   soundGroupId:g.id,soundFocus:e.focus
 }))),
 soundGroups:def.groups.map(g=>({
   id:g.id,label:g.label,ipa:g.ipa,hint:g.hint,
   itemIds:g.examples.map((_,i)=>def.id+':'+g.id+':'+i)
 }))
}));
const clone=<T,>(x:T):T=>structuredClone(x);

describe('C-09 active sound recognition from existing whole-word examples',()=>{
 it('covers five actual sound lessons and 25 distinct stable audio-backed examples',()=>{
  expect(validateSoundListeningPlan(raw)).toEqual(SOUND_LISTENING_PLAN);
  expect(SOUND_LISTENING_PLAN.map(p=>p.questions.length)).toEqual([6,5,6,4,4]);
  const all=SOUND_LISTENING_PLAN.flatMap(p=>p.questions.map(q=>q.itemId));
  expect(new Set(all).size).toBe(25);
  for(const lesson of soundLessons){
   const cards=soundListeningCards(lesson);
   const plan=SOUND_LISTENING_PLAN.find(p=>p.lessonId===lesson.id)!;
   expect(cards.length).toBe(plan.questions.length);
   expect(cards.map(c=>c.item.id)).toEqual(plan.questions.map(c=>c.itemId));
   expect(cards.every(c=>lesson.items.includes(c.item))).toBe(true);
   expect(cards.every(c=>!!c.item.audio && c.item.audio.startsWith('generated/audio/'))).toBe(true);
   expect(new Set(cards.map(c=>c.groupId)).size).toBe(lesson.soundGroups?.length);
   expect(cards[0].item.id).toBe(lesson.soundGroups![0].itemIds[0]);
  }
  // Sześć also contains the softer ś sound; avoid ambiguous unprompted quiz.
  expect(SOUND_LISTENING_PLAN.flatMap(x=>x.questions.map(y=>y.itemId)))
    .not.toContain('contrast_s_sz_sie:sz:0');
 });
 it('preserves original grapheme inside its whole recorded Polish word',()=>{
  for(const l of soundLessons)for(const card of soundListeningCards(l)){
   const parts=focusedPolishParts(card.item)!;
   expect(parts.before+parts.focus+parts.after).toBe(card.item.polish);
   expect(parts.focus).toBe(card.item.soundFocus);
  }
 });
 it('fails closed if any source recording, grapheme, Polish, group or status is altered',()=>{
  for(const mutate of [
   (l:Lesson)=>{l.items[0].polish='changed';},
   (l:Lesson)=>{l.items[0].audio='https://example.test/fake.mp3';},
   (l:Lesson)=>{l.items[0].audio=undefined;},
   (l:Lesson)=>{l.items[0].referenceReview='practice_only';},
   (l:Lesson)=>{l.items[0].soundFocus='z';},
   (l:Lesson)=>{l.items[0].soundGroupId='not-the-group';},
   (l:Lesson)=>{l.source='personal';},
   (l:Lesson)=>{l.kind='vocabulary';}
  ]){
   const changed=clone(soundLessons[0]);
   mutate(changed);
   expect(soundListeningCards(changed)).toEqual([]);
  }
  expect(soundListeningCards({...soundLessons[0],soundGroups:undefined})).toEqual([]);
  expect(soundListeningCards({...soundLessons[0],id:'unknown'})).toEqual([]);
 });
 it('rejects edited review status, duplicated IDs, missing prompts and ungrounded sounds',()=>{
  const modified=clone(raw);
  modified.lessons[0].questions[0].expectedPolish='unrelated spelling';
  expect(()=>validateSoundListeningPlan(modified)).toThrow();
  const duplicate=clone(raw);
  duplicate.lessons[0].questions[1].itemId=duplicate.lessons[0].questions[0].itemId;
  expect(()=>validateSoundListeningPlan(duplicate)).toThrow();
  const absent=clone(raw);
  absent.lessons[0].questions.pop();
  expect(()=>validateSoundListeningPlan(absent)).toThrow();
  const fake=clone(raw);
  Object.assign(fake,{independentNativeVerified:true});
  expect(()=>validateSoundListeningPlan(fake)).toThrow();
  const certification=clone(raw);
  certification.status='native-approved';
  expect(()=>validateSoundListeningPlan(certification)).toThrow();
 });
});
