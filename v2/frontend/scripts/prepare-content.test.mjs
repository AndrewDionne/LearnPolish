import assert from 'node:assert/strict';
import { test } from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import { migrateLesson, buildContent, buildSoundCurriculum } from './prepare-content.mjs';

test('migrates vocabulary into versioned, stable IDs', () => {
  const lesson = migrateLesson('numbers_1-20.json', { cards: [{ phrase: 'Jeden', meaning: 'One', pronunciation: 'YEH-den' }] });
  assert.equal(lesson.schemaVersion, 1);
  assert.equal(lesson.id, 'numbers_1-20');
  assert.equal(lesson.kind, 'vocabulary');
  assert.deepEqual(lesson.items[0], { id: 'numbers_1-20:0', polish: 'Jeden', english: 'One', pronunciation: 'YEH-den' });
});

test('sound recognition sets are flagged for native-speaker review', () => {
  const lesson = migrateLesson('letter_recognition_1.json', { cards: [{ phrase: 'mąż, wąż', meaning: 'ą' }] });
  assert.equal(lesson.kind, 'sounds');
  assert.equal(lesson.needsReview, true);
});

test('rejects malformed lesson data', () => {
  assert.throws(() => migrateLesson('bad.json', { cards: [{ phrase: 'ok' }] }), /missing Polish\/English/);
  assert.throws(() => migrateLesson('empty.json', { cards: [] }), /empty/);
});

test('new catalog retires bundled sound examples while retaining all other legacy lessons and audio', () => {
  const report = buildContent();
  assert.equal(report.lessons, 24);
  assert.equal(report.items, 477);
  assert.equal(report.reading, 6);
  assert.equal(report.sounds, 4);
  assert.equal(report.curatedAudioReferences, 22);
  assert.equal(report.audioCopied, 455);
  assert.equal(report.missingAudio, 0);
  assert.deepEqual(report.legacyGroupedSoundSetsRetired,
    ['letter_recognition_1', 'letter_recognition_2', 'letter_recognition_3']);
  const catalog = JSON.parse(fs.readFileSync(path.resolve('public/generated/lessons.json'), 'utf8')).lessons;
  const sounds = catalog.filter(x => x.kind === 'sounds');
  assert.equal(sounds.length, 4);
  for (const lesson of sounds) {
    assert.equal(lesson.source, 'curated');
    assert.equal(lesson.needsReview, true);
    assert.ok(lesson.soundGroups.every(group => group.itemIds.length >= 2));
    for (const item of lesson.items) {
      assert.ok(item.audio?.startsWith('generated/audio/'));
      assert.ok(fs.existsSync(path.join('public', item.audio)));
      assert.ok(!item.polish.includes(',') && !item.polish.includes(' / '));
    }
  }
});

test('curriculum rejects incorrect audio/text mapping rather than playing mismatched speech', () => {
  assert.throws(() => buildSoundCurriculum([
    {id:'words',kind:'vocabulary',items:[{id:'words:0',polish:'plac',english:'square',audio:'generated/audio/words/0.mp3'}]},
  ], [{id:'sounds',groups:[{id:'c',label:'C',hint:'ts',examples:[{set:'words',index:0,expected:'cztery'},{set:'words',index:0,expected:'plac'}]},{id:'cz',label:'CZ',hint:'hard ch',examples:[{set:'words',index:0,expected:'plac'},{set:'words',index:0,expected:'plac'}]}]}]), /mismatched individual audio/);
});
