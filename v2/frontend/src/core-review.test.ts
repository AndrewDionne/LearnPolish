import {describe,expect,it} from 'vitest';
import type {Lesson} from './model';
import type {ReviewSchedule} from './review';
import {recordReview,dueItems} from './review';
import {dueLaneCount,nextCoreReviewRunStep,partitionDueReviews,startCoreReviewRun} from './core-review';
const now='2026-10-23T08:00:00.000Z';
const make=(id:string,source:Lesson['source']='legacy',kind:Lesson['kind']='vocabulary'):Lesson=>({
  schemaVersion:1,id,title:id,source,kind,
  items:[{id:id+':0',polish:'Tak',english:'Yes'},{id:id+':1',polish:'Nie',english:'No'}]
});
const core=make('Conversation_1');
const nextCore=make('numbers_1-20');
const personal=make('personal_test','personal');
const extras=make('Countries_of_the_World');
const reader=make('Basic_01R','legacy','reading');
const diagnostic=make('speak_swietokrzyska','curated');
const catalog=[extras,personal,nextCore,reader,diagnostic,core];
const due=(ids:string[]):ReviewSchedule=>Object.fromEntries(ids.map(id=>[id,{
  streak:0,dueAt:now,lastReviewedAt:now,attempts:1
}]));
describe('A-04 core vs personal and supplementary due review',()=>{
  it('uses actual saved due IDs, canonical course order, and separate optional/private lanes',()=>{
    const entries=partitionDueReviews(catalog,due([
      'Conversation_1:0','Conversation_1:1','numbers_1-20:0',
      'personal_test:0','Countries_of_the_World:1','speak_swietokrzyska:0','Basic_01R:0',
    ]),now);
    expect(entries.core.map(x=>x.lesson.id)).toEqual(['Conversation_1','numbers_1-20']);
    expect(entries.core[0].itemIds).toEqual(['Conversation_1:0','Conversation_1:1']);
    expect(entries.personal.map(x=>x.lesson.id)).toEqual(['personal_test']);
    expect(entries.explore.map(x=>x.lesson.id)).toEqual(['Countries_of_the_World','speak_swietokrzyska']);
    expect([dueLaneCount(entries.core),dueLaneCount(entries.personal),dueLaneCount(entries.explore)])
      .toEqual([3,1,2]);
  });
  it('does not invent a due item for unpractised or future scheduled lessons',()=>{
    const future=recordReview({},'Conversation_1:0',true,now);
    expect(partitionDueReviews(catalog,future,now)).toEqual({core:[],personal:[],explore:[]});
    expect(startCoreReviewRun([])).toBeNull();
    expect(partitionDueReviews(catalog,{},'not a date')).toEqual({core:[],personal:[],explore:[]});
  });
  it('advances a fixed due snapshot without endlessly recycling failed recall',()=>{
    const schedule=due(['Conversation_1:0','numbers_1-20:0','personal_test:0']);
    const lanes=partitionDueReviews(catalog,schedule,now);
    const run=startCoreReviewRun(lanes.core)!;
    expect(run.steps).toEqual([
      {lessonId:'Conversation_1',itemIds:['Conversation_1:0']},
      {lessonId:'numbers_1-20',itemIds:['numbers_1-20:0']}
    ]);
    const failed=recordReview(schedule,'Conversation_1:0',false,now);
    expect(dueItems(core,failed,now)).toHaveLength(1); // unchanged scheduler
    const second=nextCoreReviewRunStep(run)!;
    expect(second.position).toBe(1);
    expect(second.steps).toBe(run.steps);
    expect(nextCoreReviewRunStep(second)).toBeNull();
    expect(run.position).toBe(0);
    expect(run.steps.flatMap(step=>step.itemIds)).not.toContain('personal_test:0');
  });
  it('does not mutate schedule or fall into fake-course after optional work',()=>{
    const schedule=due(['Conversation_1:0','personal_test:0','Countries_of_the_World:0']);
    const previous=JSON.stringify(schedule);
    const run=startCoreReviewRun(partitionDueReviews(catalog,schedule,now).core)!;
    expect(run.steps.map(x=>x.lessonId)).toEqual(['Conversation_1']);
    expect(nextCoreReviewRunStep(run)).toBeNull();
    expect(JSON.stringify(schedule)).toBe(previous);
  });
});
