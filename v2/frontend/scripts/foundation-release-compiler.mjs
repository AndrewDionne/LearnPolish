/**
 * C-04 dry-run-only source compiler.
 *
 * Candidate records are NOT an approval or a learner release. This module can
 * produce a quarantined preview for independent editorial review, but NEVER
 * writes public/generated or imports draft content into frontend runtime.
 */
import {createHash} from 'node:crypto';
import {readFileSync,readdirSync} from 'node:fs';
import {dirname,resolve,join,relative,sep} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {loadDraftInputs,validateFoundationDraft} from './foundation-editorial-gate.mjs';
import {buildReviewJobs,verifyJobInventory,inventoryFingerprint} from './foundation-review-intake.mjs';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
const candidatePath='v2/content/foundation-c04-release-intake-v1.json';
const sourcesPath='v2/content/journey1-f0-f1-editorial-v1.json';
const allowedRef=/^[A-Za-z0-9][A-Za-z0-9._:/#-]{7,159}$/;
const hex=/^[0-9a-f]{64}$/;
const clean=s=>typeof s==='string'&&s.normalize('NFC')===s&&s===s.trim()&&s.length>0;
const safeText=s=>clean(s)&&s.length<220&&!/[<>|/\\\d…]/u.test(s)&&!/\.\.\./.test(s);
const fail=s=>{throw Error('C-04 foundation compiler: '+s);};
const keys=(obj,required,where)=>{
 if(!obj||typeof obj!=='object'||Array.isArray(obj)||
    Object.keys(obj).sort().join('|')!==required.slice().sort().join('|'))
    fail('unexpected fields '+where);
};
const sha256=b=>createHash('sha256').update(b).digest('hex');

const groups={
 'f0-letter-names':{id:'foundation_f0_letter_names',title:'Polish letter names',description:'Listen to the spoken names of Polish letters.',stage:'fundamentals',track:'first-words'},
 'f0-example-words':{id:'foundation_f0_example_words',title:'Alphabet in everyday words',description:'Hear complete Polish words for each alphabet letter.',stage:'fundamentals',track:'first-words'},
 'f1-politeness':{id:'foundation_f1_first_expressions',title:'First expressions',description:'Essential polite Polish responses and greetings.',stage:'fundamentals',track:'first-words'},
 'f1-people':{id:'foundation_f1_people',title:'People and pronouns',description:'Useful Polish words for people and basic pronouns.',stage:'fundamentals',track:'first-words'},
 'f1-everyday-objects':{id:'foundation_f1_everyday_objects',title:'Useful objects and places',description:'Recognize common words from daily life in Poland.',stage:'fundamentals',track:'first-words'},
 'f1-questions-and-actions':{id:'foundation_f1_questions_actions',title:'Questions and actions',description:'First question words and simple verb expressions.',stage:'fundamentals',track:'expanded-words'},
 'f2-first-sentences':{id:'foundation_f2_first_sentences',title:'First complete sentences',description:'Build practical short Polish sentences and questions.',stage:'basic',track:'sentences'}
};
function sectionFor(job){
 if(job.kind==='letter_name')return 'f0-letter-names';
 if(job.id.startsWith('F0-W-'))return 'f0-example-words';
 if(job.id.startsWith('F1-POL-'))return 'f1-politeness';
 if(job.id.startsWith('F1-PEO-'))return 'f1-people';
 if(job.id.startsWith('F1-EVE-'))return 'f1-everyday-objects';
 if(job.id.startsWith('F1-QUE-'))return 'f1-questions-and-actions';
 if(job.id.startsWith('F2-'))return 'f2-first-sentences';
 return null; // 20 orthographic/pronunciation concepts are NOT spoken target clips.
}
const slotFor=job=>{
 const n=Number(job.id.slice(-2));
 if(!Number.isInteger(n)||n<1||n>32)fail('invalid stable job ordinal '+job.id);
 return n-1; // permanent slot, no reindexing of published item IDs
};

export function checkReleaseStub(value){
 keys(value,['schemaVersion','status','published','source','notes','items'],'empty committed release intake');
 if(value.schemaVersion!==1||value.status!=='blocked_no_native_audio'||
    value.published!==false||value.source!==sourcesPath||
    !clean(value.notes)||!Array.isArray(value.items)||value.items.length!==0)
    fail('committed intake must remain empty, unpublished and blocked');
 return {published:false,approvedAssets:0};
}

export function releasePlan(draft){
 const jobs=buildReviewJobs(draft);
 verifyJobInventory(jobs);
 const byGroup=Object.fromEntries(Object.keys(groups).map(group=>[group,[]]));
 for(const job of jobs){
  const group=sectionFor(job);
  if(group)byGroup[group].push(job);
 }
 const counts=Object.fromEntries(Object.entries(byGroup).map(([k,rows])=>[k,rows.length]));
 if(JSON.stringify(Object.values(counts))!==JSON.stringify([32,32,8,8,10,16,10]))
   fail('missing required 116 recording slots');
 return {jobs,byGroup,sourceFingerprint:inventoryFingerprint(jobs),counts};
}

function validateReviewedRow(row,job){
 keys(row,['jobId','candidateFingerprint','lessonGroup','approvedPolish','approvedEnglish',
  'languageEvidence','recordingEvidence'],'candidate row');
 const group=sectionFor(job);
 if(!group||row.lessonGroup!==group||row.jobId!==job.id||
    row.candidateFingerprint!==job.candidateFingerprint)
    fail('candidate/source ID mismatch '+String(row.jobId));
 if(!safeText(row.approvedPolish)||!safeText(row.approvedEnglish))
    fail('unfit or ambiguous fixed Polish/English phrase '+job.id);
 const l=row.languageEvidence;
 keys(l,['nativeReviewReference','englishReviewReference','decisionReference','correctionReason'],'language evidence');
 if(![l.nativeReviewReference,l.englishReviewReference,l.decisionReference].every(s=>typeof s==='string'&&allowedRef.test(s)))
    fail('missing independent language review references '+job.id);
 if(l.correctionReason!==null&&!clean(l.correctionReason))
    fail('invalid correction reason '+job.id);
 if(job.polish===null){ // letter name cannot be copied from alphabet glyph as a substitute
   if(row.approvedPolish.toLocaleUpperCase('pl-PL')===job.letterSymbol)
     fail('letter glyph is not an attested spoken letter name '+job.id);
 }else if((row.approvedPolish!==job.polish||row.approvedEnglish!==job.english)&&
          (!clean(l.correctionReason)||l.correctionReason.length<12)){
    fail('changed candidate without documented language correction '+job.id);
 }
 if(row.lessonGroup==='f0-example-words'&&/\s/u.test(row.approvedPolish))
    fail('alphabet example must remain one complete word '+job.id);
 const a=row.recordingEvidence;
 keys(a,['mediaPath','sha256','byteLength','spokenText','voiceRightsReference',
  'speakerReleaseReference','independentListeningReference','acousticReportReference'],'recording evidence');
 if(!hex.test(a.sha256)||!Number.isInteger(a.byteLength)||a.byteLength<2048||
    a.byteLength>5000000||a.spokenText!==row.approvedPolish||
    ![a.voiceRightsReference,a.speakerReleaseReference,a.independentListeningReference,
      a.acousticReportReference].every(s=>typeof s==='string'&&allowedRef.test(s)))
    fail('missing fixed-text recording/rights/acoustic evidence '+job.id);
 // This path must be under a PRIVATE review workspace; never a URL or an
 // existing generated lesson. Exact binary and acoustic truth remain distinct.
 if(typeof a.mediaPath!=='string'||
    !/^foundation-review-audio\/[a-zA-Z0-9_-]+\/[A-Za-z0-9-]+\.mp3$/.test(a.mediaPath)||
    a.mediaPath!==('foundation-review-audio/'+group+'/'+job.id+'.mp3'))
    fail('untrusted or noncanonical review-audio path '+job.id);
 return {group,slot:slotFor(job)};
}

function checkMP3Envelope(bytes){
 if(!Buffer.isBuffer(bytes)||bytes.length<2048)fail('no credible MP3 bytes');
 // Quick payload-type defense only, NOT an acoustic codec/quality validation.
 // Standalone acoustic verification must use a decoder + native listening.
 const id3=bytes.toString('latin1',0,3)==='ID3';
 const sync=bytes[0]===0xff&&(bytes[1]&0xe0)===0xe0;
 if(!id3&&!sync)fail('invalid MP3 envelope');
}

export function compileQuarantinedFoundations(candidate,source,{readAudio}={}){
 const {jobs,sourceFingerprint}=releasePlan(source);
 const byId=new Map(jobs.map(j=>[j.id,j]));
 keys(candidate,['schemaVersion','status','source','sourceFingerprint','published','items'],'release candidate');
 if(candidate.schemaVersion!==1||candidate.status!=='proposed_human_review_only'||
    candidate.source!==sourcesPath||candidate.sourceFingerprint!==sourceFingerprint||
    candidate.published!==false||!Array.isArray(candidate.items))
    fail('source provenance or unpublished status invalid');
 if(typeof readAudio!=='function')fail('readAudio must be a bounded local reader');
 const used=new Set();
 const rowsByGroup=new Map(Object.keys(groups).map(key=>[key,[]]));
 for(const row of candidate.items){
  const job=byId.get(row?.jobId);
  if(!job||used.has(job.id))fail('unknown or duplicate source job');
  used.add(job.id);
  const {group,slot}=validateReviewedRow(row,job);
  const bytes=readAudio(row.recordingEvidence.mediaPath);
  checkMP3Envelope(bytes);
  if(bytes.length!==row.recordingEvidence.byteLength||sha256(bytes)!==row.recordingEvidence.sha256)
    fail('audio binary does not match recorded byte count and SHA-256 '+job.id);
  const def=groups[group];
  rowsByGroup.get(group).push({ordinal:slot,sourceJobId:job.id,
    id:def.id+':'+job.id,polish:row.approvedPolish,
    english:row.approvedEnglish,
    proposedAudio:'generated/audio/'+def.id+'/'+slot+'.mp3',
    audioSHA256:row.recordingEvidence.sha256,
    sourceCandidateFingerprint:job.candidateFingerprint});
 }
 const previews=[];
 for(const [group,rows] of rowsByGroup){
  if(!rows.length)continue;
  rows.sort((a,b)=>a.ordinal-b.ordinal);
  const def=groups[group];
  previews.push({
    schemaVersion:1,id:def.id,title:def.title,description:def.description,
    kind:'vocabulary',source:'curated',
    curriculum:{stage:def.stage,track:def.track,order:Object.keys(groups).indexOf(group)+1},
    items:rows.map(r=>({
      id:r.id,polish:r.polish,english:r.english,
      audio:r.proposedAudio,
    })),
  });
 }
 // The compiler does NOT write files, create generated/audio assets, attach to
 // lessons.json, award progress or assert acoustic certification. The returned
 // lessons are strictly quarantined preview shapes.
 return {status:'quarantine_not_learner_approved',published:false,
  sourceFingerprint,reviewedCandidateRows:used.size,lessons:previews,
  proposedNewAudio:used.size,requiresManualLanguageAudioRightsApproval:true};
}

function runtimeReferences(){
 const dir=resolve(root,'v2/frontend/src'),found=[];
 const scan=p=>{
  for(const d of readdirSync(p,{withFileTypes:true})){
   const full=join(p,d.name);
   if(d.isDirectory())scan(full);
   else if(/\.(?:tsx?|jsx?)$/.test(d.name)){
    const text=readFileSync(full,'utf8');
    if(text.includes('foundation-c04-release-intake')||
       text.includes('foundation-release-compiler')||
       text.includes('foundation-review-audio/'))
      found.push(relative(dir,full).split(sep).join('/'));
   }
  }
 };
 scan(dir);
 return found;
}
export function checkC04(){
 const inputs=loadDraftInputs();
 validateFoundationDraft(inputs.draft,inputs.legacy,inputs.contrasts);
 const stub=JSON.parse(readFileSync(resolve(root,candidatePath),'utf8'));
 checkReleaseStub(stub);
 const plan=releasePlan(inputs.draft);
 const unexpected=runtimeReferences();
 if(unexpected.length)fail('runtime imported review-only sources: '+unexpected.join(','));
 return {candidateRecordingTargets:116,lessonGroups:Object.keys(groups).length,
   unpublished:true,committedAudio:0,learnerLessonsAdded:0,
   stableSourceFingerprint:plan.sourceFingerprint};
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{
  if(process.argv.length!==2)fail('no production CLI or implicit publishing operation');
  console.log('C-04 quarantine compiler gate PASS: '+JSON.stringify(checkC04()));
 }catch(err){console.error(err.message);process.exitCode=1;}
}
