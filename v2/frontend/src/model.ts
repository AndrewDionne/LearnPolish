export type LessonKind = 'vocabulary' | 'reading' | 'sounds';

export type LessonItem = {
  id: string;
  polish: string;
  english: string;
  pronunciation?: string;
  title?: string;
  audio?: string;
};

export type Lesson = {
  schemaVersion: 1;
  id: string;
  title: string;
  kind: LessonKind;
  items: LessonItem[];
  source: 'legacy' | 'personal';
  needsReview?: boolean;
};

export type LessonManifest = { schemaVersion: 1; lessons: Lesson[] };

export function validateLesson(value: unknown): value is Lesson {
  if (!value || typeof value !== 'object') return false;
  const x = value as Partial<Lesson>;
  return x.schemaVersion === 1 &&
    typeof x.id === 'string' && x.id.length > 0 &&
    typeof x.title === 'string' && x.title.length > 0 &&
    ['vocabulary', 'reading', 'sounds'].includes(String(x.kind)) &&
    (x.source === 'legacy' || x.source === 'personal') &&
    Array.isArray(x.items) && x.items.length > 0 &&
    x.items.every((item: LessonItem) =>
      !!item && typeof item.id === 'string' &&
      typeof item.polish === 'string' && item.polish.trim().length > 0 &&
      typeof item.english === 'string' && item.english.trim().length > 0 &&
      (item.audio === undefined || typeof item.audio === 'string')
    );
}

export function parseManifest(value: unknown): Lesson[] {
  if (!value || typeof value !== 'object') throw new Error('Missing lesson manifest');
  const data = value as Partial<LessonManifest>;
  if (data.schemaVersion !== 1 || !Array.isArray(data.lessons) || !data.lessons.every(validateLesson)) {
    throw new Error('Invalid lesson data — no content has been loaded');
  }
  if (new Set(data.lessons.map(x => x.id)).size !== data.lessons.length) {
    throw new Error('Duplicate lesson IDs');
  }
  return data.lessons;
}

export function lessonLabel(kind: LessonKind) {
  return kind === 'reading' ? 'Reading' : kind === 'sounds' ? 'Polish sounds' : 'Vocabulary';
}
