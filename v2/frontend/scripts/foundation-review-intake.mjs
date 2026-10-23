/**
 * C-03: offline human-review intake for foundations.
 * This tool only emits candidate lists or validates reviewer FEEDBACK.
 * It never creates audio, approves language, assigns scores, publishes lessons,
 * or modifies the canonical C-02 corpus.
 */
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {loadDraftInputs,validateFoundationDraft} from './foundation-editorial-gate.mjs';

const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const PURPOSE='native_editorial_feedback_only_no_certification';
const SOURCE='v2/content/journey1-f0-f1-editorial-v1.json';
const SECTIONS=['f0-letters','f0-patterns','f1-words','f2-preview'];
const DECISIONS=['pending','suggest_change','feedback_submitted'];
const requiredFields=(v,names,where)=>{
 if(!v||typeof v!=='object'||Array.isArray(v)||
    Object.keys(v).sort().join('|')!==names.slice().sort().join('|'))
  throw Error('C-03 intake: unexpected fields at '+where);
};
const digest=v=>createHash('sha256').update(JSON.stringify(v),'utf8').digest('hex');
const text=v=>typeof v==='string'&&v.trim().length>0;
const isoDate=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&
  !Number.isNaN(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
const isNullableText=v=>v===null||text(v);
const fail=s=>{throw Error('C-03 intake: '+s);};

export function buildReviewJobs(draft){
 // All C-02 candidate rows are editorial only. Letters have TWO different
 // recording/review targets: the NAME of the letter and the WHOLE example word.
 const jobs=[];
 const add=(row)=>{
  const job={...row,candidateFingerprint:digest(row)};
  jobs.push(job);
 };
 draft.alphabet.forEach((a,i)=>{
  const k=String(i+1).padStart(2,'0');
  add({id:'F0-N-'+k,section:'f0-letters',kind:'letter_name',
   letterSymbol:a.letter,polish:null,english:null,originalWholeUtteranceRef:null,
   editorialNote:'Human must supply correct spoken Polish letter name; candidate word is not a letter-name recording.'});
  add({id:'F0-W-'+k,section:'f0-letters',kind:'whole_word',
   letterSymbol:a.letter,polish:a.candidateWord,english:a.candidateMeaning,
   originalWholeUtteranceRef:null,
   editorialNote:'Verify exact full word, native stress and meaning; no recorded whole-word voice is attached.'});
 });
 draft.patterns.forEach(p=>add({id:p.id,section:'f0-patterns',kind:'pronunciation_concept',
  letterSymbol:null,polish:null,english:null,originalWholeUtteranceRef:null,
  editorialNote:p.spelling+' | candidate words: '+p.candidateExamples.join(' / ')+
   ' | native review: '+p.reviewQuestion}));
 draft.vocabulary.forEach(v=>add({id:v.id,section:'f1-words',kind:'whole_utterance',
  letterSymbol:null,polish:v.polish,english:v.english,
  originalWholeUtteranceRef:v.legacyWholeUtteranceRef,
  editorialNote:'Verify '+v.partOfSpeech+' / '+v.theme+
   (v.legacyWholeUtteranceRef?' (original full utterance ONLY, no extracted phoneme).':
    ' (new licensed exact-utterance recording required).')}));
 draft.firstSentenceCandidates.forEach(v=>add({id:v.id,section:'f2-preview',kind:'full_sentence',
  letterSymbol:null,polish:v.polish,english:v.english,
  originalWholeUtteranceRef:null,editorialNote:v.reviewQuestion}));
 return jobs;
}

export function verifyJobInventory(jobs){
 if(!Array.isArray(jobs)||jobs.length!==136||new Set(jobs.map(x=>x.id)).size!==136)
  fail('expected 136 unique F0/F1/F2 human-review targets');
 const tally=Object.fromEntries(SECTIONS.map(s=>[s,jobs.filter(x=>x.section===s).length]));
 if(tally['f0-letters']!==64||tally['f0-patterns']!==20||
   tally['f1-words']!==42||tally['f2-preview']!==10)
  fail('review inventory stage allocation changed');
 if(jobs.filter(x=>x.originalWholeUtteranceRef!==null).length!==8)
  fail('exactly eight legacy utterance candidates, not isolated phoneme clips');
 for(const job of jobs){
  requiredFields(job,['id','section','kind','letterSymbol','polish','english',
   'originalWholeUtteranceRef','editorialNote','candidateFingerprint'],'review target');
  const {candidateFingerprint,...base}=job;
  if(!/^[0-9a-f]{64}$/.test(candidateFingerprint)||candidateFingerprint!==digest(base)||
     !SECTIONS.includes(job.section)||!text(job.editorialNote)||!isNullableText(job.polish)||
     !isNullableText(job.english)||!isNullableText(job.letterSymbol)||
     !isNullableText(job.originalWholeUtteranceRef))
   fail('malformed or altered candidate fingerprint '+job.id);
  if(job.kind==='letter_name'&&(job.polish!==null||job.english!==null||
     job.originalWholeUtteranceRef!==null))fail('letter name invented or mislabelled '+job.id);
  if(job.kind==='pronunciation_concept'&&(job.polish!==null||job.english!==null))
    fail('pronunciation explanation is not a fixed recording '+job.id);
 }
 return {total:136,...tally,existingWholeUtteranceReferences:8,
         productionReadyAudioTargets:0,publishedLearningItems:0};
}
export const inventoryFingerprint=jobs=>digest(jobs.map(j=>j.candidateFingerprint));

export function buildFeedbackTemplate(jobs){
 verifyJobInventory(jobs);
 return {schemaVersion:1,purpose:PURPOSE,source:SOURCE,
  sourceFingerprint:inventoryFingerprint(jobs),published:false,
  entries:jobs.map(j=>({
   id:j.id,candidateFingerprint:j.candidateFingerprint,decision:'pending',
   proposedPolish:null,proposedEnglish:null,phoneticNotes:null,
   grammarAndRegisterNotes:null,reviewerReference:null,reviewDate:null,
   evidenceNotes:null
  }))};
}

/** Validate provenance + completeness of an offline native-review proposal.
 * A valid feedback submission NEVER establishes identity, acoustic rights or approval.
 */
export function validateFeedback(feedback,jobs){
 verifyJobInventory(jobs);
 requiredFields(feedback,['schemaVersion','purpose','source','sourceFingerprint','published','entries'],'feedback document');
 if(feedback.schemaVersion!==1||feedback.purpose!==PURPOSE||feedback.source!==SOURCE||
    feedback.published!==false||feedback.sourceFingerprint!==inventoryFingerprint(jobs))
    fail('stale or forged feedback provenance / publication status');
 if(!Array.isArray(feedback.entries)||feedback.entries.length!==jobs.length)
    fail('incomplete reviewer feedback inventory');
 const counts={pending:0,suggest_change:0,feedback_submitted:0};
 feedback.entries.forEach((entry,i)=>{
  const job=jobs[i];
  requiredFields(entry,['id','candidateFingerprint','decision','proposedPolish',
   'proposedEnglish','phoneticNotes','grammarAndRegisterNotes','reviewerReference',
   'reviewDate','evidenceNotes'],'feedback entry');
  if(entry.id!==job.id||entry.candidateFingerprint!==job.candidateFingerprint)
    fail('candidate ID or fingerprint mismatch at '+job.id);
  if(!DECISIONS.includes(entry.decision))
    fail('no automatic approval/recording states allowed: '+job.id);
  for(const key of ['proposedPolish','proposedEnglish','phoneticNotes',
    'grammarAndRegisterNotes','reviewerReference','reviewDate','evidenceNotes']){
    if(key==='reviewDate') {if(entry[key]!==null&&!isoDate(entry[key]))fail('invalid review date '+job.id);}
    else if(!isNullableText(entry[key]))fail('invalid reviewer feedback '+key+' '+job.id);
  }
  if(entry.decision==='pending'){
   if(['proposedPolish','proposedEnglish','phoneticNotes','grammarAndRegisterNotes',
     'reviewerReference','reviewDate','evidenceNotes'].some(k=>entry[k]!==null))
     fail('pending row carries undocumented changes '+job.id);
  }else{
   if(!text(entry.reviewerReference)||!isoDate(entry.reviewDate)||!text(entry.evidenceNotes)||
      entry.evidenceNotes.trim().length<12)fail('missing human feedback evidence '+job.id);
   if(entry.decision==='suggest_change'&&!['proposedPolish','proposedEnglish',
      'phoneticNotes','grammarAndRegisterNotes'].some(k=>text(entry[k])))
      fail('missing proposed correction '+job.id);
   // Identifiers, evidence and dates are self-reported, not authenticated.
  }
  counts[entry.decision]++;
 });
 return {...counts,total:jobs.length,
   status:'unverified_reviewer_feedback_only',approvedText:0,approvedAudio:0,learnerImportAllowed:false};
}
function csvEscape(input){
 let s=input==null?'':String(input);
 // Avoid formula injection when opened in a desktop spreadsheet.
 if(/^[\s]*[=+@-]/.test(s))s="'"+s;
 return '"'+s.replaceAll('"','""')+'"';
}
export function renderReviewCSV(jobs){
 const head=['ID','Section','Kind','Letter','Candidate Polish','Candidate English',
  'Original full utterance ID (not word/phoneme clip)','Editorial review prompt',
  'Candidate SHA-256','Proposed Polish (human)','Proposed English (human)',
  'Pronunciation/stress notes','Grammar/register notes','Review comments'];
 const cells=jobs.map(j=>[
  j.id,j.section,j.kind,j.letterSymbol,j.polish,j.english,
  j.originalWholeUtteranceRef,j.editorialNote,j.candidateFingerprint,'','','','',''
 ]);
 return [head,...cells].map(row=>row.map(csvEscape).join(',')).join('\n')+'\n';
}
export function renderRecordingCandidatesCSV(jobs){
 const recordable=jobs.filter(j=>j.kind!=='pronunciation_concept');
 const head=['Job ID','Recording unit kind','Candidate Polish (NOT APPROVED)',
  'Existing full-utterance source (review required)','Recorded exact transcript',
  'Native text accepted','Voice licence','Audio SHA-256','Second-listener QA',
  'Status'];
 return [head,...recordable.map(j=>[j.id,j.kind,j.polish,
   j.originalWholeUtteranceRef,'','','','','','BLOCKED — unreviewed text / missing licensed voice'])]
  .map(row=>row.map(csvEscape).join(',')).join('\n')+'\n';
}

export function checkReviewIntake(){
 const source=loadDraftInputs();
 validateFoundationDraft(source.draft,source.legacy,source.contrasts);
 return verifyJobInventory(buildReviewJobs(source.draft));
}

function main(args){
 const source=loadDraftInputs();
 validateFoundationDraft(source.draft,source.legacy,source.contrasts);
 const jobs=buildReviewJobs(source.draft);
 const result=verifyJobInventory(jobs);
 const sectionArg=args.find(a=>a.startsWith('--section='));
 const section=sectionArg?sectionArg.slice('--section='.length):null;
 if(section&&!SECTIONS.includes(section))fail('unknown section');
 const selected=section?jobs.filter(j=>j.section===section):jobs;
 if(args.includes('--review-csv'))process.stdout.write(renderReviewCSV(selected));
 else if(args.includes('--recording-csv'))process.stdout.write(renderRecordingCandidatesCSV(selected));
 else if(args.includes('--template-json')){
  // Always emit ALL rows; a review submission must reference the exact full inventory.
  if(section)fail('template cannot silently omit other sections');
  process.stdout.write(JSON.stringify(buildFeedbackTemplate(jobs),null,2)+'\n');
 }else if(args.some(a=>a.startsWith('--validate-feedback='))){
  const filename=args.find(a=>a.startsWith('--validate-feedback=')).slice(20);
  if(!filename)fail('review feedback JSON filepath required');
  const receipt=JSON.parse(readFileSync(resolve(filename),'utf8'));
  console.log(JSON.stringify(validateFeedback(receipt,jobs)));
 }else{
  if(section)fail('section filter requires a CSV output');
  console.log('C-03 review intake PASS '+JSON.stringify(result));
 }
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{main(process.argv.slice(2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
