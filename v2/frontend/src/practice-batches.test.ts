import { describe, expect, test } from 'vitest';
import type { Lesson } from './model';
import {
  boundedBatch, firstUnvisitedBatch, practiceBatchCount,
  practiceBatchItems, practiceBatchLabel, usesPracticeBatches,
} from './practice-batches';

const words: Lesson = {
  schemaVersion: 1, id: 'numbers_1-20', title: 'Numbers 1–20', kind: 'vocabulary', source: 'legacy',
  items: Array.from({length: 20}, (_, index) => ({
    id: 'numbers_1-20:' + index, polish: ({0:'Jeden',9:'Dziesięć',10:'Jedenaście',19:'Dwadzieścia'} as Record<number,string>)[index] || 'Liczba ' + index, english: 'Word ' + index,
    audio: 'generated/audio/words/' + index + '.mp3',
  })),
};
describe('short vocabulary practice sessions', () => {
  test('number lesson stays one lesson with two natural ten-number sections, retaining the canonical IDs', () => {
    expect(usesPracticeBatches(words)).toBe(true);
    expect(practiceBatchCount(words)).toBe(2);
    expect(practiceBatchItems(words, 'learn', 0).map(item => item.id)).toEqual(
      Array.from({length: 10}, (_, i) => 'numbers_1-20:' + i));
    expect(practiceBatchItems(words, 'speak', 1)[0]?.id).toBe('numbers_1-20:10');
    expect(practiceBatchItems(words, 'listen', 1).map(item => item.id)).toEqual(
      Array.from({length: 10}, (_, i) => 'numbers_1-20:' + (i + 10)));
    expect(practiceBatchLabel(words, 0)).toBe('Numbers 1–10');
    expect(practiceBatchLabel(words, 1)).toBe('Numbers 11–20');
    expect(boundedBatch(words, 99)).toBe(1);
    expect(boundedBatch(words, -10)).toBe(0);
    expect(boundedBatch(words, Number.NaN)).toBe(0);
  });
  test('resume moves to first unvisited part while previous and completed parts remain accessible', () => {
    expect(firstUnvisitedBatch(words, {})).toBe(0);
    const seen = Object.fromEntries(words.items.slice(0, 10).map(item => [item.id, {seen: 1}]));
    expect(firstUnvisitedBatch(words, seen)).toBe(1);
    // Any already-recorded Listen completion means that word was encountered.
    const heard = Object.fromEntries(words.items.slice(0, 10).map(item => ['listen:' + item.id, {seen: 1}]));
    expect(firstUnvisitedBatch(words, heard)).toBe(1);
    const done = Object.fromEntries(words.items.map(item => [item.id, {seen: 1}]));
    expect(firstUnvisitedBatch(words, done)).toBe(0);
  });
  test('short sets, reading, and partial audio sources retain their original full sessions', () => {
    const short = {...words, items: words.items.slice(0, 8)};
    const reading = {...words, kind: 'reading' as const};
    const partial = {...words, items: [...words.items.slice(0, 19), {...words.items[19], audio: undefined}]};
    const otherFullLesson = {...words, id: 'Conversation_1', title: 'Greetings'};
    const reordered = {...words, items: [words.items[1], words.items[0], ...words.items.slice(2)]};
    for (const lesson of [short, reading, partial, otherFullLesson, reordered]) {
      expect(usesPracticeBatches(lesson)).toBe(false);
      expect(practiceBatchCount(lesson)).toBe(1);
      expect(firstUnvisitedBatch(lesson, {})).toBe(0);
      expect(practiceBatchItems(lesson, 'learn', 2)).toEqual(lesson.items);
    }
    expect(practiceBatchItems(partial, 'listen', 0)).toHaveLength(19);
  });
});
