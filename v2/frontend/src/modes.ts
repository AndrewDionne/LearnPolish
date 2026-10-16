import type { Lesson, LessonItem } from './model';

export type LearningMode = 'learn' | 'read' | 'listen' | 'speak';

export function availableModes(lesson: Lesson): LearningMode[] {
  const base: LearningMode = lesson.kind === 'reading' ? 'read' : 'learn';
  const modes: LearningMode[] = lesson.kind === 'reading' ? [base] : [base, 'speak'];
  if (lesson.items.some(item => !!item.audio)) modes.push('listen');
  return modes;
}

export function itemsForMode(lesson: Lesson, mode: LearningMode): LessonItem[] {
  if (mode === 'listen') return lesson.items.filter(item => !!item.audio);
  return lesson.items;
}

export function comprehensionChoices(items: LessonItem[], current: LessonItem, index: number): string[] {
  const alternatives = [...new Set(items.map(item => item.english))]
    .filter(text => text !== current.english);
  if (alternatives.length < 1) return [];
  const offset = index % alternatives.length;
  const chosen = [...alternatives.slice(offset), ...alternatives.slice(0, offset)].slice(0, 2);
  const insert = index % (chosen.length + 1);
  chosen.splice(insert, 0, current.english);
  return chosen;
}

export function progressKey(id: string, mode: LearningMode) {
  // Keep existing Learn keys unchanged so earlier preview progress survives migration.
  return mode === 'learn' ? id : mode + ':' + id;
}

export function itemPractised(progress: Record<string, unknown>, id: string): boolean {
  return [id, 'read:' + id, 'listen:' + id].some(key => Object.hasOwn(progress, key));
}
