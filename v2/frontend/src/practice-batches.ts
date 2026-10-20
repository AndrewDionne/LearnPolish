import type { Lesson, LessonItem } from './model';
import type { LearningMode } from './modes';
import { itemPractised, itemsForMode } from './modes';

type PracticeSection = { start: number; end: number; label: string };

/**
 * Sections are editorial choices, not an automatic item-count threshold.
 * Numbers 1–20 is ONE lesson with two optional, meaningful practice sections.
 * Other lessons remain whole until their content boundaries are reviewed.
 */
function lessonSections(lesson: Lesson): PracticeSection[] | null {
  if (lesson.id !== 'numbers_1-20' || lesson.kind !== 'vocabulary' || lesson.items.length !== 20) {
    return null;
  }
  // Fail closed if the source catalog changes; never mislabel words as numbered groups.
  const items = lesson.items;
  if (!items.every((item, index) => item.id === `numbers_1-20:${index}` && !!item.audio) ||
      items[0]?.polish !== 'Jeden' ||
      items[9]?.polish !== 'Dziesięć' ||
      items[10]?.polish !== 'Jedenaście' ||
      items[19]?.polish !== 'Dwadzieścia') {
    return null;
  }
  return [
    { start: 0, end: 10, label: 'Numbers 1–10' },
    { start: 10, end: 20, label: 'Numbers 11–20' },
  ];
}

export function usesPracticeBatches(lesson: Lesson): boolean {
  return lessonSections(lesson) !== null;
}

export function practiceBatchCount(lesson: Lesson): number {
  return lessonSections(lesson)?.length ?? 1;
}

export function boundedBatch(lesson: Lesson, requested: number): number {
  if (!Number.isSafeInteger(requested)) return 0;
  return Math.max(0, Math.min(practiceBatchCount(lesson) - 1, requested));
}

export function practiceBatchItems(lesson: Lesson, mode: LearningMode, batch: number): LessonItem[] {
  const available = itemsForMode(lesson, mode);
  const sections = lessonSections(lesson);
  if (!sections) return available;
  const section = sections[boundedBatch(lesson, batch)];
  const selectedIds = new Set(lesson.items.slice(section.start, section.end).map(item => item.id));
  return available.filter(item => selectedIds.has(item.id));
}

/** Reopen at the first not-yet-encountered section; existing item progress is untouched. */
export function firstUnvisitedBatch(lesson: Lesson, progress: Record<string, unknown>): number {
  const sections = lessonSections(lesson);
  if (!sections) return 0;
  const first = lesson.items.findIndex(item => !itemPractised(progress, item.id));
  if (first < 0) return 0;
  return sections.findIndex(section => first >= section.start && first < section.end);
}

export function practiceBatchLabel(lesson: Lesson, batch: number): string {
  return lessonSections(lesson)?.[boundedBatch(lesson, batch)].label ?? lesson.title;
}
