import {describe,expect,test} from 'vitest';
import {researchWavFilename} from './research';

describe('private speech benchmark export identities', () => {
  test('round trips an exact curated or reading lesson item id', () => {
    expect(researchWavFilename('Conversation_1:0','2026-10-16T19:42:18.123Z'))
      .toBe('ptp-speech-v1--Conversation_1%3A0--20261016T194218123Z.wav');
    expect(researchWavFilename('contrast_c_cz_cie:c:0','2026-10-16T19:42:18.123Z'))
      .toContain('contrast_c_cz_cie%3Ac%3A0');
  });
  test('prevents unsafe identifiers and timestamp spoofing',()=>{
    expect(()=>researchWavFilename('../recording','2026-10-16T19:42:18.123Z')).toThrow();
    expect(()=>researchWavFilename('item 1','2026-10-16T19:42:18.123Z')).toThrow();
    expect(()=>researchWavFilename('item:1','yesterday')).toThrow();
  });
});
