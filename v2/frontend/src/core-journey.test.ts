import {describe,expect,test} from 'vitest';
import type {Lesson} from './model';
import catalog from '../../content/library-catalog.json';
import raw from '../../content/core-journey-v1.json';
import {CORE_JOURNEY_PLACEMENTS,groupJourneyLibrary,journeyPlacement,
  nextCoreLesson,orderedCoreLessons,validateCoreJourney} from './core-journey';

function lesson(id:string,source:'legacy'|'curated'|'personal'='legacy'):Lesson{
  const editorial=catalog.lessons.find(item=>item.id===id);
  return {schemaVersion:1,id,title:editorial?.title??'My practice',source,
    kind:id.startsWith('contrast_')?'sounds':editorial?.curriculum.stage==='learning'?'reading':'vocabulary',
    curriculum:editorial?.curriculum as Lesson['curriculum'],
    items:[{id:id+':0',polish:'Dzień dobry',english:'Good day'}]};
}
const all=catalog.lessons.map(item=>lesson(item.id,item.id.startsWith('contrast_')?'curated':'legacy'));

describe('A-01 source-backed, silent 3 by 3 course mapping',()=>{
  test('preserves the complete original catalogue and honest partial coverage',()=>{
    expect(catalog.lessons).toHaveLength(26);
    expect(CORE_JOURNEY_PLACEMENTS).toHaveLength(21);
    expect(new Set(CORE_JOURNEY_PLACEMENTS.map(x=>x.lessonId)).size).toBe(21);
    expect(CORE_JOURNEY_PLACEMENTS.every(x=>catalog.lessons.some(y=>y.id===x.lessonId))).toBe(true);
    expect(CORE_JOURNEY_PLACEMENTS.filter(x=>x.journey===3)).toHaveLength(0);
    expect(orderedCoreLessons(all)).toHaveLength(21);
    const sections=groupJourneyLibrary(all);
    expect(sections.map(x=>x.heading)).toEqual(['Your path','Explore more']);
    expect(sections[0].lessons).toHaveLength(21);
    expect(sections[1].lessons.map(x=>x.id).sort()).toEqual([
      'Countries_of_the_World','Districts_of_Warszawa','Names_of_Poland_1',
      'The_Cities_of_Poland','speak_swietokrzyska',
    ].sort());
    expect(sections.flatMap(x=>x.lessons).map(x=>x.id).sort()).toEqual(all.map(x=>x.id).sort());
  });

  test('orders practical greetings before isolated geographic word lists',()=>{
    const shuffled=[...all].reverse();
    expect(orderedCoreLessons(shuffled)[0].id).toBe('Conversation_1');
    expect(nextCoreLesson(shuffled,'Conversation_1')?.id).toBe('contrast_l_lstroked');
    expect(nextCoreLesson(shuffled,'Emergencies_and_Health')?.id).toBe('On_the_tram_talking_to_another_passenger');
    expect(nextCoreLesson(shuffled,'contrast_krzy_przy')?.id).toBe('numbers_1-20');
    expect(nextCoreLesson(shuffled,'H_M_clothes_shop_trying_on_a_T-shirt')).toBeNull();
    expect(nextCoreLesson(shuffled,'Road_Terminology')?.id).toBe('Conversation_-_shopping');
    expect(nextCoreLesson(shuffled,'speak_swietokrzyska')).toBeNull();
    expect(nextCoreLesson(shuffled,'missing')).toBeNull();
  });

  test('personal sets are never core, even when IDs/curriculum are forged to match',()=>{
    const fake=lesson('Conversation_1','personal');
    expect(journeyPlacement(fake)).toBeNull();
    const personal=lesson('personal_abc','personal');
    personal.curriculum=undefined;
    const grouped=groupJourneyLibrary([...all,personal]);
    expect(grouped.map(x=>x.heading)).toEqual(['Your path','Explore more','Your lessons']);
    expect(grouped[2].lessons).toEqual([personal]);
    expect(nextCoreLesson([fake,personal],'Conversation_1')).toBeNull();
  });

  test('rejects malformed, duplicate or invented journey metadata',()=>{
    expect(validateCoreJourney(raw)).toEqual(CORE_JOURNEY_PLACEMENTS);
    for(const candidate of [
      {...raw,schemaVersion:2},
      {...raw,placements:[...raw.placements,raw.placements[0]]},
      {...raw,placements:[{lessonId:'personal_hijack',journey:1,position:'beginning',order:1}]},
      {...raw,placements:[{lessonId:'speak_swietokrzyska',journey:1,position:'beginning',order:1}]},
      {...raw,placements:[{lessonId:'other',journey:4,position:'beginning',order:1}]},
      {...raw,placements:[{lessonId:'other',journey:1,position:'beginning',order:2}]},
    ])expect(()=>validateCoreJourney(candidate)).toThrow();
  });
});
