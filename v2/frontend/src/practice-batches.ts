import type { Lesson, LessonItem } from './model';
import type { LearningMode } from './modes';
import { itemPractised, itemsForMode } from './modes';

export const PRACTICE_BATCH_SIZE = 8;

/** Long, fully recorded vocabulary sets: smaller sessions, unchanged source item IDs. */
export function usesPracticeBatches(lesson: Lesson): boolean {
  return lesson.kind === 'vocabulary' &&
    lesson.items.length >= 2 * PRACTICE_BATCH_SIZE &&
    lesson.items.every(item => !!item.audio);
}

export function practiceBatchCount(lesson: Lesson): number {
  return usesPracticeBatches(lesson)
    ? Math.ceil(lesson.items.length / PRACTICE_BATCH_SIZE)
    : 1;
}

export function boundedBatch(lesson: Lesson, requested: number): number {
  if (!Number.isSafeInteger(requested)) return 0;
  return Math.max(0, Math.min(practiceBatchCount(lesson) - 1, requested));
}

export function practiceBatchItems(lesson: Lesson, mode: LearningMode, batch: number): LessonItem[] {
  const available = itemsForMode(lesson, mode);
  if (!usesPracticeBatches(lesson)) return available;
  const start = boundedBatch(lesson, batch) * PRACTICE_BATCH_SIZE;
  return available.slice(start, start + PRACTICE_BATCH_SIZE);
}

/** On reopening, start at the first unvisited part; never invent per-part progress. */
export function firstUnvisitedBatch(lesson: Lesson, progress: Record<string, unknown>): number {
  if (!usesPracticeBatches(lesson)) return 0;
  const first = lesson.items.findIndex(item => !itemPractised(progress, item.id));
  return first < 0 ? 0 : Math.floor(first / PRACTICE_BATCH_SIZE);
}

export function practiceBatchLabel(lesson: Lesson, batch: number): string {
  const group = boundedBatch(lesson, batch);
  const first = group * PRACTICE_BATCH_SIZE + 1;
  const last = Math.min(lesson.items.length, first + PRACTICE_BATCH_SIZE - 1);
  return `Part ${group + 1}: ${first}–${last}`;
}
