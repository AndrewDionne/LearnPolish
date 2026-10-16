import { describe, expect, test } from 'vitest';
import { availableModes, comprehensionChoices, itemPractised, itemsForMode, progressKey } from './modes';
import type { Lesson } from './model';

const lesson: Lesson = {
  schemaVersion: 1, id: 'sample', title: 'Sample', kind: 'reading', source: 'legacy',
  items: [
    { id: 'sample:0', polish: 'Tak', english: 'Yes', audio: 'generated/audio/sample/0.mp3' },
    { id: 'sample:1', polish: 'Nie', english: 'No' },
    { id: 'sample:2', polish: 'Może', english: 'Maybe', audio: 'generated/audio/sample/2.mp3' },
  ],
};

describe('learning modes', () => {
  test('reading exposes listen only when real audio is present', () => {
    expect(availableModes(lesson)).toEqual(['read', 'listen']);
    expect(availableModes({ ...lesson, items: [{ id: 'x', polish: 'Tak', english: 'Yes' }] })).toEqual(['read']);
    expect(availableModes({ ...lesson, kind: 'vocabulary' })).toEqual(['learn', 'listen']);
  });

  test('listening never queues an item without reference audio', () => {
    expect(itemsForMode(lesson, 'listen').map(x => x.id)).toEqual(['sample:0', 'sample:2']);
    expect(itemsForMode(lesson, 'read')).toHaveLength(3);
  });

  test('comprehension choices include target exactly once and unique distractors', () => {
    for (let i = 0; i < lesson.items.length; i++) {
      const choices = comprehensionChoices(lesson.items, lesson.items[i], i);
      expect(choices.filter(x => x === lesson.items[i].english)).toHaveLength(1);
      expect(new Set(choices).size).toBe(choices.length);
    }
    expect(comprehensionChoices([lesson.items[0]], lesson.items[0], 0)).toEqual([]);
  });

  test('mode-specific practice leaves Learn history intact', () => {
    expect(progressKey('sample:0', 'learn')).toBe('sample:0');
    expect(progressKey('sample:0', 'listen')).toBe('listen:sample:0');
    expect(itemPractised({ 'listen:sample:0': {} }, 'sample:0')).toBe(true);
    expect(itemPractised({}, 'sample:0')).toBe(false);
  });
});
