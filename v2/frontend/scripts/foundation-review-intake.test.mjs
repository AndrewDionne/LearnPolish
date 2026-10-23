import test from 'node:test';
import assert from 'node:assert/strict';
import {loadDraftInputs} from './foundation-editorial-gate.mjs';
import {buildReviewJobs,verifyJobInventory,inventoryFingerprint,
 buildFeedbackTemplate,validateFeedback,renderReviewCSV,renderRecordingCandidatesCSV,
 checkReviewIntake} from './foundation-review-intake.mjs';

const source=loadDraftInputs();
const jobs=buildReviewJobs(source.draft);
const fresh=()=>structuredClone(buildFeedbackTemplate(jobs));
const valid=doc=>validateFeedback(doc,jobs);
const annotate=(doc,id,decision='feedback_submitted')=>{
 const e=doc.entries.find(x=>x.id===id);
 e.decision=decision;
 e.reviewerReference='native-review-desk-01 (identity not verified)';
 e.reviewDate='2026-10-24';
 e.evidenceNotes='Suggested text checked by reviewer; independent approval required.';
 if(decision==='suggest_change')e.proposedPolish='Proponowana korekta';
 return e;
};

test('C-03 offline intake pins 136 independent, unpublished review targets',()=>{
 assert.deepEqual(checkReviewIntake(),{
   total:136,'f0-letters':64,'f0-patterns':20,
   'f1-words':42,'f2-preview':10,existingWholeUtteranceReferences:8,
   productionReadyAudioTargets:0,publishedLearningItems:0
 });
 assert.equal(verifyJobInventory(jobs).total,136);
 assert.equal(new Set(jobs.map(x=>x.candidateFingerprint)).size,136);
 assert.match(inventoryFingerprint(jobs),/^[a-f0-9]{64}$/);
});
test('letter name is a separate unrecorded target, not the example word',()=>{
 assert.equal(jobs[0].id,'F0-N-01');
 assert.equal(jobs[0].kind,'letter_name');
 assert.equal(jobs[0].letterSymbol,'A');
 assert.equal(jobs[0].polish,null);
 assert.equal(jobs[1].id,'F0-W-01');
 assert.equal(jobs[1].polish,'auto');
 assert.equal(jobs[2].id,'F0-N-02');
 assert.equal(jobs[2].letterSymbol,'Ą');
 assert.equal(jobs[2].polish,null);
 assert.equal(jobs[3].polish,'mąż');
});
test('original eight legacy references remain exact WHOLE utterances',()=>{
 const anchored=jobs.filter(j=>j.originalWholeUtteranceRef!==null);
 assert.equal(anchored.length,8);
 assert.equal(anchored[0].polish,'tak');
 assert.equal(anchored[0].originalWholeUtteranceRef,'Conversation_1:14');
 assert.equal(anchored[7].originalWholeUtteranceRef,'Conversation_1:4');
 assert.equal(jobs.filter(j=>j.kind==='pronunciation_concept').length,20);
});
test('review CSV and recording candidates contain no approvals or invented names',()=>{
 const csv=renderReviewCSV(jobs);
 const rows=csv.trimEnd().split('\n');
 assert.equal(rows.length,137);
 assert.match(rows[1],/F0-N-01/);
 assert.match(csv,/Candidate Polish/);
 assert.match(csv,/Candidate SHA-256/);
 const recording=renderRecordingCandidatesCSV(jobs);
 assert.equal(recording.trimEnd().split('\n').length,117);
 assert.match(recording,/BLOCKED/);
 assert.doesNotMatch(recording,/F0-01/); // A pronunciation concept isn't a recording.
 assert.match(recording,/F0-N-01/); // Blank name to be reviewed, not invented.
});
test('JSON template validates but explicitly has ZERO native/audio approvals',()=>{
 const pending=fresh();
 assert.equal(pending.entries.length,136);
 assert.deepEqual(valid(pending),{
  pending:136,suggest_change:0,feedback_submitted:0,total:136,
  status:'unverified_reviewer_feedback_only',
  approvedText:0,approvedAudio:0,learnerImportAllowed:false
 });
 const input=fresh();
 annotate(input,'F0-N-02','suggest_change');
 annotate(input,'F1-POL-01');
 assert.deepEqual(valid(input),{
  pending:134,suggest_change:1,feedback_submitted:1,total:136,
  status:'unverified_reviewer_feedback_only',
  approvedText:0,approvedAudio:0,learnerImportAllowed:false
 });
});
test('reject stale source digest, shifted candidate IDs, reorder and duplicates',()=>{
 const old=fresh();old.sourceFingerprint='0'.repeat(64);
 assert.throws(()=>valid(old),/stale or forged/);
 const id=fresh();id.entries[0].id='F0-N-99';
 assert.throws(()=>valid(id),/mismatch/);
 const moved=fresh();[moved.entries[0],moved.entries[1]]=[moved.entries[1],moved.entries[0]];
 assert.throws(()=>valid(moved),/mismatch/);
 const short=fresh();short.entries.pop();
 assert.throws(()=>valid(short),/incomplete/);
 const drift=structuredClone(jobs);drift[3].polish='wąż';
 assert.throws(()=>verifyJobInventory(drift),/fingerprint/);
});
test('fail closed against false signed-off voice, grammar or completion flags',()=>{
 const fake=fresh();fake.published=true;
 assert.throws(()=>valid(fake),/publication/);
 const approval=fresh();approval.entries[0].decision='native_approved';
 assert.throws(()=>valid(approval),/no automatic approval/);
 const audio=fresh();audio.entries[3].audioFile='fake.wav';
 assert.throws(()=>valid(audio),/unexpected fields/);
 const late=fresh();late.entries[0].proposedPolish='a';
 assert.throws(()=>valid(late),/pending row/);
});
test('require documented reviewer feedback, never infer identity or credentials',()=>{
 const noName=fresh();const a=annotate(noName,'F1-POL-01');
 a.reviewerReference=null;
 assert.throws(()=>valid(noName),/missing human feedback evidence/);
 const vague=fresh();const b=annotate(vague,'F1-POL-01');
 b.evidenceNotes='ok';
 assert.throws(()=>valid(vague),/missing human feedback evidence/);
 const weirdDate=fresh();const c=annotate(weirdDate,'F1-POL-01');
 c.reviewDate='2026-02-30';
 assert.throws(()=>valid(weirdDate),/invalid review date/);
 const change=fresh();const d=annotate(change,'F0-N-02','suggest_change');
 d.proposedPolish=null;
 assert.throws(()=>valid(change),/missing proposed correction/);
});
test('CSV escapes spreadsheet-formula input rather than allowing executable cells',()=>{
 const edited=structuredClone(jobs);
 edited[1].english='=HYPERLINK("http://bad","click")';
 const data=renderReviewCSV(edited);
 assert.match(data,/"'=HYPERLINK\(""http:\/\/bad"",""click""\)"/);
});
