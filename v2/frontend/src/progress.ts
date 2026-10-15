export type Attempt = { seen: number; remembered: number; needsPractice: number; lastSeen: string };
export type Progress = Record<string, Attempt>;
export const STORAGE_KEY = 'ptp-v2-progress';

export function parseProgress(raw: string | null): Progress {
  if (!raw) return {};
  try {
    const data: unknown = JSON.parse(raw);
    if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
    const result: Progress = {};
    for (const [key, value] of Object.entries(data)) {
      if (key === '__proto__' || !value || typeof value !== 'object') continue;
      const a = value as Partial<Attempt>;
      if (![a.seen, a.remembered, a.needsPractice].every(x => Number.isSafeInteger(x) && Number(x) >= 0) ||
          typeof a.lastSeen !== 'string') continue;
      result[key] = { seen: a.seen!, remembered: a.remembered!, needsPractice: a.needsPractice!, lastSeen: a.lastSeen };
    }
    return result;
  } catch { return {}; }
}

export function recordAttempt(progress: Progress, id: string, remembered: boolean, isoTime: string): Progress {
  const old = progress[id] || { seen: 0, remembered: 0, needsPractice: 0, lastSeen: isoTime };
  return {
    ...progress,
    [id]: {
      seen: old.seen + 1,
      remembered: old.remembered + (remembered ? 1 : 0),
      needsPractice: old.needsPractice + (remembered ? 0 : 1),
      lastSeen: isoTime,
    },
  };
}

export function recallRate(progress: Progress): number {
  const values = Object.values(progress);
  const remembered = values.reduce((sum, x) => sum + x.remembered, 0);
  const seen = values.reduce((sum, x) => sum + x.seen, 0);
  return seen ? Math.round(100 * remembered / seen) : 0;
}
