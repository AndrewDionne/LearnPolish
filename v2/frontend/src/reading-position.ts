export const READING_POSITION_KEY = 'ptp-v2-reading-position';
export type ReadingPositions = Record<string, number>;

export function parseReadingPositions(raw: string | null): ReadingPositions {
  if (!raw) return {};
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    const result: ReadingPositions = {};
    for (const [id, number] of Object.entries(parsed)) {
      if (id !== '__proto__' && Number.isSafeInteger(number) && Number(number) >= 0) result[id] = number as number;
    }
    return result;
  } catch {
    return {};
  }
}

export function safeReadingPosition(positions: ReadingPositions, lessonId: string, itemCount: number): number {
  if (itemCount <= 0) return 0;
  const stored = positions[lessonId] || 0;
  return Math.min(Math.max(0, stored), itemCount - 1);
}
