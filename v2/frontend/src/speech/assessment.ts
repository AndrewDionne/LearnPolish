/** No Azure key or raw provider JSON reaches the browser. */
import type {AssessmentReadyCapture} from './format';
import {FAMILY_API} from '../family/api';

export type SpeechTiming = {roundTripMs:number;sdkMs?:number};

export type SpeechFeedback =
  | {status:'ok'; engine:'azure-pl-PL-scripted'; calibration:'uncalibrated';
     scores:{accuracy:number;fluency:number;completeness:number};timing?:SpeechTiming}
  | {status:'inconclusive'; reason:string;timing?:SpeechTiming};

const REASONS:Record<string,string>={
  no_match:'Azure could not recognize enough speech. Try again.',
  canceled:'Azure could not complete this assessment. You can replay or try again.',
  no_assessment:'Azure did not return enough pronunciation information to score this take.',
  provider_inconclusive:'Pronunciation feedback was unavailable for this take.',
  provider_unavailable:'Pronunciation feedback is temporarily unavailable.',
};

export const SPEECH_ASSESSMENT_AVAILABLE =
  import.meta.env.VITE_SPEECH_ASSESSMENT_ENABLED === 'true' && Boolean(FAMILY_API);

/** Validate untrusted service replies. Unrecognized/missing grades are never zero. */
export function parseSpeechFeedback(input:unknown):SpeechFeedback {
  if(!input || typeof input!=='object')throw new Error('Assessment response unavailable.');
  const row=input as Record<string,unknown>;
  if(row.status==='inconclusive'){
    const reason=typeof row.reason==='string'&&Object.hasOwn(REASONS,row.reason)
      ? row.reason : 'provider_inconclusive';
    return {status:'inconclusive',reason:REASONS[reason]};
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
  return {status:'ok',engine:'azure-pl-PL-scripted',calibration:'uncalibrated',
          scores:{accuracy:scores.accuracy,fluency:scores.fluency,completeness:scores.completeness}};
}

export async function requestSpeechFeedback(
  capture:AssessmentReadyCapture, token:string, signal?:AbortSignal,
):Promise<SpeechFeedback>{
  if(!SPEECH_ASSESSMENT_AVAILABLE || !FAMILY_API || !token ||
      capture.check.quality!=='usable'){
    throw new Error('Pronunciation feedback is unavailable.');
  }
  const body=new FormData();
  body.append('item_id',capture.itemId);
  body.append('audio',capture.wav,'learner.wav');
  body.append('approve_azure_audio_upload','yes');
  const started=performance.now();
  const response=await fetch(FAMILY_API+'/api/v2/family/speech/assess',{
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
