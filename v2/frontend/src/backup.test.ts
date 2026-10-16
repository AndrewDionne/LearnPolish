import { describe, expect, test } from 'vitest';
import { makeBackup, parseBackup } from './backup';
import { recordAttempt } from './progress';
import { recordReview } from './review';
import { makePersonalLesson } from './personal';

const lesson = makePersonalLesson({
  title:'Small lesson',kind:'vocabulary',items:[{polish:'Cześć',english:'Hello'}],
},undefined,()=>'stable');

const backup = makeBackup({
  personalLessons:[lesson],
  progress:recordAttempt({},lesson.items[0].id,true,'2026-10-16T08:00:00Z'),
  reviews:recordReview({},lesson.items[0].id,true,'2026-10-16T08:00:00Z'),
  readingPositions:{Basic_01R:2},
  lastLessonId:lesson.id,
},'2026-10-16T08:01:00Z');

describe('full local-data backup and restore',()=>{
  test('round trip keeps identifiers, schedule, progress and reading position',()=>{
    expect(parseBackup(JSON.parse(JSON.stringify(backup)))).toEqual(backup);
  });
  test('rejects corrupted, unknown-version and executable media references',()=>{
    expect(()=>parseBackup({format:'not-us',version:1})).toThrow(/not a supported/);
    expect(()=>parseBackup({...backup,version:2})).toThrow(/not a supported/);
    expect(()=>parseBackup({...backup,personalLessons:[{...lesson,items:[{...lesson.items[0],audio:'https://external.invalid/a.mp3'}]}]})).toThrow(/text only/);
    expect(()=>parseBackup({...backup,progress:{'unsafe':{seen:-1,remembered:0,needsPractice:0,lastSeen:'x'}}})).toThrow(/Invalid practice progress/);
    expect(()=>parseBackup({...backup,reviews:{'unsafe':{streak:100,dueAt:'x',lastReviewedAt:'x',attempts:0}}})).toThrow(/Invalid scheduled review/);
  });
  test('export drops personal lesson media fields',()=>{
    const sample = { ...lesson, items:[{...lesson.items[0], audio:'generated/audio/words/1.mp3'}] };
    const data=makeBackup({...backup, personalLessons:[sample]},backup.exportedAt);
    expect(data.personalLessons[0].items[0].audio).toBeUndefined();
  });
  test('rejects duplicate personal identifiers',()=>{
    expect(()=>parseBackup({...backup,personalLessons:[lesson,lesson]})).toThrow(/duplicate/);
  });
});
