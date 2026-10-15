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
