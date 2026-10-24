import assert from 'node:assert/strict';
import { test } from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import { migrateLesson, buildContent, buildSoundCurriculum, attachReferenceReview, attachMicroDialogues, attachLibraryCatalog } from './prepare-content.mjs';
import {inspectSpeakCatalog,printAuditMarkdown} from './speak-readiness.mjs';

test('migrates vocabulary into versioned, stable IDs', () => {
  const lesson = migrateLesson('numbers_1-20.json', { cards: [{ phrase: 'Jeden', meaning: 'One', pronunciation: 'YEH-den' }] });
  assert.equal(lesson.schemaVersion, 1);
  assert.equal(lesson.id, 'numbers_1-20');
  assert.equal(lesson.kind, 'vocabulary');
  assert.deepEqual(lesson.items[0], { id: 'numbers_1-20:0', polish: 'Jeden', english: 'One', pronunciation: 'YEH-den' });
});

test('library editorial audit covers all 26 stable source IDs without changing their items',()=>{
  buildContent();
  const catalog=JSON.parse(fs.readFileSync(path.resolve('../content/library-catalog.json'),'utf8'));
  const built=JSON.parse(fs.readFileSync(path.resolve('public/generated/lessons.json'),'utf8')).lessons;
  assert.equal(catalog.lessons.length,26);
  assert.deepEqual(new Set(catalog.lessons.map(entry=>entry.id)),
    new Set(built.map(lesson=>lesson.id)));
  assert.ok(built.every(lesson=>lesson.title && lesson.description && lesson.curriculum));
  for(const lesson of built){
    const author=catalog.lessons.find(entry=>entry.id===lesson.id);
    assert.equal(lesson.title,author.title);
    assert.equal(lesson.description,author.description);
    assert.deepEqual(lesson.curriculum,author.curriculum);
  }
  assert.equal(built.find(lesson=>lesson.id==='Numbers_20-100').title,'Numbers Beyond 20');
  assert.equal(built.find(lesson=>lesson.id==='Districts_of_Warszawa').title,'Warsaw Districts and Landmarks');
  assert.equal(built.find(lesson=>lesson.id==='speak_swietokrzyska').curriculum.stage,'practice');

  const original=structuredClone(built).map(lesson=>({...lesson,title:'source title',description:undefined,curriculum:undefined}));
  const idsBefore=original.map(lesson=>[lesson.id,lesson.items.map(item=>[item.id,item.polish,item.audio])]);
  const result=attachLibraryCatalog(original,catalog);
  assert.deepEqual(result,{fundamentals:12,basic:7,learning:6,practice:1});
  assert.deepEqual(original.map(lesson=>[lesson.id,lesson.items.map(item=>[item.id,item.polish,item.audio])]),idsBefore);

  const duplicate=structuredClone(catalog);
  duplicate.lessons[1].id=duplicate.lessons[0].id;
  assert.throws(()=>attachLibraryCatalog(structuredClone(original),duplicate),/Invalid or missing/);
  const missing=structuredClone(catalog);missing.lessons.pop();
  assert.throws(()=>attachLibraryCatalog(structuredClone(original),missing),/26 original/);
  const wrongTrack=structuredClone(catalog);
  wrongTrack.lessons[0].curriculum.track='conversations-reading';
  assert.throws(()=>attachLibraryCatalog(structuredClone(original),wrongTrack),/Invalid or missing/);
  const badDescription=structuredClone(catalog);
  badDescription.lessons[0].description='x';
  assert.throws(()=>attachLibraryCatalog(structuredClone(original),badDescription),/Invalid or missing/);
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
  assert.equal(report.lessons, 26);
  assert.deepEqual(report.curriculumCounts,{
    fundamentals:12,basic:7,learning:6,practice:1,
  });
  assert.equal(report.referenceReviewItems,14);
  assert.equal(report.items, 482);
  assert.equal(report.pronunciationGrouping.total,482);
  assert.equal(report.pronunciationGrouping.authored,1);
  assert.ok(report.pronunciationGrouping.editorial>=19);
  assert.equal(report.pronunciationGrouping.total,
    report.pronunciationGrouping.authored+
    report.pronunciationGrouping.editorial+
    report.pronunciationGrouping.drafts);
  assert.equal(report.reading, 6);
  assert.equal(report.sounds, 5);
  assert.equal(report.curatedAudioReferences, 26);
  assert.equal(report.authoredReadingChecks, 24);
  assert.equal(report.microDialogues,3);
  assert.equal(report.readingPathwayLessons, 6);
  assert.equal(report.audioCopied, 455);
  assert.equal(report.missingAudio, 1);
  assert.deepEqual(report.legacyGroupedSoundSetsRetired,
    ['letter_recognition_1', 'letter_recognition_2', 'letter_recognition_3']);
  const catalog = JSON.parse(fs.readFileSync(path.resolve('public/generated/lessons.json'), 'utf8')).lessons;
  assert.equal(catalog.flatMap(lesson=>lesson.items).filter(item=>Object.hasOwn(item,'syllableAudio')).length,0,
    'Word-only pronunciation must never introduce syllable audio metadata');
  const audit=inspectSpeakCatalog({schemaVersion:1,lessons:catalog});
  assert.deepEqual({
    modules:audit.summary.modules,
    speakModules:audit.summary.speakModules,
    readingModules:audit.summary.readingModules,
    items:audit.summary.items,
    spokenItems:audit.summary.spokenItems,
    readingItems:audit.summary.readingItems,
    withAudio:audit.summary.withAudio,
    editorial:audit.summary.editorial,
    autoDraft:audit.summary.autoDraft,
    authored:audit.summary.authored,
    speakBlockedReferences:audit.summary.speakBlockedReferences,
    speakUnfinishedReferences:audit.summary.speakUnfinishedReferences,
    practiceOnlyReferences:audit.summary.practiceOnlyReferences,
  },{
    modules:26,speakModules:20,readingModules:6,items:482,
    spokenItems:431,readingItems:51,withAudio:481,
    editorial:23,autoDraft:458,authored:1,
    speakBlockedReferences:11,speakUnfinishedReferences:3,
    practiceOnlyReferences:14,
  });
  const unread=audit.modules.filter(x=>!x.speakAvailable);
  assert.equal(unread.length,6);
  assert.ok(unread.every(x=>x.kind==='reading' && x.items===x.withAudio));
  const blocked=audit.modules.flatMap(x=>x.speakAvailable?x.blockedReferences:[]);
  assert.ok(blocked.some(x=>x.polish==='Jak ma pan/pani na imię?'));
  assert.ok(blocked.some(x=>x.polish==='droga wojewódzka 634'));
  assert.ok(!blocked.some(x=>x.polish==='Świętokrzyska'));
  const unfinished=audit.modules.flatMap(x=>x.speakAvailable?x.unfinishedReferences:[]);
  assert.ok(unfinished.some(x=>x.polish==='Mam na imię…'));
  assert.ok(printAuditMarkdown(audit).includes('| Speak |'));
  assert.ok(printAuditMarkdown(audit).includes('| Read only |'));
  // Pronunciation latency target appears in the normal Library and in the
  // authenticated server's authoritative catalog, without synthetic audio.
  const spoken = catalog.find(x => x.id === 'speak_swietokrzyska');
  assert.equal(spoken?.kind, 'vocabulary');
  assert.equal(spoken?.source, 'curated');
  assert.deepEqual(spoken?.items.map(({id,polish})=>({id,polish})), [
    {id:'speak_swietokrzyska:0',polish:'Świętokrzyska'},
  ]);
  assert.equal(spoken.items[0].audio, undefined);
  const fromRoad=catalog.find(lesson=>lesson.id==='Road_Terminology');
  const ulica=fromRoad.items.find(item=>item.polish==='ulica');
  assert.deepEqual(ulica.pronunciationSegments,{
    method:'editorial-draft-v1',segments:['u','li','ca']});
  const fromConversation=catalog.find(lesson=>lesson.id==='Conversation_1');
  assert.deepEqual(fromConversation.items.filter(x=>x.referenceReview).map(x=>x.id),
    ['Conversation_1:24','Conversation_1:25']);
  assert.equal(fromConversation.items.filter(x=>x.referenceReview).length,2);
  assert.equal(catalog.flatMap(lesson=>lesson.items).filter(item=>item.referenceReview==='practice_only').length,14);
  assert.ok(fromConversation.items[24].audio && fromConversation.items[25].audio);
  assert.equal(fromConversation.items[23].referenceReview,undefined);
  const greeting=fromConversation.items.find(item=>item.polish==='Dzień dobry');
  assert.deepEqual(greeting.pronunciationSegments,{
    method:'editorial-draft-v1',segments:['Dzień ','do','bry']});
  assert.deepEqual(spoken.items[0].soundPractice,{
    lessonId:'contrast_krzy_przy',groupId:'krzy',label:'krzy'
  });
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
  const micros=reading.flatMap(lesson=>(lesson.microDialogues||[]).map(scene=>({lesson,scene})));
  assert.equal(micros.length,3);
  assert.deepEqual(micros.map(({scene})=>scene.comprehension.correctIndex),[0,1,2]);
  assert.deepEqual(micros.map(({scene})=>scene.replyPractice.correctIndex),[1,2,1]);
  for(const {lesson,scene} of micros){
    const reply=scene.replyPractice;
    assert.equal(reply.promptItemId,scene.turns[scene.turns.length-2].itemId);
    assert.equal(reply.replyItemId,scene.turns[scene.turns.length-1].itemId);
    assert.equal(reply.choiceItemIds[reply.correctIndex],reply.replyItemId);
    assert.equal(new Set(reply.choiceItemIds).size,3);
    for(const id of reply.choiceItemIds){
      const item=lesson.items.find(item=>item.id===id);
      assert.ok(item?.audio,'Reply candidate has original recording: '+id);
      assert.ok(fs.existsSync(path.join('public',item.audio)));
    }
  }
  for(const {scene} of micros){
    assert.equal(scene.comprehension.options.length,3);
    assert.ok(scene.comprehension.feedback.length>=10);
  }
  assert.deepEqual(micros.map(x=>[x.lesson.id,x.scene.id,x.scene.turns.length]),[
    ['Basic_01R','greeting-how-are-you',2],
    ['Basic_01R','greeting-name',2],
    ['Grocery_store_very_basic_shopping','buying-apples',3],
  ]);
  for (const {lesson,scene} of micros) {
    for (const turn of scene.turns) {
      const item=lesson.items.find(item=>item.id===turn.itemId);
      assert.ok(item?.audio);
      assert.ok(fs.existsSync(path.join('public',item.audio)));
      assert.equal(item.referenceReview,undefined);
    }
  }
  assert.deepEqual(reading.map(x => x.progression.order).sort((a,b)=>a-b), [1,2,3,4,5,6]);
  assert.equal(reading.reduce((count,x) => count + x.items.filter(i => !!i.comprehension).length,0),24);
  for (const item of reading.flatMap(x => x.items).filter(x => !!x.comprehension)) {
    assert.equal(item.comprehension.options.length,3);
    assert.equal(new Set(item.comprehension.options).size,3);
    assert.ok(item.audio);
  }
  const sounds = catalog.filter(x => x.kind === 'sounds');
  assert.equal(sounds.length, 5);
  const clusters = sounds.find(x => x.id === 'contrast_krzy_przy');
  assert.deepEqual(clusters.soundGroups.map(group => group.id),['krzy','przy']);
  assert.deepEqual(clusters.soundGroups.map(group => group.itemIds.length),[2,2]);
  assert.deepEqual(clusters.items.map(item => item.polish),[
    'ulica Świętokrzyska','Krzysztof Wiśniewski',
    'Przystanek autobusowy','Czy mogę to przymierzyć?'
  ]);
  assert.deepEqual(sounds.map(lesson => [lesson.id, ...lesson.soundGroups.map(group=>group.id)]),[
    ['contrast_c_cz_cie','c','cz','ci'],
    ['contrast_s_sz_sie','s','sz','si'],
    ['contrast_z_zh_zi','z','zh','zi'],
    ['contrast_l_lstroked','l','lstroked'],
    ['contrast_krzy_przy','krzy','przy']
  ]);
  for (const lesson of sounds) {
    assert.equal(lesson.source, 'curated');
    assert.equal(lesson.needsReview, true);
    assert.ok(lesson.soundGroups.every(group => group.itemIds.length >= 2));
    for (const item of lesson.items) {
      assert.ok(item.soundFocus, 'Sound Lab focus must be authored for '+item.polish);
      assert.equal(item.polish.split(item.soundFocus).length,2,
        'Exactly one matching focus in '+item.polish);
      assert.ok(item.audio?.startsWith('generated/audio/'));
      assert.ok(fs.existsSync(path.join('public', item.audio)));
      assert.ok(!item.polish.includes(',') && !item.polish.includes(' / '));
    }
  }
});

test('sound focus must match exactly one recorded Polish substring', () => {
  buildContent();
  const catalog = JSON.parse(fs.readFileSync(path.resolve('public/generated/lessons.json'),'utf8')).lessons.filter(lesson=>lesson.kind!=='sounds');
  const definitions = JSON.parse(fs.readFileSync(path.resolve('../content/sound-contrasts.json'),'utf8'));
  const bad = structuredClone(definitions);
  bad[0].groups[0].examples[0].focus='sz';
  assert.throws(() => buildSoundCurriculum(catalog,bad), /invalid or ambiguous focus letters/);
  const missing = structuredClone(definitions);
  delete missing[0].groups[0].examples[0].focus;
  assert.throws(() => buildSoundCurriculum(catalog,missing), /invalid or ambiguous focus letters/);
  const ambiguous = structuredClone(definitions);
  // "Sześć" contains two occurrences of the letter "ś"? Use existing "Siedem"'s e twice.
  ambiguous[1].groups[2].examples[1].focus='e';
  assert.throws(() => buildSoundCurriculum(catalog,ambiguous), /invalid or ambiguous focus letters/);
  const valid = buildSoundCurriculum(catalog,definitions);
  assert.equal(valid.flatMap(lesson=>lesson.items).length,26);
  const difficult=valid.find(lesson=>lesson.id==='contrast_c_cz_cie');
  assert.deepEqual(difficult.items.map(item=>item.soundFocus), ['c','c','Cz','Cz','ć','ć']);
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

test('all fourteen original source blockers are fixed-ID, content-matched and without invented MP3s',()=>{
  buildContent();
  const first=JSON.parse(fs.readFileSync(path.resolve('../content/voice-production.json'),'utf8'));
  const rest=JSON.parse(fs.readFileSync(path.resolve('../content/additional-speak-reference-blockers.json'),'utf8'));
  const built=JSON.parse(fs.readFileSync(path.resolve('public/generated/lessons.json'),'utf8'));
  const vocabulary=structuredClone(built.lessons.filter(lesson=>lesson.kind==='vocabulary' && lesson.source==='legacy'));
  const originals=new Map(vocabulary.flatMap(lesson=>lesson.items.map(item=>[item.id,{polish:item.polish,audio:item.audio}])));
  for(const lesson of vocabulary)for(const item of lesson.items)delete item.referenceReview;
  assert.equal(attachReferenceReview(vocabulary,first,rest),14);
  const reviewed=vocabulary.flatMap(lesson=>lesson.items).filter(item=>item.referenceReview==='practice_only');
  assert.equal(reviewed.length,14);
  assert.deepEqual(new Set(reviewed.map(item=>item.id)),
    new Set([...first.sourceBlockers,...rest.sourceBlockers].map(item=>item.itemId)));
  for(const item of reviewed){
    assert.deepEqual({polish:item.polish,audio:item.audio},originals.get(item.id));
  }
  const changed=structuredClone(vocabulary);
  changed.find(l=>l.id==='Road_Terminology').items[21].polish='droga wojewódzka sześćset trzydzieści cztery';
  assert.throws(()=>attachReferenceReview(changed,first,rest),/Changed or missing Speak audio review/);
  const missing=structuredClone(rest);missing.sourceBlockers.pop();
  assert.throws(()=>attachReferenceReview(vocabulary,first,missing),/Expected exact/);
  const changedIds=structuredClone(rest);changedIds.sourceBlockers[0].itemId='other:0';
  assert.throws(()=>attachReferenceReview(vocabulary,first,changedIds),/Unexpected edited/);
  const newUnreviewed=structuredClone(vocabulary);
  newUnreviewed.find(l=>l.id==='Road_Terminology').items.push({
    id:'Road_Terminology:unreviewed',polish:'Droga 999',audio:'generated/audio/Road_Terminology/99.mp3'
  });
  assert.throws(()=>attachReferenceReview(newUnreviewed,first,rest),/Unreviewed new alternative/);
  assert.ok(printAuditMarkdown(inspectSpeakCatalog(built)).includes('Practice only'));
});

test('micro-dialogue review fails closed on original Polish drift or unverified audio',()=>{
  buildContent();
  const catalog=JSON.parse(fs.readFileSync(path.resolve('public/generated/lessons.json'),'utf8'));
  const defs=JSON.parse(fs.readFileSync(path.resolve('../content/micro-dialogues.json'),'utf8'));
  const source=structuredClone(catalog.lessons.filter(lesson=>lesson.kind==='reading'));
  for(const lesson of source)delete lesson.microDialogues;
  assert.equal(attachMicroDialogues(source,defs),3);
  assert.deepEqual(source.filter(lesson=>lesson.microDialogues)
    .map(lesson=>[lesson.id,lesson.microDialogues.length]),[
    ['Basic_01R',2],['Grocery_store_very_basic_shopping',1]
  ]);
  const wrong=structuredClone(defs);
  wrong.scenes[0].turns[0].polish='Cześć, jak się masz?';
  const changed=structuredClone(catalog.lessons.filter(lesson=>lesson.kind==='reading'));
  for(const lesson of changed)delete lesson.microDialogues;
  assert.throws(()=>attachMicroDialogues(changed,wrong),/Invalid or mismatched/);
  const skipped=structuredClone(defs);
  skipped.scenes[2].turns[1].index=7;
  assert.throws(()=>attachMicroDialogues(changed,skipped),/Invalid or mismatched/);
  const badAudio=structuredClone(changed);
  badAudio.find(lesson=>lesson.id==='Basic_01R').items[0].audio=undefined;
  assert.throws(()=>attachMicroDialogues(badAudio,defs),/Invalid or mismatched/);
  const badReview=structuredClone(changed);
  badReview.find(lesson=>lesson.id==='Basic_01R').items[0].referenceReview='practice_only';
  assert.throws(()=>attachMicroDialogues(badReview,defs),/Invalid or mismatched/);
  const repeated=structuredClone(defs);
  repeated.scenes[1].turns[0].index=0;
  assert.throws(()=>attachMicroDialogues(changed,repeated),/Invalid or mismatched/);
  const absentCheck=structuredClone(defs);
  delete absentCheck.scenes[0].comprehension;
  assert.throws(()=>attachMicroDialogues(changed,absentCheck),/Invalid E2 dialogue comprehension/);
  const duplicated=structuredClone(defs);
  duplicated.scenes[2].comprehension.options[1]=duplicated.scenes[2].comprehension.options[0];
  assert.throws(()=>attachMicroDialogues(changed,duplicated),/Invalid E2 dialogue comprehension/);
  const invalidAnswer=structuredClone(defs);
  invalidAnswer.scenes[1].comprehension.correctIndex=4;
  assert.throws(()=>attachMicroDialogues(changed,invalidAnswer),/Invalid E2 dialogue comprehension/);
  const wrongReply=structuredClone(defs);
  wrongReply.scenes[2].replyPractice.correctIndex=0;
  assert.throws(()=>attachMicroDialogues(changed,wrongReply),/Invalid source-grounded E2 reply/);
  const invented=structuredClone(defs);
  invented.scenes[0].replyPractice.choices[0].polish='Wymyślona odpowiedź';
  assert.throws(()=>attachMicroDialogues(changed,invented),/Invalid source-grounded E2 reply/);
  const wrongAudio=structuredClone(changed);
  wrongAudio.find(lesson=>lesson.id==='Basic_01R').items[5].audio=undefined;
  assert.throws(()=>attachMicroDialogues(wrongAudio,defs),/Invalid source-grounded E2 reply/);
  const duplicates=structuredClone(defs);
  duplicates.scenes[1].replyPractice.choices[0]=structuredClone(duplicates.scenes[1].replyPractice.choices[1]);
  assert.throws(()=>attachMicroDialogues(changed,duplicates),/Invalid source-grounded E2 reply/);
  const sceneAlternative=structuredClone(defs);
  sceneAlternative.scenes[0].replyPractice.choices[2]={index:0,polish:'Cześć! Jak się masz?'};
  assert.throws(()=>attachMicroDialogues(changed,sceneAlternative),/Invalid source-grounded E2 reply/);
});

test('C-09 source-backed sound-ear exercises preserve real full-word MP3s and original lesson IDs',()=>{
  const report=buildContent();
  assert.equal(report.lessons,26);
  assert.equal(report.sounds,5);
  assert.equal(report.audioCopied,455);
  const plan=JSON.parse(fs.readFileSync(path.resolve('../content/sound-listening-v1.json'),'utf8'));
  const catalog=JSON.parse(fs.readFileSync(path.resolve('public/generated/lessons.json'),'utf8')).lessons;
  assert.equal(plan.status,'existing_recorded_whole_word_sound_examples_editorial_not_native_certified');
  assert.deepEqual(plan.lessons.map(x=>x.questions.length),[6,5,6,4,4]);
  const used=new Set();
  for(const practice of plan.lessons){
    const lesson=catalog.find(l=>l.id===practice.lessonId);
    assert.equal(lesson?.kind,'sounds');
    assert.equal(lesson?.source,'curated');
    for(const question of practice.questions){
      assert.ok(!used.has(question.itemId),'Each listening check uses a unique existing sound item');
      used.add(question.itemId);
      const item=lesson.items.find(i=>i.id===question.itemId);
      const group=lesson.soundGroups.find(g=>g.id===question.groupId);
      assert.ok(item && group && group.itemIds.includes(item.id));
      assert.equal(item.polish,question.expectedPolish);
      assert.equal(item.soundFocus,question.expectedFocus);
      assert.equal(item.soundGroupId,group.id);
      assert.ok(item.audio?.startsWith('generated/audio/'));
      assert.ok(fs.existsSync(path.join('public',item.audio)));
      assert.equal(item.polish.split(item.soundFocus).length,2);
    }
  }
  assert.equal(used.size,25);
  assert.ok(!used.has('contrast_s_sz_sie:sz:0'),'Avoid the ambiguous Sześć sound-family quiz');
  assert.equal(catalog.length,26,'No cloned learner lessons for sound questions');
});
