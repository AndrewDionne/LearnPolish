export type LessonKind = 'vocabulary' | 'reading' | 'sounds';

export type SoundGroup = { id: string; label: string; ipa: string; hint: string; itemIds: string[] };

export type ComprehensionCheck = {
  prompt: string;
  options: [string, string, string];
  correctIndex: number;
  feedback: string;
};

export type ReadingProgression = { order: number; stage: 'foundations' | 'daily-life' | 'getting-around'; goal: string };
/** Explicitly validated learning difficulty only; missing defaults to beginner XP. */
export type LearningDifficulty = 1 | 2 | 3 | 4 | 5;

export type LessonItem = {
  id: string;
  polish: string;
  english: string;
  pronunciation?: string;
  title?: string;
  audio?: string;
  soundGroupId?: string;
  comprehension?: ComprehensionCheck;
};

export type Lesson = {
  schemaVersion: 1;
  id: string;
  title: string;
  kind: LessonKind;
  items: LessonItem[];
  source: 'legacy' | 'personal' | 'curated';
  intro?: string;
  soundGroups?: SoundGroup[];
  progression?: ReadingProgression;
  difficultyTier?: LearningDifficulty;
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
    (x.source === 'legacy' || x.source === 'personal' || x.source === 'curated') &&
    Array.isArray(x.items) && x.items.length > 0 &&
    x.items.every((item: LessonItem) =>
      !!item && typeof item.id === 'string' &&
      typeof item.polish === 'string' && item.polish.trim().length > 0 &&
      typeof item.english === 'string' && item.english.trim().length > 0 &&
      (item.audio === undefined || typeof item.audio === 'string') &&
      (item.soundGroupId === undefined || typeof item.soundGroupId === 'string') &&
      (item.comprehension === undefined || (
        x.kind === 'reading' && !!item.comprehension &&
        typeof item.comprehension.prompt === 'string' && item.comprehension.prompt.length >= 12 &&
        Array.isArray(item.comprehension.options) && item.comprehension.options.length === 3 &&
        item.comprehension.options.every(option => typeof option === 'string' && option.trim().length > 1) &&
        new Set(item.comprehension.options.map(option => option.trim().toLowerCase())).size === 3 &&
        Number.isInteger(item.comprehension.correctIndex) &&
        item.comprehension.correctIndex >= 0 && item.comprehension.correctIndex <= 2 &&
        typeof item.comprehension.feedback === 'string' && item.comprehension.feedback.length >= 10
      ))
    ) &&
    (x.difficultyTier === undefined || [1,2,3,4,5].includes(x.difficultyTier)) &&
    (x.progression === undefined || (
      x.kind === 'reading' && Number.isInteger(x.progression.order) &&
      x.progression.order >= 1 &&
      ['foundations', 'daily-life', 'getting-around'].includes(x.progression.stage) &&
      typeof x.progression.goal === 'string' && x.progression.goal.length >= 10
    )) &&
    (x.soundGroups === undefined || (
      x.kind === 'sounds' && Array.isArray(x.soundGroups) &&
      x.soundGroups.length >= 2 && x.soundGroups.every(group =>
        !!group && typeof group.id === 'string' && group.id.length > 0 &&
        typeof group.label === 'string' && typeof group.ipa === 'string' &&
        typeof group.hint === 'string' && Array.isArray(group.itemIds) &&
        group.itemIds.length >= 2 && group.itemIds.every(id =>
          typeof id === 'string' && x.items?.some(item => item.id === id && item.soundGroupId === group.id)
        )
      )
    ));
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
