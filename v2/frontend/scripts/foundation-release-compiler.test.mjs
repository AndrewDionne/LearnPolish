import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {loadDraftInputs} from './foundation-editorial-gate.mjs';
import {buildReviewJobs} from './foundation-review-intake.mjs';
import {checkReleaseStub,releasePlan,compileQuarantinedFoundations,checkC04} from './foundation-release-compiler.mjs';

const draft=loadDraftInputs().draft;
const plan=releasePlan(draft);
const jobs=buildReviewJobs(draft);
const byId=new Map(jobs.map(j=>[j.id,j]));
// The following bytes are intentionally NOT an authentic, decodable recording.
// They test binary checksum mechanics ONLY; the result stays QUARANTINED and
// must NOT become a learner MP3 or evidence of language/acoustic/rights approval.
const simulated=Buffer.concat([Buffer.from('ID3'),Buffer.alloc(2500,0x42)]);
const sha=createHash('sha256').update(simulated).digest('hex');
const base=()=>({schemaVersion:1,status:'proposed_human_review_only',
 source:'v2/content/journey1-f0-f1-editorial-v1.json',
 sourceFingerprint:plan.sourceFingerprint,published:false,items:[]});
const row=(id,changes={})=>{
 const j=byId.get(id);
 const group=id.startsWith('F0-N-')?'f0-letter-names':
   id.startsWith('F0-W-')?'f0-example-words':
   id.startsWith('F1-POL-')?'f1-politeness':
   id.startsWith('F1-PEO-')?'f1-people':
   id.startsWith('F1-EVE-')?'f1-everyday-objects':
   id.startsWith('F1-QUE-')?'f1-questions-and-actions':'f2-first-sentences';
 const polish=j.polish??'be';
 return {...{
  jobId:j.id,candidateFingerprint:j.candidateFingerprint,lessonGroup:group,
  approvedPolish:polish,approvedEnglish:j.english??'spoken letter name',
  languageEvidence:{
   nativeReviewReference:'review:polish-2026-001',
   englishReviewReference:'review:english-2026-002',
   decisionReference:'decision:operator-2026-003',
   correctionReason:j.polish===null?'Letter name supplied only for quarantined test rehearsal':null
  },
  recordingEvidence:{
   mediaPath:'foundation-review-audio/'+group+'/'+j.id+'.mp3',
   sha256:sha,byteLength:simulated.length,spokenText:polish,
   voiceRightsReference:'rights:sample-dummy-0001',
   speakerReleaseReference:'speaker:sample-dummy-0001',
   independentListeningReference:'listening:sample-dummy-0001',
   acousticReportReference:'acoustic:sample-dummy-0001'
  }
 },...changes};
};
const compile=(data,reader=()=>simulated)=>compileQuarantinedFoundations(data,draft,{readAudio:reader});
const clone=x=>structuredClone(x);

test('C-04 empty committed intake stays blocked and unpublishable',()=>{
 assert.deepEqual(checkReleaseStub({
  schemaVersion:1,status:'blocked_no_native_audio',published:false,
  source:'v2/content/journey1-f0-f1-editorial-v1.json',
  notes:'No approved content is available',items:[]
 }),{published:false,approvedAssets:0});
 const gate=checkC04();
 assert.equal(gate.candidateRecordingTargets,116);
 assert.equal(gate.lessonGroups,7);
 assert.equal(gate.unpublished,true);
 assert.equal(gate.learnerLessonsAdded,0);
 assert.match(gate.stableSourceFingerprint,/^[0-9a-f]{64}$/);
});
test('deny activity/asset promotion inside repository intake',()=>{
 const stub={schemaVersion:1,status:'blocked_no_native_audio',published:false,
  source:'v2/content/journey1-f0-f1-editorial-v1.json',
  notes:'Still blocked',items:[]};
 for(const edit of [{published:true},{status:'approved'},
    {items:[{id:'fake'}]},{source:'v2/content/other.json'}]){
  assert.throws(()=>checkReleaseStub({...stub,...edit}),/committed intake must remain/);
 }
});
test('future rehearsal quarantines exact source-backed Polish with stable IDs and audio paths',()=>{
 const input=base();
 input.items.push(row('F1-POL-01'),row('F1-POL-03'),row('F1-PEO-01'));
 const result=compile(input);
 assert.equal(result.published,false);
 assert.equal(result.reviewedCandidateRows,3);
 assert.equal(result.proposedNewAudio,3);
 assert.equal(result.status,'quarantine_not_learner_approved');
 assert.equal(result.requiresManualLanguageAudioRightsApproval,true);
 assert.equal(result.lessons.length,2);
 assert.deepEqual(result.lessons[0].items.map(x=>x.id),[
  'foundation_f1_first_expressions:F1-POL-01',
  'foundation_f1_first_expressions:F1-POL-03']);
 assert.equal(result.lessons[0].items[1].audio,'generated/audio/foundation_f1_first_expressions/2.mp3');
 assert.equal(result.lessons[1].items[0].id,'foundation_f1_people:F1-PEO-01');
 assert.equal(result.lessons[1].kind,'vocabulary');
});
test('letter NAMES and whole WORDS remain separate proposal groups',()=>{
 const input=base();
 const name=row('F0-N-02',{approvedPolish:'ą'});
 assert.throws(()=>compile({...input,items:[name]}),/letter glyph is not an attested/);
 const supplied=row('F0-N-02',{approvedPolish:'on'});
 supplied.recordingEvidence.spokenText='on';
 const fullword=row('F0-W-02');
 input.items=[supplied,fullword];
 const result=compile(input);
 assert.deepEqual(result.lessons.map(x=>x.id),[
  'foundation_f0_letter_names','foundation_f0_example_words']);
 assert.deepEqual(result.lessons.map(x=>x.items[0].audio),[
  'generated/audio/foundation_f0_letter_names/1.mp3',
  'generated/audio/foundation_f0_example_words/1.mp3']);
});
test('no conceptual F0 pronunciation topic becomes a fabricated voice item',()=>{
 const input=base();input.items=[row('F0-01')];
 assert.throws(()=>compile(input),/candidate\/source ID mismatch/);
});
test('reject changed source, item order/IDs and duplicate work IDs',()=>{
 const input=base();
 input.sourceFingerprint='f'.repeat(64);
 assert.throws(()=>compile(input),/source provenance/);
 const input2=base();input2.items=[row('F1-POL-01'),row('F1-POL-01')];
 assert.throws(()=>compile(input2),/duplicate source job/);
 const input3=base();input3.items=[{...row('F1-POL-01'),candidateFingerprint:'0'.repeat(64)}];
 assert.throws(()=>compile(input3),/candidate\/source ID mismatch/);
 const input4=base();input4.items=[{...row('F1-POL-01'),lessonGroup:'f2-first-sentences'}];
 assert.throws(()=>compile(input4),/candidate\/source ID mismatch/);
});
test('reject edits without language correction and mismatched exact spoken text',()=>{
 const input=base();input.items=[row('F1-POL-01')];
 const corrupt=clone(input);
 corrupt.items[0].approvedPolish='Nie';
 assert.throws(()=>compile(corrupt),/changed candidate without/);
 const alt=clone(input);
 alt.items[0].recordingEvidence.spokenText='Nie';
 assert.throws(()=>compile(alt),/missing fixed-text recording/);
 const noRights=clone(input);
 noRights.items[0].recordingEvidence.voiceRightsReference='';
 assert.throws(()=>compile(noRights),/missing fixed-text recording/);
 const noListening=clone(input);
 noListening.items[0].recordingEvidence.independentListeningReference='';
 assert.throws(()=>compile(noListening),/missing fixed-text recording/);
});
test('reject invented URLs, traversal, hash drift and empty/invalid MP3 payloads',()=>{
 const input=base();input.items=[row('F1-POL-01')];
 for(const pathname of [
  '../fake.mp3','https://evil.example/path.mp3',
  'generated/audio/foundation_f1_first_expressions/0.mp3',
  'foundation-review-audio/f1-politeness/../F1-POL-01.mp3'
 ]){
  const changed=clone(input);
  changed.items[0].recordingEvidence.mediaPath=pathname;
  assert.throws(()=>compile(changed),/untrusted or noncanonical/);
 }
 const altered=clone(input);
 altered.items[0].recordingEvidence.sha256='0'.repeat(64);
 assert.throws(()=>compile(altered),/audio binary does not match/);
 assert.throws(()=>compile(input,()=>Buffer.from('not an mp3')),/no credible MP3 bytes/);
 assert.throws(()=>compile(input,()=>Buffer.alloc(simulated.length)),/invalid MP3 envelope/);
});
test('reject invented numeric/slash/multiple alternative utterances',()=>{
 const input=base();
 const bad=row('F1-POL-01',{approvedPolish:'Tak / Nie'});
 bad.languageEvidence.correctionReason='Reviewer proposed alternative, must split into fixed utterances';
 bad.recordingEvidence.spokenText='Tak / Nie';
 input.items=[bad];
 assert.throws(()=>compile(input),/unfit or ambiguous fixed Polish/);
});
