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
  assert.equal(report.lessons, 25);
  assert.equal(report.items, 478);
  assert.equal(report.reading, 6);
  assert.equal(report.sounds, 4);
  assert.equal(report.curatedAudioReferences, 22);
  assert.equal(report.authoredReadingChecks, 24);
  assert.equal(report.readingPathwayLessons, 6);
  assert.equal(report.audioCopied, 455);
  assert.equal(report.missingAudio, 1);
  assert.deepEqual(report.legacyGroupedSoundSetsRetired,
    ['letter_recognition_1', 'letter_recognition_2', 'letter_recognition_3']);
  const catalog = JSON.parse(fs.readFileSync(path.resolve('public/generated/lessons.json'), 'utf8')).lessons;
  // Pronunciation latency target appears in the normal Library and in the
  // authenticated server's authoritative catalog, without synthetic audio.
  const spoken = catalog.find(x => x.id === 'speak_swietokrzyska');
  assert.equal(spoken?.kind, 'vocabulary');
  assert.equal(spoken?.source, 'curated');
  assert.deepEqual(spoken?.items.map(({id,polish})=>({id,polish})), [
    {id:'speak_swietokrzyska:0',polish:'Świętokrzyska'},
  ]);
  assert.equal(spoken.items[0].audio, undefined);
  // ONE curated source for English-friendly cues in Speak and the offline
  // sound-similarity review. Polish segmentation must never drift.
  const shared = JSON.parse(fs.readFileSync(path.resolve('../content/pronunciation-swietokrzyska.json'),'utf8'));
  const item = spoken.items[0];
  assert.deepEqual(item.pronunciationGuide.syllables,shared.syllables);
  assert.equal(item.pronunciationGuide.stressIndex,2);
  assert.equal(item.pronunciationGuide.reviewStatus,'needs_native_speaker_review');
  assert.equal(item.pronunciation,shared.syllables.map(s=>s.englishCue).join(' · '));
  assert.equal(shared.syllables.map(s=>s.polish).join(''),item.polish);
  assert.deepEqual(shared.syllables.map(s=>s.englishCue),['shfyehn','toh','KSHIH','skah']);
  const reading = catalog.filter(x => x.kind === 'reading');
  assert.deepEqual(reading.map(x => x.progression.order).sort((a,b)=>a-b), [1,2,3,4,5,6]);
  assert.equal(reading.reduce((count,x) => count + x.items.filter(i => !!i.comprehension).length,0),24);
  for (const item of reading.flatMap(x => x.items).filter(x => !!x.comprehension)) {
    assert.equal(item.comprehension.options.length,3);
    assert.equal(new Set(item.comprehension.options).size,3);
    assert.ok(item.audio);
  }
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


test('authored reading questions reject a changed or mismatched Polish sentence', async () => {
  const fs = await import('node:fs');
  const path = await import('node:path');
  const { attachReadingCurriculum } = await import('./prepare-content.mjs');
  const definitions = JSON.parse(fs.readFileSync(path.resolve('../../v2/content/reading-checks.json'),'utf8'));
  const lesson = {id:'Basic_01R',kind:'reading',items:[
    {polish:'WRONG TEXT',audio:'generated/audio/Basic_01R/0.mp3'}
  ]};
  assert.throws(
    () => attachReadingCurriculum([lesson], {schemaVersion:1,curricula:[{...definitions.curricula[0]}]}),
    /Invalid or mismatched reading check|Reading curriculum/,
  );
});
