/** No Azure key or raw provider JSON reaches the browser. */
import type {AssessmentReadyCapture} from './format';
import {FAMILY_API} from '../family/api';

export type SpeechTiming = {roundTripMs:number;sdkMs?:number};

/** Reserved for human-calibrated acoustic syllable scores.
 * Current pl-PL Azure aggregate adapter NEVER emits this structure.
 * Polish phoneme names/auto syllable groups are not supplied by Azure.
 */
export type CalibratedSyllables = {
  method:'reviewed-acoustic-syllables-v1';
  reference:string;
  segments:{polish:string;score:number|null}[];
};

export type ColourHints = {
  method:'whisper-transcript-proxy-v1';
  reference:string;
  segments:{polish:string;hint:'close'|'review'|'focus'|'uncertain'}[];
};

export type SpeechFeedback =
  | {status:'ok';engine:'azure-pl-PL-scripted';calibration:'uncalibrated';
     scores:{accuracy:number;fluency:number;completeness:number};
     syllableFeedback?:CalibratedSyllables;timing?:SpeechTiming}
  | {status:'ok';engine:'azure-whisper-blend-v1';calibration:'experimental-uncalibrated';
     combined:number;colourHints:ColourHints;timing?:SpeechTiming}
  | {status:'inconclusive';reason:string;timing?:SpeechTiming};

/** Validate an explicit, independently reviewed syllable result.
 * Incomplete or malformed segmentation MUST NOT be partially shown.
 * This does not establish model calibration by itself; server publishing
 * is reserved until offline native controls and learner ratings validate it.
 */
export function parseCalibratedSyllables(input:unknown):CalibratedSyllables|null {
  if(!input || typeof input!=='object')return null;
  const value=input as Record<string,unknown>;
  if(value.method!=='reviewed-acoustic-syllables-v1'||
     typeof value.reference!=='string' || !value.reference ||
     !Array.isArray(value.segments) || value.segments.length<2 || value.segments.length>12)return null;
  const segments:{polish:string;score:number|null}[]=[];
  for(const raw of value.segments){
    if(!raw || typeof raw!=='object')return null;
    const seg=raw as Record<string,unknown>;
    const score=seg.score;
    if(typeof seg.polish!=='string' || !seg.polish ||
       !(score===null || (typeof score==='number'&&Number.isFinite(score)&&score>=0&&score<=100)))return null;
    segments.push({polish:seg.polish,score:score as number|null});
  }
  if(segments.map(seg=>seg.polish).join('')!==value.reference)return null;
  return {method:'reviewed-acoustic-syllables-v1',reference:value.reference,segments};
}

const REASONS:Record<string,string>={
  no_match:'Azure could not recognize enough speech. Try again.',
  canceled:'Azure could not complete this assessment. You can replay or try again.',
  no_assessment:'Azure did not return enough pronunciation information to score this take.',
  provider_inconclusive:'Pronunciation feedback was unavailable for this take.',
  provider_unavailable:'Pronunciation feedback is temporarily unavailable.',
};

export const SPEECH_ASSESSMENT_AVAILABLE =
  import.meta.env.VITE_SPEECH_ASSESSMENT_ENABLED === 'true' && Boolean(FAMILY_API);
/** Separately opted-in experimental two-provider workflow; never on by default. */
export const SPEECH_BLEND_AVAILABLE =
  SPEECH_ASSESSMENT_AVAILABLE && import.meta.env.VITE_SPEECH_BLEND_ENABLED === 'true';

export function parseColourHints(input:unknown):ColourHints|null {
  if(!input||typeof input!=='object')return null;
  const v=input as Record<string,unknown>;
  if(v.method!=='whisper-transcript-proxy-v1' || typeof v.reference!=='string' ||
     !v.reference || !Array.isArray(v.segments) ||
     v.segments.length<1 || v.segments.length>32)return null;
  const segments:ColourHints['segments']=[];
  for(const raw of v.segments){
    if(!raw||typeof raw!=='object')return null;
    const part=raw as Record<string,unknown>;
    if(typeof part.polish!=='string'||!part.polish ||
       !['close','review','focus','uncertain'].includes(String(part.hint)))return null;
    segments.push({polish:part.polish,hint:part.hint as ColourHints['segments'][number]['hint']});
  }
  if(segments.map(p=>p.polish).join('')!==v.reference)return null;
  return {method:'whisper-transcript-proxy-v1',reference:v.reference,segments};
}

/** Validate untrusted service replies. Unrecognized/missing grades are never zero. */
export function parseSpeechFeedback(input:unknown):SpeechFeedback {
  if(!input || typeof input!=='object')throw new Error('Assessment response unavailable.');
  const row=input as Record<string,unknown>;
  if(row.status==='inconclusive'){
    const reason=typeof row.reason==='string'&&Object.hasOwn(REASONS,row.reason)
      ? row.reason : 'provider_inconclusive';
    return {status:'inconclusive',reason:REASONS[reason]};
  }
  if(row.status==='ok'&&row.engine==='azure-whisper-blend-v1'){
    const numeric=typeof row.combined==='number' && Number.isFinite(row.combined) &&
                  Number.isInteger(row.combined) && row.combined>=0 && row.combined<=100;
    const hints=parseColourHints(row.colourHints);
    if(row.calibration!=='experimental-uncalibrated'||!numeric||!hints){
      throw new Error('Assessment response unavailable.');
    }
    return {status:'ok',engine:'azure-whisper-blend-v1',calibration:'experimental-uncalibrated',
            combined:row.combined as number,colourHints:hints};
  }
  if(row.status!=='ok'||row.engine!=='azure-pl-PL-scripted'||
      row.calibration!=='uncalibrated'||!row.scores||typeof row.scores!=='object'){
    throw new Error('Assessment response unavailable.');
  }
  const scores=row.scores as Record<string,unknown>;
  const finite=(value:unknown):value is number=>
    typeof value==='number' && Number.isFinite(value) && value>=0 && value<=100;
  if(!finite(scores.accuracy)||!finite(scores.fluency)||!finite(scores.completeness)){
    throw new Error('Assessment response unavailable.');
  }
  const syllableFeedback=parseCalibratedSyllables(row.syllableFeedback);
  return {status:'ok',engine:'azure-pl-PL-scripted',calibration:'uncalibrated',
          scores:{accuracy:scores.accuracy,fluency:scores.fluency,completeness:scores.completeness},
          ...(syllableFeedback ? {syllableFeedback} : {})};
}

export async function requestSpeechFeedback(
  capture:AssessmentReadyCapture, token:string, signal?:AbortSignal, blended=false,
):Promise<SpeechFeedback>{
  if(!SPEECH_ASSESSMENT_AVAILABLE || (blended && !SPEECH_BLEND_AVAILABLE) ||
      !FAMILY_API || !token || capture.check.quality!=='usable'){
    throw new Error('Pronunciation feedback is unavailable.');
  }
  const body=new FormData();
  body.append('item_id',capture.itemId);
  body.append('audio',capture.wav,'learner.wav');
  body.append('approve_azure_audio_upload','yes');
  if(blended)body.append('approve_groq_audio_upload','yes');
  const started=performance.now();
  const response=await fetch(FAMILY_API+(blended?'/api/v2/family/speech/assess-blend':'/api/v2/family/speech/assess'),{
    method:'POST',
    headers:{Authorization:'Bearer '+token},
    body,cache:'no-store',signal,
  });
  if(!response.ok){
    if(response.status===429)throw new Error('Daily free pronunciation assessment limit reached. You can still practise and replay.');
    if(response.status===503)throw new Error('Pronunciation assessment is not available on this server. Recording and replay still work.');
    if(response.status===401)throw new Error('Sign in again to request pronunciation feedback.');
    throw new Error('Pronunciation assessment could not be completed. Please try again later.');
  }
  const feedback=parseSpeechFeedback(await response.json());
  const elapsed=performance.now()-started;
  const roundTripMs=Number.isFinite(elapsed) ? Math.round(Math.max(0,elapsed)) : 0;
  // This header is duration-only and is exposed by the private API. Never
  // show untrusted server strings or claim the SDK value is pure inference time.
  const rawTiming=response.headers.get('Server-Timing') || '';
  const matched=/(?:^|,)\s*speech-sdk;dur=(\d+(?:\.\d+)?)(?:\s*(?:,|$))/.exec(rawTiming);
  const sdk=matched?Number(matched[1]):null;
  const timing:SpeechTiming={roundTripMs};
  if(sdk!==null && Number.isFinite(sdk) && sdk>=0 && sdk<=120000){
    timing.sdkMs=Math.round(sdk);
  }
  return {...feedback,timing};
}
