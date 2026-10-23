import {describe,expect,test} from 'vitest';
import {groupLibraryLessons,libraryMatches,LIBRARY_STAGES,inLibraryView,libraryViewCount,nextCurriculumLesson} from './library-curriculum';
import type {Lesson} from './model';

const make = (id:string,title:string,stage:NonNullable<Lesson['curriculum']>['stage'],
  track:NonNullable<Lesson['curriculum']>['track'],order:number):Lesson=>({
  schemaVersion:1,id,title,kind:stage==='learning'?'reading':track==='sounds'?'sounds':'vocabulary',
  source:'legacy',items:[{id:id+':0',polish:'Dzień dobry',english:'Good day'}],
  description:'A source-grounded lesson about Polish language.',
  curriculum:{stage,track,order},
});

describe('grouped curriculum library',()=>{
  test('keeps meaningful order regardless of original file order, without duplicating lessons',()=>{
    const lessons=[
      make('read','Read','learning','conversations-reading',1),
      make('numbers','Numbers 1-20','fundamentals','first-words',1),
      make('clusters','C, CZ, Ć','fundamentals','sounds',2),
      make('greetings','Greetings','basic','first-phrases',1),
      make('z','Z / Ż','fundamentals','sounds',1),
      make('lab','Lab','practice','lab',1),
    ];
    const sections=groupLibraryLessons(lessons);
    expect(sections.map(section=>section.heading))
      .toEqual(['Fundamentals','Basic','Learning','Practice tools']);
    expect(sections[0].tracks.map(track=>track.heading))
      .toEqual(['Polish sounds','First words']);
    expect(sections[0].tracks[0].lessons.map(lesson=>lesson.id)).toEqual(['z','clusters']);
    expect(sections.flatMap(section=>section.tracks.flatMap(track=>track.lessons.map(lesson=>lesson.id))).sort())
      .toEqual(lessons.map(lesson=>lesson.id).sort());
    expect(LIBRARY_STAGES.slice(0,3).map(stage=>stage.id))
      .toEqual(['fundamentals','basic','learning']);
  });
  test('keeps personal lessons separately and hides empty groups under filters',()=>{
    const personal:Lesson={...make('mine','My Polish','basic','sentences',1),curriculum:undefined,source:'personal'};
    const sections=groupLibraryLessons([personal,make('read','Reading','learning','conversations-reading',1)]);
    expect(sections.map(section=>section.heading)).toEqual(['Learning','Your lessons']);
    expect(groupLibraryLessons([])).toEqual([]);
  });
  test('stage views are presentation-only and show personal lessons separately',()=>{
    const items=[
      make('sound','Sounds','fundamentals','sounds',1),
      make('number','Numbers','fundamentals','first-words',1),
      make('basic','Phrases','basic','first-phrases',1),
      make('read','Reading','learning','conversations-reading',1),
      make('lab','Test','practice','lab',1),
      {...make('personal','My phrasebook','basic','sentences',1),
        curriculum:undefined,source:'personal' as const},
    ];
    expect(libraryViewCount(items,'all')).toBe(6);
    expect(libraryViewCount(items,'fundamentals')).toBe(2);
    expect(libraryViewCount(items,'basic')).toBe(1);
    expect(libraryViewCount(items,'learning')).toBe(1);
    expect(libraryViewCount(items,'practice')).toBe(1);
    expect(libraryViewCount(items,'personal')).toBe(1);
    expect(items.filter(item=>inLibraryView(item,'learning')).map(item=>item.id)).toEqual(['read']);
    expect(items.filter(item=>inLibraryView(item,'personal')).map(item=>item.id)).toEqual(['personal']);
    expect(items.filter(item=>inLibraryView(item,'all'))).toEqual(items);
    expect(items[5].curriculum).toBeUndefined();
  });
  test('suggests next authored course step regardless of source file order or past progress',()=>{
    const sound2=make('s2','Second sound','fundamentals','sounds',2);
    const sound1=make('s1','First sound','fundamentals','sounds',1);
    const numbers=make('nums','Numbers','fundamentals','first-words',1);
    const expanded=make('more','More words','fundamentals','expanded-words',1);
    const phrases=make('phrases','Expressions','basic','first-phrases',1);
    const sentences=make('sentences','Sentences','basic','sentences',1);
    const read=make('reading','Read','learning','conversations-reading',1);
    const lab=make('lab','Pronunciation lab','practice','lab',1);
    const personal:Lesson={...sentences,id:'mine',source:'personal',curriculum:undefined};
    const shuffled=[read,lab,expanded,sentences,personal,phrases,sound2,numbers,sound1];
    const expected:Record<string,string>={s1:'s2',s2:'nums',nums:'more',
      more:'phrases',phrases:'sentences',sentences:'reading'};
    for(const [from,to] of Object.entries(expected)){
      expect(nextCurriculumLesson(shuffled,from)?.id).toBe(to);
    }
    expect(nextCurriculumLesson(shuffled,'reading')).toBeNull();
    expect(nextCurriculumLesson(shuffled,'lab')).toBeNull();
    expect(nextCurriculumLesson(shuffled,'mine')).toBeNull();
    expect(nextCurriculumLesson(shuffled,'missing')).toBeNull();
  });
  test('search matches new titles, descriptions, historical file IDs and Polish source',()=>{
    const lesson=make('Conversation_1','Greetings and Introductions','basic','first-phrases',1);
    expect(libraryMatches(lesson,'Conversation 1')).toBe(true);
    expect(libraryMatches(lesson,'greetings')).toBe(true);
    expect(libraryMatches(lesson,'source-grounded')).toBe(true);
    expect(libraryMatches(lesson,'dzień dobry')).toBe(true);
    expect(libraryMatches(lesson,'unrelated')).toBe(false);
    expect(libraryMatches(make('numbers_1-20','Numbers 1-20','fundamentals','first-words',1),'numbers 1-20')).toBe(true);
  });
});
