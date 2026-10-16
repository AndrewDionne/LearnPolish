import { validateLesson } from './model';
import type { Lesson } from './model';
import { toPortableLesson } from './personal';
import type { Progress } from './progress';
import { parseProgress } from './progress';
import type { ReviewSchedule } from './review';
import { parseReviewSchedule } from './review';
import type { ReadingPositions } from './reading-position';
import { parseReadingPositions } from './reading-position';

export const BACKUP_FORMAT = 'path-to-polish-v2-local-backup';
export const MAX_BACKUP_BYTES = 2_000_000;
export type LocalBackup = {
  format: typeof BACKUP_FORMAT;
  version: 1;
  exportedAt: string;
  personalLessons: Lesson[];
  progress: Progress;
  reviews: ReviewSchedule;
  readingPositions: ReadingPositions;
  lastLessonId: string | null;
};

export function makeBackup(data: Omit<LocalBackup, 'format' | 'version' | 'exportedAt'>, exportedAt: string): LocalBackup {
  return {
    format: BACKUP_FORMAT, version: 1, exportedAt,
    personalLessons: data.personalLessons.map(toPortableLesson),
    progress: data.progress, reviews: data.reviews, readingPositions: data.readingPositions,
    lastLessonId: data.lastLessonId,
  };
}

function checkedMap<T>(input: unknown, parser: (raw: string) => Record<string, T>, label: string): Record<string, T> {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Invalid ' + label + ' data in backup');
  const source = Object.keys(input);
  if (source.length > 20_000) throw new Error(label + ' data exceeds backup limits');
  const restored = parser(JSON.stringify(input));
  if (Object.keys(restored).length !== source.length) throw new Error('Invalid ' + label + ' entries in backup');
  return restored;
}

export function parseBackup(value: unknown): LocalBackup {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Backup must be a JSON object');
  const raw = value as Partial<LocalBackup>;
  if (raw.format !== BACKUP_FORMAT || raw.version !== 1)
    throw new Error('This file is not a supported Path to Polish V2 backup');
  if (typeof raw.exportedAt !== 'string' || !Number.isFinite(Date.parse(raw.exportedAt)))
    throw new Error('Backup export date is invalid');
  if (!Array.isArray(raw.personalLessons) || raw.personalLessons.length > 100)
    throw new Error('Backup contains an invalid number of personal lessons');
  const ids = new Set<string>();
  const personalLessons = raw.personalLessons.map((lesson, index) => {
    if (!validateLesson(lesson) || lesson.source !== 'personal' ||
        !lesson.id.startsWith('personal_') || lesson.title.length > 100 ||
        lesson.items.length > 150 || ids.has(lesson.id)) {
      throw new Error('Invalid or duplicate personal lesson at position ' + (index + 1));
    }
    ids.add(lesson.id);
    if (lesson.items.some(item => !!item.audio || item.polish.length > 800 || item.english.length > 1400))
      throw new Error('Backup lessons must contain text only, without audio links');
    if (new Set(lesson.items.map(item => item.id)).size !== lesson.items.length)
      throw new Error('Duplicate item identifiers in backed-up lesson');
    return toPortableLesson(lesson);
  });
  if (raw.lastLessonId !== null &&
      (typeof raw.lastLessonId !== 'string' || !/^[a-zA-Z0-9_-]{1,140}$/.test(raw.lastLessonId)))
    throw new Error('Invalid recent-lesson reference in backup');
  return {
    format: BACKUP_FORMAT, version: 1, exportedAt: raw.exportedAt,
    personalLessons,
    progress: checkedMap(raw.progress, parseProgress, 'practice progress'),
    reviews: checkedMap(raw.reviews, parseReviewSchedule, 'scheduled review'),
    readingPositions: checkedMap(raw.readingPositions, parseReadingPositions, 'reading position'),
    lastLessonId: raw.lastLessonId,
  };
}
