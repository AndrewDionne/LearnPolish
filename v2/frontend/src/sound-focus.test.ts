import { describe, expect, test } from 'vitest';
import { focusedPolishParts } from './SoundContrastDeck';
import type { LessonItem } from './model';

function sample(polish: string, soundFocus?: string): LessonItem {
  return {id: 'sample:0',polish,english:'test',soundFocus};
}

describe('Sound Lab authored focus rendering',()=>{
  test('does not replace or alter the original Polish word',()=>{
    for(const [word,focus] of [
      ['Cztery','Cz'],['Pięć','ć'],['Sześć','Sz'],
      ['Siedem','Si'],['Śródmieście','Ś'],['Rzeszów','Rz'],
      ['Zielona Góra','Zi'],['Mateusz Woźniak','ź'],
      ['ulica Świętokrzyska','krzy'],['Czy mogę to przymierzyć?','przy']
    ] as const){
      const parts=focusedPolishParts(sample(word,focus));
      expect(parts).not.toBeNull();
      expect(parts!.before+parts!.focus+parts!.after).toBe(word);
      expect(parts!.focus).toBe(focus);
    }
  });
  test('missing or ambiguous focus never creates a misleading highlight',()=>{
    expect(focusedPolishParts(sample('Siedem'))).toBeNull();
    expect(focusedPolishParts(sample('Siedem','xyz'))).toBeNull();
    expect(focusedPolishParts(sample('Siedem','e'))).toBeNull();
  });
});
