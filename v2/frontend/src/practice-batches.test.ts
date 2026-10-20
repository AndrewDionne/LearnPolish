import { describe, expect, test } from 'vitest';
import type { Lesson } from './model';
import {
  PRACTICE_BATCH_SIZE, boundedBatch, firstUnvisitedBatch, practiceBatchCount,
  practiceBatchItems, practiceBatchLabel, usesPracticeBatches,
} from './practice-batches';

const words: Lesson = {
  schemaVersion: 1, id: 'words', title: 'Twenty words', kind: 'vocabulary', source: 'legacy',
  items: Array.from({length: 20}, (_, index) => ({
    id: 'words:' + index, polish: 'Słowo ' + index, english: 'Word ' + index,
    audio: 'generated/audio/words/' + index + '.mp3',
  })),
};
describe('short vocabulary practice sessions', () => {
  test('long fully recorded sets become groups of eight, retaining the canonical IDs', () => {
    expect(PRACTICE_BATCH_SIZE).toBe(8);
    expect(usesPracticeBatches(words)).toBe(true);
    expect(practiceBatchCount(words)).toBe(3);
    expect(practiceBatchItems(words, 'learn', 0).map(item => item.id)).toEqual(
      Array.from({length: 8}, (_, i) => 'words:' + i));
    expect(practiceBatchItems(words, 'speak', 1)[0]?.id).toBe('words:8');
    expect(practiceBatchItems(words, 'listen', 2).map(item => item.id)).toEqual(
      ['words:16', 'words:17', 'words:18', 'words:19']);
    expect(practiceBatchLabel(words, 2)).toBe('Part 3: 17–20');
    expect(boundedBatch(words, 99)).toBe(2);
    expect(boundedBatch(words, -10)).toBe(0);
    expect(boundedBatch(words, Number.NaN)).toBe(0);
  });
  test('resume moves to first unvisited part while previous and completed parts remain accessible', () => {
    expect(firstUnvisitedBatch(words, {})).toBe(0);
    const seen = Object.fromEntries(words.items.slice(0, 8).map(item => [item.id, {seen: 1}]));
    expect(firstUnvisitedBatch(words, seen)).toBe(1);
    // Any already-recorded Listen completion means that word was encountered.
    const heard = Object.fromEntries(words.items.slice(0, 16).map(item => ['listen:' + item.id, {seen: 1}]));
    expect(firstUnvisitedBatch(words, heard)).toBe(2);
    const done = Object.fromEntries(words.items.map(item => [item.id, {seen: 1}]));
    expect(firstUnvisitedBatch(words, done)).toBe(0);
  });
  test('short sets, reading, and partial audio sources retain their original full sessions', () => {
    const short = {...words, items: words.items.slice(0, 8)};
    const reading = {...words, kind: 'reading' as const};
    const partial = {...words, items: [...words.items.slice(0, 19), {...words.items[19], audio: undefined}]};
    for (const lesson of [short, reading, partial]) {
      expect(usesPracticeBatches(lesson)).toBe(false);
      expect(practiceBatchCount(lesson)).toBe(1);
      expect(firstUnvisitedBatch(lesson, {})).toBe(0);
      expect(practiceBatchItems(lesson, 'learn', 2)).toEqual(lesson.items);
    }
    expect(practiceBatchItems(partial, 'listen', 0)).toHaveLength(19);
  });
});
