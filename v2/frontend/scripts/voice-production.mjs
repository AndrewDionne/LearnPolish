/** Offline-only reference-audio and pronunciation-content plan.
 *
 * Generates a source-verified audit and a bounded three-voice audition list.
 * It NEVER synthesizes speech, makes HTTP requests, or writes audio.
 * Production audio remains the existing, unchanged legacy MP3 per lesson.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../../..');
const catalogPath=path.join(root,'v2/frontend/public/generated/lessons.json');
const specificationPath=path.join(root,'v2/content/voice-production.json');
const publicDir=path.join(root,'v2/frontend/public');
const LEGACY_AUDIO=/^generated\/audio\/[A-Za-z0-9_%.-]+\/[0-9]+\.mp3$/u;
const PROXY_STRIPPABLE=/[\s.,!?;:()\-’'„”“"…]/gu;
const PROXY_LETTERS=/^[a-ząćęłńóśźż]+$/u;
const INCOMPLETE=/…|\.{3,}/u;
const sha=(value)=>createHash('sha256').update(value).digest('hex');

function assert(condition, message){
  if(!condition) throw new Error(message);
}
function unique(items, label){
  assert(new Set(items).size===items.length, 'Duplicate '+label);
}
export function makeVoiceProductionPlan(manifest, specification, options={}){
  const {hasAudio=()=>true, hashAudio=()=>null}=options;
  assert(manifest?.schemaVersion===1 && Array.isArray(manifest.lessons),
    'Expected generated V2 lessons.json');
  assert(specification?.schemaVersion===1 &&
    specification.reviewStatus==='candidates_not_approved',
    'Unapproved or incompatible audio specification');
  assert(Array.isArray(specification.lessons) && specification.lessons.length===4,
    'Expected exactly first four beginner learning sets');
  assert(Array.isArray(specification.voiceCandidates) &&
    specification.voiceCandidates.length===3,'Expected three audition voices');
  assert(Array.isArray(specification.sourceBlockers) &&
    Array.isArray(specification.auditionSamples),'Missing review/audition rows');

  const voiceIds=specification.voiceCandidates.map(v=>v.id);
  unique(voiceIds,'voice candidate');
  const preference=specification.ownerVoicePreference;
  assert(preference &&
    preference.status==='provisional_owner_listening_preference_not_approved_production_audio' &&
    typeof preference.source==='string' && !!preference.source &&
    typeof preference.observation==='string' && !!preference.observation &&
    Array.isArray(preference.rankedVoiceIds) &&
    preference.rankedVoiceIds.length===voiceIds.length &&
    preference.rankedVoiceIds.every((id,index)=>id===voiceIds[index]) &&
    Array.isArray(preference.qualityFocus) && preference.qualityFocus.length>=2 &&
    preference.qualityFocus.every(x=>typeof x==='string' && !!x) &&
    typeof preference.nextGate==='string' && !!preference.nextGate,
    'Unreviewed or inconsistent owner voice-preference ranking');
  for(const voice of specification.voiceCandidates){
    assert(/^pl-PL-[A-Za-z]+Neural$/.test(voice.id) &&
      typeof voice.label==='string' && !!voice.label &&
      typeof voice.role==='string' && !!voice.role,
    'Invalid Polish voice candidate');
  }
  const known=new Map(manifest.lessons.map(lesson=>[lesson.id,lesson]));
  unique(specification.lessons.map(x=>x.id),'lesson target');
  const items=[];
  const lessons=[];
  for(const selected of specification.lessons){
    const lesson=known.get(selected.id);
    assert(lesson && ['vocabulary','sounds'].includes(lesson.kind) &&
      lesson.items?.length===selected.items &&
      /^E1\.0[1-4]$/.test(selected.stage),
      'Changed stage, size or missing lesson: '+selected.id);
    let withAudio=0;
    for(const item of lesson.items){
      assert(typeof item.polish==='string' && !!item.polish.trim() &&
        typeof item.english==='string' && !!item.english.trim() &&
        typeof item.id==='string' && !!item.id &&
        item.pronunciationSegments?.segments?.join('')===item.polish,
        'Missing aligned pronunciation data: '+item?.id);
      assert(typeof item.audio==='string' && LEGACY_AUDIO.test(item.audio) &&
        hasAudio(item.audio),'Missing or untrusted legacy MP3: '+item.id);
      withAudio++;
      const normalized=item.polish.toLowerCase().replace(PROXY_STRIPPABLE,'');
      const referenceBlocked=!PROXY_LETTERS.test(normalized);
      const unfinished=INCOMPLETE.test(item.polish);
      items.push({
        itemId:item.id,lessonId:lesson.id,stage:selected.stage,
        polish:item.polish,english:item.english,
        referenceStatus:referenceBlocked?'unsupported':unfinished?'unfinished':'fixed_written_target',
        referenceAudio:{
          path:item.audio,sha256:hashAudio(item.audio),
          voice:'unknown_legacy_import',reviewStatus:'needs_listening_review'
        },
        pronunciationSegments:{
          method:item.pronunciationSegments.method,
          segments:item.pronunciationSegments.segments,
          reviewStatus:'needs_native_speaker_review'
        },
        englishGuideStatus:item.pronunciationGuide?'aligned_draft':item.pronunciation?'unsegmented_legacy_cue':'not_authored',
        // No invented voice variants: the production selector must not show nonexistent files.
        availableNewVoiceVariants:[]
      });
    }
    lessons.push({stage:selected.stage,id:lesson.id,items:lesson.items.length,withAudio});
  }
  assert(items.length===58, 'Beginner voice plan must contain exactly 58 real catalog items');
  unique(items.map(i=>i.itemId),'item ID');
  const indexed=new Map(items.map(i=>[i.itemId,i]));
  const blocked=items.filter(i=>i.referenceStatus!=='fixed_written_target');
  unique(specification.sourceBlockers.map(x=>x.itemId),'blocker ID');
  assert(blocked.length===specification.sourceBlockers.length,
    'Source blockers changed; review spec before using audio plan');
  for(const source of specification.sourceBlockers){
    const row=indexed.get(source.itemId);
    assert(row && row.referenceStatus!=='fixed_written_target' &&
      row.polish===source.polish && typeof source.reason==='string' && source.reason.length>10,
      'Stale, missing or unexpected blocker: '+source.itemId);
    row.blockerReason=source.reason;
  }
  assert(blocked.every(i=>!!i.blockerReason),
    'Unlisted blocked or unfinished beginner reference');
  unique(specification.auditionSamples.map(x=>x.itemId),'audition item ID');
  assert(specification.auditionSamples.length>=3 && specification.auditionSamples.length<=12,
    'Audition must contain 3–12 curated short expressions');
  const audition=[];
  for(const sample of specification.auditionSamples){
    const row=indexed.get(sample.itemId);
    assert(row && row.polish===sample.polish &&
      row.referenceStatus==='fixed_written_target',
      'Missing, edited or unsafe audition target: '+sample.itemId);
    assert(Array.from(row.polish).length<=120,'Audition target too long');
    for(const voice of specification.voiceCandidates){
      audition.push({
        itemId:row.itemId,polish:row.polish,
        voiceId:voice.id,
        textSha256:sha(row.polish),
        characters:Array.from(row.polish).length,
        suggestedLocalFilename:voice.id+'/'+row.itemId.replaceAll(':','_')+'.mp3',
        status:'not_generated_not_reviewed'
      });
    }
  }
  return {
    schemaVersion:1,phase:'offline_preview_only',
    notes:'No provider has been called. Existing audio voices are unknown; all new voices are ungenerated candidates.',
    summary:{
      lessons:lessons.length,items:items.length,
      withLegacyAudio:items.filter(i=>!!i.referenceAudio.path).length,
      audioAuditedByHuman:0,
      fixedWrittenTargets:items.length-blocked.length,
      sourceBlockers:blocked.length,
      nativeReviewedSegments:0,
      proposedVoiceCandidates:voiceIds.length,
      auditionSamples:specification.auditionSamples.length,
      proposedAudioFiles:audition.length,
      proposedCharacters:audition.reduce((a,x)=>a+x.characters,0),
      producedAudioFiles:0,
      networkCalls:0
    },
    voices:specification.voiceCandidates,
    ownerVoicePreference:preference,
    lessons,items,audition
  };
}
export function previewMarkdown(plan){
  const s=plan.summary;
  return [
    '# First 58 Speak items — offline audio & pronunciation audit',
    '',
    'Existing reference audio: '+s.withLegacyAudio+'/'+s.items+'; legacy voice/provenance unverified.',
    'Written targets: '+s.fixedWrittenTargets+' fixed; '+s.sourceBlockers+' require editorial repair.',
    'Native-reviewed syllable groupings: '+s.nativeReviewedSegments+'/'+s.items+'.',
    'Audition: '+s.auditionSamples+' expressions × '+s.proposedVoiceCandidates+
      ' candidate voices = '+s.proposedAudioFiles+' PROPOSED clips ('+s.proposedCharacters+
      ' characters). No clips generated and no requests made.',
    '',
    '| Stage | Lesson | Items | Existing MP3 |',
    '|---|---|---:|---:|',
    ...plan.lessons.map(l=>'| '+l.stage+' | '+l.id+' | '+l.items+' | '+l.withAudio+' |'),
    '',
    '## References not yet safe for scored Speak',
    ...plan.items.filter(x=>x.blockerReason)
      .map(x=>'- '+x.itemId+' — '+x.polish+' → '+x.blockerReason),
    '',
    '## Owner-preferred audition order (not yet production approved)',
    ...plan.voices.map((v,index)=>(index+1)+'. '+v.label+' ('+v.id+')'),
    '',
    'Owner quality concern: '+plan.ownerVoicePreference.observation,
    'Next gate: '+plan.ownerVoicePreference.nextGate,
    '',
    'To inspect every item and the exact proposed clips: npm run audit:voice -- --json',
    ''
  ].join('\n');
}
export function loadVoiceProductionPlan(){
  const manifest=JSON.parse(fs.readFileSync(catalogPath,'utf8'));
  const config=JSON.parse(fs.readFileSync(specificationPath,'utf8'));
  const hasAudio=(relative)=>fs.existsSync(path.join(publicDir,relative));
  const hashAudio=(relative)=>sha(fs.readFileSync(path.join(publicDir,relative)));
  return makeVoiceProductionPlan(manifest,config,{hasAudio,hashAudio});
}
if(process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const args=process.argv.slice(2);
  if(args.length>1 || (args.length===1 && args[0]!=='--json' && args[0]!=='--markdown')){
    throw new Error('Offline-only. Use --json or --markdown; no --send or provider calls.');
  }
  const plan=loadVoiceProductionPlan();
  process.stdout.write(args[0]==='--json'
    ? JSON.stringify(plan,null,2)+'\n'
    : previewMarkdown(plan));
}
