import { describe, expect, test } from 'vitest';
import { parseManifest, validateLesson } from './model';
import { parseProgress, recordAttempt, recallRate } from './progress';

const lesson = {
  schemaVersion: 1, id: 'greetings', title: 'Greetings', kind: 'vocabulary',
  source: 'legacy', items: [{ id: 'greetings:0', polish: 'Cześć', english: 'Hi' }]
};

describe('lesson schema', () => {
  test('validates a canonical lesson', () => {
    expect(validateLesson(lesson)).toBe(true);
    expect(parseManifest({ schemaVersion: 1, lessons: [lesson] })).toHaveLength(1);
  });
  test('practice-only reference status is allowed only in built vocabulary items',()=>{
    expect(validateLesson({...lesson,items:[{...lesson.items[0],referenceReview:'practice_only'}]})).toBe(true);
    expect(validateLesson({...lesson,kind:'sounds',
      items:[{...lesson.items[0],referenceReview:'practice_only'}]})).toBe(false);
    expect(validateLesson({...lesson,items:[{...lesson.items[0],referenceReview:'verified'}]})).toBe(false);
  });
  test('rejects invalid items and duplicate IDs', () => {
    expect(validateLesson({ ...lesson, items: [{ polish: '', english: 'Hi' }] })).toBe(false);
    expect(() => parseManifest({ schemaVersion: 1, lessons: [lesson, lesson] })).toThrow(/Duplicate/);
  });
});
describe('syllable-aligned English pronunciation guides', () => {
  const chunks = [
    {polish:'Świę',englishCue:'shfyehn',letterFocus:'św · ię',tip:'Soft ś.'},
    {polish:'to',englishCue:'toh',letterFocus:'t · o',tip:'Open o.'},
    {polish:'krzy',englishCue:'KSHIH',letterFocus:'k · rz · y',tip:'Stress krzy.'},
    {polish:'ska',englishCue:'skah',letterFocus:'sk · a',tip:'Clear ska.'},
  ];
  const item = {id:'speak_swietokrzyska:0',polish:'Świętokrzyska',
                english:'Warsaw place name',
                pronunciationGuide:{
                  syllables:chunks,stressIndex:2,
                  qualification:'Approximate English sounds.',
                  reviewStatus:'needs_native_speaker_review',
                }};
  const candidate = {...lesson,items:[item]};
  test('accepts exactly aligned cues; rejects null, mismatched syllables and invalid stress',()=>{
    expect(validateLesson(candidate)).toBe(true);
    expect(validateLesson({...candidate,items:[{...item,pronunciationGuide:null}]})).toBe(false);
    expect(validateLesson({...candidate,items:[{...item,pronunciationGuide:{
      ...item.pronunciationGuide,stressIndex:7,
    }}]})).toBe(false);
    expect(validateLesson({...candidate,items:[{...item,pronunciationGuide:{
      ...item.pronunciationGuide,syllables:chunks.slice(1),
    }}]})).toBe(false);
    expect(validateLesson({...candidate,items:[{...item,pronunciationGuide:{
      ...item.pronunciationGuide,syllables:[{...chunks[0],englishCue:''},...chunks.slice(1)],
    }}]})).toBe(false);
  });
});

describe('progress', () => {
  test('records distinct learning outcomes', () => {
    const one = recordAttempt({}, 'greetings:0', false, '2026-10-16T00:00:00Z');
    const two = recordAttempt(one, 'greetings:0', true, '2026-10-16T00:01:00Z');
    expect(two['greetings:0']).toMatchObject({ seen: 2, remembered: 1, needsPractice: 1 });
    expect(recallRate(two)).toBe(50);
  });
  test('rejects malformed persisted data', () => {
    expect(parseProgress('not json')).toEqual({});
    expect(parseProgress('{"a":{"seen":-1,"remembered":1,"needsPractice":0,"lastSeen":"x"}}')).toEqual({});
  });
});

describe('curated contrast structure', () => {
  test('rejects a sound group referencing unrelated items', () => {
    const base = { ...lesson, source: 'curated', kind: 'sounds',
      items: [{ id:'x:0', polish:'plac', english:'square', soundGroupId:'c' },
        { id:'x:1', polish:'Cztery', english:'four', soundGroupId:'cz' }] };
    const soundGroups = [
      { id:'c', label:'C', ipa:'/t͡s/', hint:'ts', itemIds:['x:0','x:1'] },
      { id:'cz', label:'CZ', ipa:'/t͡ʂ/', hint:'hard ch', itemIds:['x:1','x:0'] },
    ];
    expect(validateLesson({ ...base, soundGroups })).toBe(false);
  });
});


describe('authored reading comprehension schema', () => {
  test('rejects ambiguous answers, invalid indexes and questions on vocabulary items', () => {
    const q = {prompt:'What is the speaker asking?', options:['Blue','Green','Red'], correctIndex:1, feedback:'Green is the answer.'};
    const sample = {
      ...lesson, kind:'reading',
      items:[{...lesson.items[0], comprehension:q}],
      progression:{stage:'foundations', order:1, goal:'Start with greetings'},
    };
    const duplicate = {...sample, items:[{...lesson.items[0], comprehension:{...q, options:['Blue','Blue','Red']}}]};
    const invalidIndex = {...sample, items:[{...lesson.items[0], comprehension:{...q, correctIndex:4}}]};
    expect(validateLesson(sample)).toBe(true);
    expect(validateLesson(duplicate)).toBe(false);
    expect(validateLesson(invalidIndex)).toBe(false);
    expect(validateLesson({...sample, kind:'vocabulary'})).toBe(false);
  });
});


describe('exact-source short dialogue schema',()=>{
  const items=[
    {id:'Basic_01R:0',polish:'Cześć! Jak się masz?',english:'Hi, how are you?',
      audio:'generated/audio/Basic_01R/0.mp3'},
    {id:'Basic_01R:1',polish:'Dziękuję, mam się dobrze.',english:'Thank you, I am well.',
      audio:'generated/audio/Basic_01R/1.mp3'},
    {id:'Basic_01R:unrelated',polish:'Przepraszam, nie rozumiem.',english:'I do not understand',
      audio:'generated/audio/Basic_01R/5.mp3'},
    {id:'Basic_01R:extra',polish:'Mam na imię Ela.',english:'My name is Ela.',
      audio:'generated/audio/Basic_01R/6.mp3'},
  ];
  const scene={id:'how-are-you',title:'How are you?',
    speakers:{A:'Person A',B:'Person B'},
    turns:[{itemId:'Basic_01R:0',speaker:'A'}, {itemId:'Basic_01R:1',speaker:'B'}],
    replyPractice:{promptItemId:'Basic_01R:0',replyItemId:'Basic_01R:1',
      choiceItemIds:['Basic_01R:extra','Basic_01R:1','Basic_01R:unrelated'],correctIndex:1},
    comprehension:{prompt:'How does the second speaker feel?',
      options:['Well, thank you','Hungry','Lost'],correctIndex:0,
      feedback:'They say they are feeling well.'}};
  const reading={...lesson,id:'Basic_01R',kind:'reading',items,microDialogues:[scene]};
  test('accepts only source-linked, alternating, recorded reading turns',()=>{
    expect(validateLesson(reading)).toBe(true);
    expect(validateLesson({...reading,kind:'vocabulary'})).toBe(false);
    expect(validateLesson({...reading,microDialogues:[scene,scene]})).toBe(false);
    expect(validateLesson({...reading,microDialogues:[{...scene,turns:[scene.turns[0],
      {...scene.turns[1],speaker:'A'}]}]})).toBe(false);
    expect(validateLesson({...reading,microDialogues:[{...scene,turns:[scene.turns[0],
      {...scene.turns[1],itemId:'Basic_01R:missing'}]}]})).toBe(false);
    expect(validateLesson({...reading,items:[items[0],{...items[1],audio:undefined}]})).toBe(false);
    expect(validateLesson({...reading,microDialogues:[{...scene,replyPractice:undefined}]})).toBe(false);
    expect(validateLesson({...reading,microDialogues:[{...scene,replyPractice:{
      ...scene.replyPractice,correctIndex:2}}]})).toBe(false);
    expect(validateLesson({...reading,microDialogues:[{...scene,replyPractice:{
      ...scene.replyPractice,choiceItemIds:['Basic_01R:1','Basic_01R:1','Basic_01R:unrelated']}}]})).toBe(false);
    expect(validateLesson({...reading,microDialogues:[{...scene,replyPractice:{
      ...scene.replyPractice,promptItemId:'Basic_01R:unrelated'}}]})).toBe(false);
    expect(validateLesson({...reading,microDialogues:[{...scene,comprehension:undefined}]})).toBe(false);
    expect(validateLesson({...reading,microDialogues:[{...scene,comprehension:{
      ...scene.comprehension,options:['Well, thank you','Well, thank you','Lost']}}]})).toBe(false);
    expect(validateLesson({...reading,microDialogues:[{...scene,comprehension:{
      ...scene.comprehension,correctIndex:3}}]})).toBe(false);
  });
});

describe('explicit learning tier validation',()=>{
  test('tiers remain opt-in and unknown difficulty is not invented',()=>{
    expect(validateLesson({...lesson,difficultyTier:3})).toBe(true);
    expect(validateLesson({...lesson,difficultyTier:9})).toBe(false);
  });
});

describe('C-07 independently reviewed source-word syllable excerpt schema',()=>{
 const timings={
  method:'independently-reviewed-source-excerpts-v1',
  audio:'generated/audio/Road_Terminology/0.mp3',
  sourceSha256:'a'.repeat(64),durationMs:1200,
  segments:[{polish:'u',startMs:0,endMs:350},
   {polish:'li',startMs:350,endMs:700},
   {polish:'ca',startMs:700,endMs:1200}],
 };
 const item={id:'Road_Terminology:0',polish:'ulica',english:'Street',
  audio:timings.audio,syllableAudio:timings};
 const source={schemaVersion:1,id:'Road_Terminology',title:'Roads',
  source:'legacy',kind:'vocabulary',items:[item]};
 test('permits properly aligned reviewed source excerpts but not arbitrary imported personal clip data',()=>{
  expect(validateLesson(source)).toBe(true);
  expect(validateLesson({...source,source:'personal'})).toBe(false);
  expect(validateLesson({...source,items:[{...item,audio:undefined}]})).toBe(false);
  expect(validateLesson({...source,items:[{...item,polish:'aleja'}]})).toBe(false);
 });
 test('rejects zero/overlapping/reordered/out-of-duration excerpts',()=>{
  expect(validateLesson({...source,items:[{...item,syllableAudio:{
   ...timings,segments:[timings.segments[0],{...timings.segments[1],startMs:200},timings.segments[2]]
  }}]})).toBe(false);
  expect(validateLesson({...source,items:[{...item,syllableAudio:{
   ...timings,segments:timings.segments.map((s,i)=>i===2?{...s,endMs:1550}:s)
  }}]})).toBe(false);
  expect(validateLesson({...source,items:[{...item,syllableAudio:{
   ...timings,sourceSha256:'not-a-hash'
  }}]})).toBe(false);
 });
});
