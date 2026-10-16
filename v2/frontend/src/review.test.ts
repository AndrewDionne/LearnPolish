import { describe, expect, test } from 'vitest';
import { countDue, dueItems, nextDue, parseReviewSchedule, recordReview } from './review';
import type { Lesson } from './model';

const lesson: Lesson = {
  schemaVersion: 1, id: 'one', title: 'One', kind: 'vocabulary', source: 'legacy',
  items: [{id: 'one:0',polish:'Tak',english:'Yes'}, {id: 'one:1',polish:'Nie',english:'No'}],
};
const now = '2026-10-16T08:00:00.000Z';

describe('deterministic spaced review', () => {
  test('first remembered item is due tomorrow, then 3 and 7 days later', () => {
    let schedule = recordReview({}, 'one:0', true, now);
    expect(schedule['one:0'].dueAt).toBe('2026-10-17T08:00:00.000Z');
    schedule = recordReview(schedule, 'one:0', true, '2026-10-17T08:00:00.000Z');
    expect(schedule['one:0'].dueAt).toBe('2026-10-20T08:00:00.000Z');
    schedule = recordReview(schedule, 'one:0', true, '2026-10-20T08:00:00.000Z');
    expect(schedule['one:0'].dueAt).toBe('2026-10-27T08:00:00.000Z');
    expect(schedule['one:0'].streak).toBe(3);
  });
  test('missed review resets streak, makes the card due and preserves attempts', () => {
    const first = recordReview({}, 'one:0', true, now);
    const missed = recordReview(first, 'one:0', false, now);
    expect(missed['one:0']).toMatchObject({streak:0, attempts:2, dueAt:now});
    expect(dueItems(lesson, missed, now).map(x => x.id)).toEqual(['one:0']);
    expect(countDue([lesson], missed, now)).toBe(1);
  });
  test('stable parsing rejects damaged fields and prototype pollution', () => {
    expect(parseReviewSchedule('{oops')).toEqual({});
    expect(parseReviewSchedule(JSON.stringify({a:{streak:-1,dueAt:now,lastReviewedAt:now,attempts:1}}))).toEqual({});
    const schedule = recordReview({}, 'one:1', false, now);
    expect(parseReviewSchedule(JSON.stringify(schedule))).toEqual(schedule);
  });
  test('next due ignores old lessons and already-due items', () => {
    let schedule = recordReview({}, 'one:0', true, now);
    schedule = recordReview(schedule, 'orphan:1', true, now);
    expect(nextDue([lesson], schedule, now)).toBe('2026-10-17T08:00:00.000Z');
  });
});
