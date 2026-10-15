import assert from 'node:assert/strict';
import { test } from 'node:test';
import { migrateLesson, buildContent } from './prepare-content.mjs';

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

test('full migration retains the complete legacy inventory', () => {
  const report = buildContent();
  assert.equal(report.lessons, 23);
  assert.equal(report.items, 488);
  assert.equal(report.reading, 6);
  assert.equal(report.sounds, 3);
  assert.ok(report.audioCopied > 0);
});
