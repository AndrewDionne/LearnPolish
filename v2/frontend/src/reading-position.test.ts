import { describe, expect, test } from 'vitest';
import { parseReadingPositions, safeReadingPosition } from './reading-position';

describe('reading position', () => {
  test('loads and clamps the last passage', () => {
    const saved = parseReadingPositions('{"story":3,"bad":-1,"odd":1.5}');
    expect(saved).toEqual({ story: 3 });
    expect(safeReadingPosition(saved, 'story', 2)).toBe(1);
    expect(safeReadingPosition(saved, 'story', 9)).toBe(3);
    expect(safeReadingPosition(saved, 'new', 9)).toBe(0);
  });
  test('malformed data is ignored', () => {
    expect(parseReadingPositions('broken')).toEqual({});
  });
});
