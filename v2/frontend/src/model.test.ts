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
  test('rejects invalid items and duplicate IDs', () => {
    expect(validateLesson({ ...lesson, items: [{ polish: '', english: 'Hi' }] })).toBe(false);
    expect(() => parseManifest({ schemaVersion: 1, lessons: [lesson, lesson] })).toThrow(/Duplicate/);
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
