import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {makeVoiceProductionPlan,loadVoiceProductionPlan,previewMarkdown} from './voice-production.mjs';

const catalogPath=path.resolve('public/generated/lessons.json');
const configPath=path.resolve('../../v2/content/voice-production.json');
const fixture=()=>{
  const catalog=JSON.parse(fs.readFileSync(catalogPath,'utf8'));
  const config=JSON.parse(fs.readFileSync(configPath,'utf8'));
  return {catalog,config};
};

test('first 58 real built-in Speak exercises produce an exact, cost-free audio plan',()=>{
  const plan=loadVoiceProductionPlan();
  assert.deepEqual(plan.lessons.map(x=>[x.id,x.items]),[
    ['Conversation_1',26],['contrast_c_cz_cie',6],
    ['contrast_s_sz_sie',6],['numbers_1-20',20]
  ]);
  assert.equal(plan.summary.items,58);
  assert.equal(plan.summary.withLegacyAudio,58);
  assert.equal(plan.summary.fixedWrittenTargets,56);
  assert.equal(plan.summary.sourceBlockers,2);
  assert.equal(plan.summary.auditionSamples,8);
  assert.equal(plan.summary.proposedAudioFiles,24);
  assert.deepEqual(plan.voices.map(v=>v.id),[
    'pl-PL-MarekNeural','pl-PL-AgnieszkaNeural','pl-PL-ZofiaNeural'
  ]);
  assert.deepEqual(plan.ownerVoicePreference.rankedVoiceIds,plan.voices.map(v=>v.id));
  assert.equal(plan.ownerVoicePreference.status,
    'provisional_owner_listening_preference_not_approved_production_audio');
  assert.ok(plan.ownerVoicePreference.observation.includes('clipped'));
  assert.equal(plan.summary.producedAudioFiles,0);
  assert.equal(plan.summary.networkCalls,0);
  assert.ok(plan.summary.proposedCharacters>0);
  assert.ok(plan.items.every(x=>x.pronunciationSegments.segments.join('')===x.polish));
  assert.ok(plan.items.every(x=>x.referenceAudio.sha256?.length===64));
  assert.ok(plan.items.every(x=>x.referenceAudio.voice==='unknown_legacy_import'));
  assert.ok(plan.items.every(x=>x.availableNewVoiceVariants.length===0));
  assert.deepEqual(plan.items.filter(x=>x.blockerReason).map(x=>x.itemId),[
    'Conversation_1:24','Conversation_1:25'
  ]);
  assert.ok(previewMarkdown(plan).includes('Audition: 8 expressions'));
});

test('source edit, untracked blocker or stale count fails instead of certifying wrong speech',()=>{
  const {catalog,config}=fixture();
  const ok=()=>makeVoiceProductionPlan(catalog,config);
  assert.equal(ok().summary.items,58);
  let changed=structuredClone(catalog);
  changed.lessons.find(x=>x.id==='Conversation_1').items[24].polish='Jak ma pan na imię?';
  assert.throws(()=>makeVoiceProductionPlan(changed,config),/Missing aligned pronunciation data/);
  changed=structuredClone(catalog);
  changed.lessons.find(x=>x.id==='Conversation_1').items[24].pronunciationSegments.segments=['Jak ma pani na imię?'];
  assert.throws(()=>makeVoiceProductionPlan(changed,config),/Missing aligned pronunciation data/);
  const modified=structuredClone(config);
  modified.sourceBlockers.pop();
  assert.throws(()=>makeVoiceProductionPlan(catalog,modified),/Source blockers changed/);
  modified.sourceBlockers.push({...config.sourceBlockers[0]});
  assert.throws(()=>makeVoiceProductionPlan(catalog,modified),/Duplicate blocker ID/);
  const wrongCount=structuredClone(config);
  wrongCount.lessons[0].items=27;
  assert.throws(()=>makeVoiceProductionPlan(catalog,wrongCount),/Changed stage, size or missing lesson/);
});

test('voice auditions reject invented assets, changed Polish and duplicated candidates',()=>{
  const {catalog,config}=fixture();
  assert.throws(()=>makeVoiceProductionPlan(catalog,config,{hasAudio:()=>false}),/Missing or untrusted legacy MP3/);
  const changed=structuredClone(config);
  changed.auditionSamples[0].polish='Dzień inny';
  assert.throws(()=>makeVoiceProductionPlan(catalog,changed),/Missing, edited or unsafe audition target/);
  const dup=structuredClone(config);
  dup.voiceCandidates[1].id=dup.voiceCandidates[0].id;
  assert.throws(()=>makeVoiceProductionPlan(catalog,dup),/Duplicate voice candidate/);
  const stalePreference=structuredClone(config);
  stalePreference.ownerVoicePreference.rankedVoiceIds.reverse();
  assert.throws(()=>makeVoiceProductionPlan(catalog,stalePreference),
    /Unreviewed or inconsistent owner voice-preference ranking/);
  const noApproval=structuredClone(config);
  noApproval.ownerVoicePreference.status='approved_for_production';
  assert.throws(()=>makeVoiceProductionPlan(catalog,noApproval),
    /Unreviewed or inconsistent owner voice-preference ranking/);
  const bad=structuredClone(config);
  bad.voiceCandidates[0].id='en-US-AriaNeural';
  assert.throws(()=>makeVoiceProductionPlan(catalog,bad),/Invalid Polish voice candidate/);
  const attempted=structuredClone(config);
  attempted.auditionSamples.push({itemId:'Conversation_1:24',polish:'Jak ma pan/pani na imię?'});
  assert.throws(()=>makeVoiceProductionPlan(catalog,attempted),/Missing, edited or unsafe audition target/);
});

test('production audit command refuses synthesis flags (offline-only)',()=>{
  assert.throws(()=>execFileSync(process.execPath,['scripts/voice-production.mjs','--send'],{
    cwd:path.resolve('.'),stdio:'pipe'
  }),/Use --json or --markdown/);
});
