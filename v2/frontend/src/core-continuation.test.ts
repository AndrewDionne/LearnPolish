import {describe,expect,test} from 'vitest';
import type {Lesson} from './model';
import type {Progress} from './progress';
import catalog from '../../content/library-catalog.json';
import {CORE_CONTINUE_KEY,parseCoreContinueId,resolveCourseContinuation} from './core-continuation';

const builtins:Lesson[]=catalog.lessons.map(x=>({
  schemaVersion:1,id:x.id,title:x.title,kind:x.curriculum.stage==='learning'?'reading':'vocabulary',
  source:'legacy',curriculum:x.curriculum as Lesson['curriculum'],
  items:[{id:x.id+':0',polish:'Cześć',english:'Hello'}],
}));
const personal:Lesson={schemaVersion:1,id:'personal_custom',title:'Family words',
  kind:'vocabulary',source:'personal',items:[{id:'personal_custom:0',polish:'Cześć',english:'Hello'}]};
const record=(seenAt:string)=>({seen:1,remembered:1,needsPractice:0,lastSeen:seenAt});

describe('A-02 independent core vs recent practice continuity',()=>{
  test('preserves explicit core selection across personal and optional recent practice',()=>{
    const all=[...builtins,personal];
    expect(resolveCourseContinuation(all,{},'Conversation_1',personal.id)).toMatchObject({
      lesson:{id:'Conversation_1'},origin:'selected'});
    expect(resolveCourseContinuation(all,{},'Basic_01R','Countries_of_the_World')).toMatchObject({
      lesson:{id:'Basic_01R'},origin:'selected'});
    // Explicit personal/optional IDs must not be accepted as core positions.
    expect(resolveCourseContinuation(all,{},personal.id,personal.id)).toMatchObject({
      lesson:{id:'Conversation_1'},origin:'start'});
    expect(resolveCourseContinuation(all,{},'Countries_of_the_World',personal.id).origin).toBe('start');
  });

  test('migrates legacy recent core and then most-recent actual core activity',()=>{
    expect(resolveCourseContinuation(builtins,{},null,'numbers_1-20')).toMatchObject({
      lesson:{id:'numbers_1-20'},origin:'recent-core'});
    const progress:Progress={
      'Conversation_1:0':record('2026-10-20T12:00:00Z'),
      'listen:Basic_01R:0':record('2026-10-22T12:00:00Z'),
      'personal_custom:0':record('2026-10-23T12:00:00Z'),
      'Countries_of_the_World:0':record('2026-10-23T13:00:00Z'),
    };
    expect(resolveCourseContinuation([...builtins,personal],progress,null,personal.id))
      .toMatchObject({lesson:{id:'Basic_01R'},origin:'practice-history'});
    expect(resolveCourseContinuation(builtins,progress,null,'missing'))
      .toMatchObject({lesson:{id:'Basic_01R'},origin:'practice-history'});
  });

  test('begins at real greeting source and degrades honestly if catalog absent',()=>{
    expect(resolveCourseContinuation([...builtins,personal],{},null,null))
      .toMatchObject({lesson:{id:'Conversation_1'},origin:'start'});
    expect(resolveCourseContinuation([personal],{},null,null)).toEqual({
      lesson:null,origin:'unavailable'});
    expect(resolveCourseContinuation([],{},'Conversation_1','Conversation_1').lesson).toBeNull();
  });

  test('uses sound/number sessions without deriving course placement from XP',()=>{
    const progress:Progress={'numbers_1-20:0':record('2026-10-23T12:00:00Z')};
    const a=resolveCourseContinuation(builtins,progress,null,'speak_swietokrzyska');
    expect(a.lesson?.id).toBe('numbers_1-20');
    expect(a.origin).toBe('practice-history');
    expect(CORE_CONTINUE_KEY).toBe('ptp-v2-core-continue');
  });

  test('parses only plain bounded core cursor identifiers',()=>{
    expect(parseCoreContinueId('Conversation_1')).toBe('Conversation_1');
    expect(parseCoreContinueId(null)).toBeNull();
    for(const raw of ['','personal_custom','../unsafe','x'.repeat(141),'\u0000'])
      expect(parseCoreContinueId(raw)).toBeNull();
  });
});
