import type { Lesson } from './model';

export type ReviewEntry = {
  streak: number;
  dueAt: string;
  lastReviewedAt: string;
  attempts: number;
};
export type ReviewSchedule = Record<string, ReviewEntry>;
export const REVIEW_STORAGE_KEY = 'ptp-v2-review-schedule';
const DAY = 24 * 60 * 60 * 1000;
const INTERVALS = [1, 3, 7, 14, 30, 60, 90];

export function parseReviewSchedule(raw: string | null): ReviewSchedule {
  if (!raw) return {};
  try {
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
    const result: ReviewSchedule = {};
    for (const [key, rawEntry] of Object.entries(value)) {
      if (key === '__proto__' || !rawEntry || typeof rawEntry !== 'object') continue;
      const entry = rawEntry as Partial<ReviewEntry>;
      if (!Number.isInteger(entry.streak) || Number(entry.streak) < 0 || Number(entry.streak) > INTERVALS.length ||
          !Number.isSafeInteger(entry.attempts) || Number(entry.attempts) < 1 ||
          typeof entry.dueAt !== 'string' || !Number.isFinite(Date.parse(entry.dueAt)) ||
          typeof entry.lastReviewedAt !== 'string' || !Number.isFinite(Date.parse(entry.lastReviewedAt))) continue;
      result[key] = entry as ReviewEntry;
    }
    return result;
  } catch { return {}; }
}

export function recordReview(schedule: ReviewSchedule, id: string, remembered: boolean, isoTime: string): ReviewSchedule {
  const time = Date.parse(isoTime);
  if (!id || !Number.isFinite(time)) throw new Error('Review needs a valid item and timestamp');
  const old = schedule[id];
  const streak = remembered ? Math.min((old?.streak || 0) + 1, INTERVALS.length) : 0;
  // A missed item is available again immediately, rather than being falsely "mastered".
  const interval = remembered ? INTERVALS[streak - 1] * DAY : 0;
  return {
    ...schedule,
    [id]: {
      streak, dueAt: new Date(time + interval).toISOString(),
      lastReviewedAt: new Date(time).toISOString(),
      attempts: (old?.attempts || 0) + 1,
    },
  };
}

export function dueItems(lesson: Lesson, schedule: ReviewSchedule, nowIso: string) {
  const time = Date.parse(nowIso);
  if (!Number.isFinite(time)) return [];
  return lesson.items.filter(item => {
    const review = schedule[item.id];
    return !!review && Date.parse(review.dueAt) <= time;
  });
}

export function countDue(lessons: Lesson[], schedule: ReviewSchedule, nowIso: string) {
  return lessons.reduce((total, lesson) => total + dueItems(lesson, schedule, nowIso).length, 0);
}

export function nextDue(lessons: Lesson[], schedule: ReviewSchedule, nowIso: string): string | null {
  const now = Date.parse(nowIso);
  const validIds = new Set(lessons.flatMap(lesson => lesson.items.map(item => item.id)));
  const candidates = Object.entries(schedule)
    .filter(([id, entry]) => validIds.has(id) && Date.parse(entry.dueAt) > now)
    .map(([, entry]) => entry.dueAt).sort();
  return candidates[0] || null;
}
