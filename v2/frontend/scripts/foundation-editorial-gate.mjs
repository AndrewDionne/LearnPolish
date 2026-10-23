/**
 * C-02 foundations review gate: editorial-only F0/F1 candidates.
 * Never ship to learner runtime or treat English respellings as verified phonetic audio.
 */
import {readFileSync,readdirSync} from 'node:fs';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const read=(p)=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const ALPHABET='A Ą B C Ć D E Ę F G H I J K L Ł M N Ń O Ó P R S Ś T U W Y Z Ź Ż'.split(' ');
const CONTRASTS=['contrast_l_lstroked','contrast_c_cz_cie','contrast_s_sz_sie','contrast_z_zh_zi','contrast_krzy_przy'];
const THEMES=[['politeness',8],['people',8],['everyday-objects',10],['questions-and-actions',16]];
const EXPECTED_SOURCE=['Conversation_1:14','Conversation_1:15','Conversation_1:10','Conversation_1:8','Conversation_1:12','Conversation_1:2','Conversation_1:0','Conversation_1:4'];
const REVIEW_KEYS=['nativePolish','englishMeaning','letterNamesAndIPA','registeredVoiceRights','exactUtteranceRecording','independentAcousticListening'];
const fail=(message)=>{throw Error('C-02 F0/F1 review gate: '+message);};
const valid=(s)=>typeof s==='string'&&s.trim().length>0;
const object=(x)=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const fields=(obj,expected,name)=>{
 if(!object(obj)||Object.keys(obj).sort().join('|')!==expected.slice().sort().join('|'))
  fail('unexpected '+name+' fields');
};
export function loadDraftInputs(){
 return {
  draft:read('v2/content/journey1-f0-f1-editorial-v1.json'),
  legacy:read('docs/sets/Conversation_1.json'),
  contrasts:read('v2/content/sound-contrasts.json')
 };
}
function sourceReferences(dir){
 const references=[];
 function walk(path){
  for(const item of readdirSync(path,{withFileTypes:true})){
   const full=join(path,item.name);
   if(item.isDirectory())walk(full);
   else if(/\.(?:ts|tsx|js|jsx)$/.test(item.name)){
    const content=readFileSync(full,'utf8');
    if(content.includes('journey1-f0-f1-editorial-v1'))references.push(full);
   }
  }
 }
 walk(dir);
 return references;
}
export function validateFoundationDraft(draft,legacy,contrasts,{runtimeReferences=[]}={}){
 fields(draft,['schemaVersion','status','published','issue','scope','sourcePolicy','approval',
 'alphabet','patterns','originalContrastLessonIds','vocabulary','firstSentenceCandidates','releaseRule'],'draft');
 if(draft.schemaVersion!==1||draft.status!=='unpublished_f0_f1_editorial_candidates'||
    draft.published!==false||draft.issue!==140||
    draft.scope!=='F0_complete_letter_inventory_and_spelling_patterns_F1_high_frequency_words_F2_preview_only'||
    draft.sourcePolicy!=='legacy_sound_contrasts_are_recorded_whole_words_not_verified_isolated_phonemes'||
    draft.releaseRule!=='never_import_into_runtime_or_grade_without_separate_reviewed_text_and_recorded_audio_PR')
    fail('draft status or audio/source policy changed');
 fields(draft.approval,REVIEW_KEYS,'review approval');
 if(REVIEW_KEYS.some(key=>draft.approval[key]!==false))
    fail('unreviewed content cannot claim text, sound or rights approval');
 if(!Array.isArray(draft.alphabet)||draft.alphabet.length!==32||
    draft.alphabet.some((item,i)=>{
      fields(item,['letter','candidateWord','candidateMeaning','letterName','primarySoundIPA','reviewed','audio'],'alphabet entry');
      return item.letter!==ALPHABET[i]||!valid(item.candidateWord)||!valid(item.candidateMeaning)||
       !item.candidateWord.toLocaleUpperCase('pl-PL').includes(item.letter)||
       item.letterName!==null||item.primarySoundIPA!==null||item.reviewed!==false||item.audio!==null;
    }))fail('incomplete 32-letter alphabet, unsourced letter name/IPA or fake voice');
 if(!Array.isArray(draft.patterns)||draft.patterns.length!==20)
    fail('twenty planned phonics/spelling checks required');
 draft.patterns.forEach((p,i)=>{
  fields(p,['id','group','spelling','candidateExamples','reviewQuestion','reviewed','audio'],'sound pattern');
  if(p.id!=='F0-'+String(i+1).padStart(2,'0')||!valid(p.group)||!valid(p.spelling)||
     !valid(p.reviewQuestion)||p.reviewQuestion.length<30||
     !Array.isArray(p.candidateExamples)||p.candidateExamples.length<2||
     p.candidateExamples.some(s=>!valid(s))||p.reviewed!==false||p.audio!==null)
     fail('missing/unreviewed phonics candidate '+(i+1));
 });
 if(JSON.stringify(draft.originalContrastLessonIds)!==JSON.stringify(CONTRASTS)||
    !Array.isArray(contrasts)||!CONTRASTS.every(id=>contrasts.some(c=>c.id===id)))
    fail('all five original whole-word contrasts must remain traceable');
 if(!Array.isArray(draft.vocabulary)||draft.vocabulary.length!==42||
    new Set(draft.vocabulary.map(w=>w.id)).size!==42)
    fail('missing or duplicated purposeful first words');
 let n=0,idx=0;
 for(const [theme,count] of THEMES){
  for(let j=0;j<count;j++,idx++){
   const w=draft.vocabulary[idx];
   fields(w,['id','theme','polish','english','partOfSpeech','legacyWholeUtteranceRef','exactNewAudio','reviewed'],'vocabulary item');
   if(w.theme!==theme||w.id!=='F1-'+theme.toUpperCase().slice(0,3)+'-'+String(j+1).padStart(2,'0')||
      !valid(w.polish)||!valid(w.english)||!valid(w.partOfSpeech)||w.exactNewAudio!==null||w.reviewed!==false)
      fail('unreviewed F1 item incorrectly described/approved: '+idx);
   if(idx<8){
    const ref=EXPECTED_SOURCE[idx];
    if(w.legacyWholeUtteranceRef!==ref)fail('changed original whole-utterance source ID '+ref);
    const original=legacy.cards?.[Number(ref.split(':')[1])];
    if(!original||original.phrase.toLocaleLowerCase('pl-PL')!==w.polish.toLocaleLowerCase('pl-PL'))
       fail('original recorded expression does not match F1 candidate '+ref);
   }else if(w.legacyWholeUtteranceRef!==null){
    fail('invented source for candidate F1 word '+w.id);
   }
   n++;
  }
 }
 if(!Array.isArray(draft.firstSentenceCandidates)||draft.firstSentenceCandidates.length!==10)
    fail('missing preliminary bridge sentences');
 draft.firstSentenceCandidates.forEach((p,i)=>{
  fields(p,['id','polish','english','reviewQuestion','reviewed','audio'],'bridge sentence');
  if(p.id!=='F2-'+String(i+1).padStart(2,'0')||!valid(p.polish)||!valid(p.english)||
     !valid(p.reviewQuestion)||p.reviewed!==false||p.audio!==null)
    fail('F2 preview cannot be silently approved or recorded');
 });
 if(runtimeReferences.length)fail('learner code imported unpublished author draft: '+runtimeReferences[0]);
 return {letters:32,soundPatterns:20,firstVocabulary:n,sentencePreviews:10,
         unapprovedText:true,recordedNewAudio:0,learnerFacingChanges:0};
}
export function renderFoundationReviewSheet(draft){
 const lines=[
  '# Journey 1 F0/F1 native-review sheet — UNPUBLISHED AUTHOR DRAFT',
  '',
  'Not a native-reviewed lesson, not letter-name/IPA authority, not audio.',
  'For every row: correct Polish and English, stress/grammar/register, source rights and exact full-utterance recording.',
  '',
  '## F0 — all 32 Polish letters (candidate examples, NOT letter-name recordings)',
  '',
  '| Letter | Candidate word | English | Native letter name | Primary IPA |',
  '|---|---|---|---|---|'
 ];
 for(const l of draft.alphabet) lines.push('| '+l.letter+' | '+l.candidateWord+' | '+l.candidateMeaning+' | PENDING | PENDING |');
 lines.push('','## F0 — 20 pronunciation and spelling review items','','| ID | Pattern | Candidate words | Native review question |','|---|---|---|---|');
 for(const p of draft.patterns)lines.push('| '+p.id+' | '+p.spelling+' | '+p.candidateExamples.join(', ')+' | '+p.reviewQuestion+' |');
 lines.push('','## F1 — prioritized first vocabulary, 42 editorial items','','| ID | Polish | English | Form | Existing *whole-utterance* anchor |','|---|---|---|---|---|');
 for(const w of draft.vocabulary)lines.push('| '+w.id+' | '+w.polish+' | '+w.english+' | '+w.partOfSpeech+' | '+(w.legacyWholeUtteranceRef??'NEW VOICE NEEDED')+' |');
 lines.push('','## F2 preview ONLY — ten sentence-building requests','','| ID | Candidate Polish | English | Human grammar/register check |','|---|---|---|---|');
 for(const p of draft.firstSentenceCandidates)lines.push('| '+p.id+' | '+p.polish+' | '+p.english+' | '+p.reviewQuestion+' |');
 lines.push('','Do not import these draft IDs, null audio or unverified isolated phoneme claims into learner content.');
 return lines.join('\n');
}
export function checkFoundationDraft(){
 const inputs=loadDraftInputs();
 return validateFoundationDraft(inputs.draft,inputs.legacy,inputs.contrasts,
  {runtimeReferences:sourceReferences(resolve(root,'v2/frontend/src'))});
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{
  const result=checkFoundationDraft();
  if(process.argv.includes('--review-sheet'))
    process.stdout.write(renderFoundationReviewSheet(loadDraftInputs().draft)+'\n');
  else console.log('C-02 F0/F1 unpublished native-review gate PASS:',JSON.stringify(result));
 }catch(err){console.error(err.message);process.exitCode=1;}
}
