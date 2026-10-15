import { describe, expect, test } from 'vitest';
import { importPersonalLesson, makePersonalLesson, parsePersonalLessons, toPortableLesson, upsertPersonalLesson } from './personal';

describe('personal lesson authoring', () => {
  test('creates a portable personal lesson without Git or backend', () => {
    let i = 0;
    const fresh = makePersonalLesson({
      title: '  Greetings  ', kind: 'vocabulary',
      items: [{ polish: '  Cześć ', english: ' Hi ' }, { polish: 'Dzień dobry', english: 'Hello' }],
    }, undefined, () => String(++i));
    expect(fresh.id).toBe('personal_1');
    expect(fresh.items.map(x => x.id)).toEqual(['personal_1:2', 'personal_1:3']);
    expect(fresh.items[0].polish).toBe('Cześć');
    expect(fresh.source).toBe('personal');
  });
  test('editing retains lesson and unchanged item identities', () => {
    const initial = makePersonalLesson({ title: 'Old', kind: 'vocabulary', items: [{ polish: 'Tak', english: 'Yes' }] }, undefined, () => 'abc');
    const updated = makePersonalLesson({ title: 'New', kind: 'vocabulary', items: [{ ...initial.items[0], english: 'Yep' }] }, initial, () => 'xyz');
    expect(updated.id).toBe(initial.id);
    expect(updated.items[0].id).toBe(initial.items[0].id);
    expect(updated.items[0].english).toBe('Yep');
  });
  test('rejects incomplete items', () => {
    expect(() => makePersonalLesson({ title: 'Bad', kind: 'vocabulary', items: [{ polish: '', english: 'test' }] })).toThrow(/Item 1/);
    expect(() => makePersonalLesson({ title: 'Bad', kind: 'vocabulary', items: [] })).toThrow(/between 1 and 150/);
  });
  test('imports as an independent lesson and strips old audio', () => {
    const lesson = makePersonalLesson({ title: 'Example', kind: 'vocabulary', items: [{ polish: 'Tak', english: 'Yes' }] }, undefined, () => 'one');
    const portable = toPortableLesson(lesson);
    const imported = importPersonalLesson({ ...portable, source: 'legacy', items: [{ ...portable.items[0], audio: 'https://bad.test/speech.mp3' }] }, () => 'two');
    expect(imported.id).not.toBe(lesson.id);
    expect(imported.items[0].audio).toBeUndefined();
    expect(imported.items[0].polish).toBe('Tak');
  });
  test('loads only valid user sets and upserts on edit', () => {
    const lesson = makePersonalLesson({ title: 'Good', kind: 'vocabulary', items: [{ polish: 'Nie', english: 'No' }] }, undefined, () => 'id');
    expect(parsePersonalLessons(JSON.stringify([null, {}, lesson, lesson]))).toHaveLength(1);
    expect(upsertPersonalLesson([lesson], { ...lesson, title: 'Renamed' })).toHaveLength(1);
  });
});
