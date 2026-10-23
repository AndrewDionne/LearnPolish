import test from 'node:test';
import assert from 'node:assert/strict';
import {loadDraftInputs,validateFoundationDraft,renderFoundationReviewSheet} from './foundation-editorial-gate.mjs';

const source=loadDraftInputs();
const fresh=()=>structuredClone(source.draft);
const validate=(draft,options)=>validateFoundationDraft(draft,source.legacy,source.contrasts,options);

test('C-02: 32 letters + 20 patterns + 42 useful F1 items + 10 bridge previews remain draft only',()=>{
 assert.deepEqual(validate(fresh()),{
  letters:32,soundPatterns:20,firstVocabulary:42,sentencePreviews:10,
  unapprovedText:true,recordedNewAudio:0,learnerFacingChanges:0
 });
});
test('review sheet is complete and explicitly pending for both sound and language',()=>{
 const out=renderFoundationReviewSheet(fresh());
 assert.match(out,/\| Ą \| mąż \|/);
 assert.match(out,/\| Ż \| żaba \|/);
 assert.match(out,/\| F0-20 \|/);
 assert.match(out,/\| F2-10 \|/);
 assert.match(out,/NEW VOICE NEEDED/);
 assert.match(out,/UNPUBLISHED AUTHOR DRAFT/);
});
test('reject incomplete alphabet, wrong Polish letters, missing letter example',()=>{
 const missing=fresh();missing.alphabet.pop();
 assert.throws(()=>validate(missing),/32-letter alphabet/);
 const changed=fresh();changed.alphabet[1].letter='A';
 assert.throws(()=>validate(changed),/32-letter alphabet/);
 const blank=fresh();blank.alphabet[30].candidateWord='';
 assert.throws(()=>validate(blank),/32-letter alphabet/);
});
test('no unreviewed names, phoneme IPA, bogus MP3 or text/rights approval',()=>{
 for(const field of ['letterName','primarySoundIPA','audio']){
  const draft=fresh();draft.alphabet[1][field]=field==='audio'?'a.mp3':'invented';
  assert.throws(()=>validate(draft),/32-letter alphabet/);
 }
 for(const key of Object.keys(source.draft.approval)){
  const draft=fresh();draft.approval[key]=true;
  assert.throws(()=>validate(draft),/approval/);
 }
});
test('reject edited, deleted, prerecorded or fake-reviewed sound examples',()=>{
 const removed=fresh();removed.patterns.pop();
 assert.throws(()=>validate(removed),/twenty planned/);
 const fake=fresh();fake.patterns[4].audio='fake.mp3';
 assert.throws(()=>validate(fake),/unreviewed phonics/);
 const approved=fresh();approved.patterns[1].reviewed=true;
 assert.throws(()=>validate(approved),/unreviewed phonics/);
 const lost=fresh();lost.originalContrastLessonIds.pop();
 assert.throws(()=>validate(lost),/original whole-word contrasts/);
});
test('original eight real phrase anchors must match exact legacy Polish',()=>{
 const moved=fresh();moved.vocabulary[0].legacyWholeUtteranceRef='Conversation_1:13';
 assert.throws(()=>validate(moved),/changed original/);
 const edited=fresh();edited.vocabulary[0].polish='może';
 assert.throws(()=>validate(edited),/original recorded expression/);
 const invented=fresh();invented.vocabulary[20].legacyWholeUtteranceRef='Conversation_1:20';
 assert.throws(()=>validate(invented),/invented source/);
});
test('reject new fake first-word voice, reordered themes or malformed sentence bridge',()=>{
 const voice=fresh();voice.vocabulary[15].exactNewAudio='/audio/invented.mp3';
 assert.throws(()=>validate(voice),/F1 item/);
 const shuffled=fresh();[shuffled.vocabulary[8],shuffled.vocabulary[20]]=[shuffled.vocabulary[20],shuffled.vocabulary[8]];
 assert.throws(()=>validate(shuffled),/F1 item/);
 const fake=fresh();fake.firstSentenceCandidates[0].reviewed=true;
 assert.throws(()=>validate(fake),/F2 preview/);
 const noPhrase=fresh();noPhrase.firstSentenceCandidates.pop();
 assert.throws(()=>validate(noPhrase),/missing preliminary bridge sentences/);
});
test('reject learner runtime imports and publication status flip',()=>{
 assert.throws(()=>validate(fresh(),{runtimeReferences:['v2/frontend/src/Study.tsx']}),/learner code imported/);
 const live=fresh();live.published=true;
 assert.throws(()=>validate(live),/status or audio\/source policy/);
 const approved=fresh();approved.status='native_reviewed';
 assert.throws(()=>validate(approved),/status or audio\/source policy/);
});
