export type LessonKind = 'vocabulary' | 'reading' | 'sounds';

export type SoundGroup = { id: string; label: string; ipa: string; hint: string; itemIds: string[] };

export type ComprehensionCheck = {
  prompt: string;
  options: [string, string, string];
  correctIndex: number;
  feedback: string;
};

export type ReadingProgression = { order: number; stage: 'foundations' | 'daily-life' | 'getting-around'; goal: string };
export type MicroDialogue = {
  id: string;
  title: string;
  speakers: {A:string; B:string};
  turns: {itemId:string; speaker:'A'|'B'}[];
};
/** Explicitly validated learning difficulty only; missing defaults to beginner XP. */
export type LearningDifficulty = 1 | 2 | 3 | 4 | 5;

export type EnglishPronunciationGuide = {
  syllables: {polish:string;englishCue:string;letterFocus:string;tip:string}[];
  stressIndex: number;
  qualification: string;
  reviewStatus: 'needs_native_speaker_review';
};

export type PronunciationSegments = {method:'authored-v1'|'editorial-draft-v1'|'draft-orthographic-v1';segments:string[]};

export type LessonItem = {
  id: string;
  polish: string;
  english: string;
  pronunciation?: string;
  pronunciationGuide?: EnglishPronunciationGuide;
  /** Exact textual grouping. Draft segments are not speaker-verified Polish syllables. */
  pronunciationSegments?: PronunciationSegments;
  /** Authored optional route to an existing recorded sound exercise, not a diagnosis. */
  soundPractice?: {lessonId:string;groupId:string;label:string};
  title?: string;
  audio?: string;
  /** Existing written prompt/audio requires exact native verification before scoring. */
  referenceReview?: 'practice_only';
  soundGroupId?: string;
  /** Curated graphemes to notice in the existing sound example, not an acoustic score. */
  soundFocus?: string;
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
  /** Optional exact-source dialogue practice; not a separate lesson or XP source. */
  microDialogues?: MicroDialogue[];
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
      (item.soundPractice === undefined || (
        !!item.soundPractice &&
        typeof item.soundPractice.lessonId === 'string' && item.soundPractice.lessonId.length > 0 &&
        typeof item.soundPractice.groupId === 'string' && item.soundPractice.groupId.length > 0 &&
        typeof item.soundPractice.label === 'string' && item.soundPractice.label.length > 0
      )) &&
      (item.pronunciationSegments === undefined || (
        !!item.pronunciationSegments &&
        ['authored-v1','editorial-draft-v1','draft-orthographic-v1'].includes(item.pronunciationSegments.method) &&
        Array.isArray(item.pronunciationSegments.segments) &&
        item.pronunciationSegments.segments.length >= 1 &&
        item.pronunciationSegments.segments.length <= 32 &&
        item.pronunciationSegments.segments.every(part=>typeof part==='string' && part.length>0) &&
        item.pronunciationSegments.segments.join('')===item.polish
      )) &&
      (item.pronunciationGuide === undefined || (
        !!item.pronunciationGuide &&
        Array.isArray(item.pronunciationGuide.syllables) &&
        item.pronunciationGuide.syllables.length >= 2 &&
        item.pronunciationGuide.syllables.length <= 12 &&
        item.pronunciationGuide.syllables.every(segment =>
          !!segment && typeof segment.polish === 'string' && segment.polish.length > 0 &&
          typeof segment.englishCue === 'string' && segment.englishCue.trim().length > 0 &&
          typeof segment.letterFocus === 'string' && segment.letterFocus.trim().length > 0 &&
          typeof segment.tip === 'string' && segment.tip.trim().length > 0
        ) &&
        item.pronunciationGuide.syllables.map(segment => segment.polish).join('') === item.polish &&
        Number.isInteger(item.pronunciationGuide.stressIndex) &&
        item.pronunciationGuide.stressIndex >= 0 &&
        item.pronunciationGuide.stressIndex < item.pronunciationGuide.syllables.length &&
        typeof item.pronunciationGuide.qualification === 'string' &&
        item.pronunciationGuide.qualification.length > 0 &&
        item.pronunciationGuide.reviewStatus === 'needs_native_speaker_review'
      )) &&
      (item.audio === undefined || typeof item.audio === 'string') &&
      (item.referenceReview === undefined || (
        x.kind === 'vocabulary' && item.referenceReview === 'practice_only'
      )) &&
      (item.soundGroupId === undefined || typeof item.soundGroupId === 'string') &&
      (item.soundFocus === undefined || (
        x.kind === 'sounds' && typeof item.soundFocus === 'string' &&
        item.soundFocus.length > 0 && item.soundFocus.length <= 8 &&
        !/\s/u.test(item.soundFocus) &&
        item.polish.includes(item.soundFocus) &&
        item.polish.indexOf(item.soundFocus, item.polish.indexOf(item.soundFocus) + item.soundFocus.length) === -1
      )) &&
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
    (x.microDialogues === undefined || (
      x.kind === 'reading' && Array.isArray(x.microDialogues) &&
      x.microDialogues.length >= 1 && x.microDialogues.length <= 8 &&
      new Set(x.microDialogues.map(dialogue=>dialogue.id)).size === x.microDialogues.length &&
      x.microDialogues.every(dialogue=>
        !!dialogue && typeof dialogue.id === 'string' && /^[a-z0-9-]+$/.test(dialogue.id) &&
        typeof dialogue.title === 'string' && dialogue.title.trim().length >= 5 &&
        typeof dialogue.speakers?.A === 'string' && !!dialogue.speakers.A.trim() &&
        typeof dialogue.speakers?.B === 'string' && !!dialogue.speakers.B.trim() &&
        Array.isArray(dialogue.turns) && dialogue.turns.length >= 2 && dialogue.turns.length <= 4 &&
        dialogue.turns.every((turn,i) => {
          const itemIndex=x.items?.findIndex(item=>item.id===turn.itemId) ?? -1;
          const previous=i > 0 ? (x.items?.findIndex(item=>item.id===dialogue.turns[i-1].itemId) ?? -1) : -1;
          return itemIndex >= 0 && !!x.items?.[itemIndex].audio &&
            x.items?.[itemIndex].referenceReview !== 'practice_only' &&
            turn.speaker === (i % 2 === 0 ? 'A' : 'B') &&
            (i===0 || itemIndex===previous+1);
        })
      )
    )) &&
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
  // Cross-reference deliberate links; never render phantom/misdirected sound drills.
  const lessonsById = new Map(data.lessons.map(lesson => [lesson.id, lesson]));
  for (const lesson of data.lessons) for (const item of lesson.items) {
    const focus = item.soundPractice;
    if (!focus) continue;
    const destination = lessonsById.get(focus.lessonId);
    const group = destination?.soundGroups?.find(g => g.id === focus.groupId);
    if (destination?.kind !== 'sounds' || !group?.itemIds.length ||
        !group.itemIds.every(id => destination.items.some(ex => ex.id === id && !!ex.audio))) {
      throw new Error('Invalid sound-practice destination for ' + item.id);
    }
  }
  return data.lessons;
}

export function lessonLabel(kind: LessonKind) {
  return kind === 'reading' ? 'Reading' : kind === 'sounds' ? 'Polish sounds' : 'Vocabulary';
}
