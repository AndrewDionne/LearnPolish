import { describe, expect, test } from 'vitest';
import { downloadableAudio } from './offline';
import type { Lesson } from './model';

describe('offline manifest selection', () => {
  test('includes only existing reference audio and deduplicates entries', () => {
    const lesson: Lesson = {
      schemaVersion: 1, id: 'g', title: 'Greetings', kind: 'vocabulary', source: 'legacy',
      items: [
        { id: 'g:0', polish: 'Tak', english: 'Yes', audio: 'generated/audio/g/0.mp3' },
        { id: 'g:1', polish: 'Nie', english: 'No', audio: 'generated/audio/g/0.mp3' },
        { id: 'g:2', polish: 'Dobrze', english: 'Good' },
      ],
    };
    expect(downloadableAudio(lesson)).toEqual(['generated/audio/g/0.mp3']);
  });
});
