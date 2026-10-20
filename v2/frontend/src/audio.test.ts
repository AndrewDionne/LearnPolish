import { describe, expect, it } from 'vitest';
import { AUDIO_RATES } from './audio';

describe('Polish lesson playback rates', () => {
  it('offers only natural, non-accelerated learning speeds', () => {
    expect(AUDIO_RATES).toEqual([0.75, 0.85, 1]);
    expect(AUDIO_RATES.every(speed => speed > 0.5 && speed <= 1)).toBe(true);
    expect([...AUDIO_RATES].sort((a, b) => a - b)).toEqual([...AUDIO_RATES]);
  });
});
