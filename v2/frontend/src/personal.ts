import { validateLesson } from './model';
import type { Lesson, LessonItem, LessonKind } from './model';

export const PERSONAL_STORAGE_KEY = 'ptp-v2-personal-lessons';
const MAX_LESSONS = 100;
const MAX_ITEMS = 150;

export type DraftItem = Pick<LessonItem, 'polish' | 'english'> & Partial<Pick<LessonItem, 'id' | 'pronunciation' | 'title'>>;
export type DraftLesson = { title: string; kind: LessonKind; items: DraftItem[] };

export function makePersonalLesson(draft: DraftLesson, existing?: Lesson, makeId: () => string = () => crypto.randomUUID()): Lesson {
  const title = draft.title.trim().normalize('NFC');
  if (!title || title.length > 100) throw new Error('Lesson name must be between 1 and 100 characters.');
  if (!Array.isArray(draft.items) || draft.items.length < 1 || draft.items.length > MAX_ITEMS) {
    throw new Error('Each lesson must have between 1 and 150 items.');
  }
  const id = existing?.id ?? 'personal_' + makeId();
  const items = draft.items.map((row, index) => {
    const polish = typeof row.polish === 'string' ? row.polish.trim().normalize('NFC') : '';
    const english = typeof row.english === 'string' ? row.english.trim() : '';
    if (!polish || !english) throw new Error('Item ' + (index + 1) + ' needs Polish and English text.');
    if (polish.length > 800 || english.length > 1400) throw new Error('Item ' + (index + 1) + ' is too long.');
    return {
      id: row.id && existing?.items.some(item => item.id === row.id) ? row.id : id + ':' + makeId(),
      polish,
      english,
      ...(row.pronunciation ? { pronunciation: row.pronunciation.trim() } : {}),
      ...(row.title ? { title: row.title.trim() } : {}),
    };
  });
  if (new Set(items.map(item => item.id)).size !== items.length) throw new Error('Duplicate item identifiers.');
  return { schemaVersion: 1, id, title, kind: draft.kind, items, source: 'personal' };
}

export function importPersonalLesson(json: unknown, makeId: () => string = () => crypto.randomUUID()): Lesson {
  if (!validateLesson(json)) throw new Error('Invalid Path to Polish V2 lesson format.');
  const source = json as Lesson;
  // Imported content is independent of the source ID. Audio URLs are deliberately
  // removed: untrusted external URLs and device-local paths must not be played.
  return makePersonalLesson({
    title: source.title,
    kind: source.kind,
    items: source.items.map(({ polish, english, pronunciation, title }) => ({ polish, english, pronunciation, title })),
  }, undefined, makeId);
}

export function parsePersonalLessons(raw: string | null): Lesson[] {
  if (!raw) return [];
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) return [];
    const list = value.filter((x): x is Lesson => validateLesson(x) && x.source === 'personal');
    const ids = new Set<string>();
    return list.filter(lesson => {
      if (ids.has(lesson.id) || !lesson.id.startsWith('personal_')) return false;
      ids.add(lesson.id);
      return true;
    }).slice(0, MAX_LESSONS);
  } catch { return []; }
}

export function upsertPersonalLesson(lessons: Lesson[], next: Lesson): Lesson[] {
  const found = lessons.some(x => x.id === next.id);
  if (!found && lessons.length >= MAX_LESSONS) throw new Error('The local library is full (100 personal lessons).');
  return found ? lessons.map(x => x.id === next.id ? next : x) : [...lessons, next];
}

export function toPortableLesson(lesson: Lesson): Lesson {
  // Export is plaintext content only, not audio URLs or learner progress.
  return {
    schemaVersion: 1,
    id: lesson.id,
    title: lesson.title,
    kind: lesson.kind,
    source: 'personal',
    items: lesson.items.map(({ id, polish, english, pronunciation, title }) => ({
      id, polish, english,
      ...(pronunciation ? { pronunciation } : {}),
      ...(title ? { title } : {}),
    })),
  };
}
