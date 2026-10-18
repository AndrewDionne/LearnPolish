import {describe,expect,test,vi,afterEach} from 'vitest';
import {parseSpeechFeedback,requestSpeechFeedback,SPEECH_ASSESSMENT_AVAILABLE} from './assessment';
import type {AssessmentReadyCapture} from './format';

describe('Pronunciation assessment contract — real Azure scores only',()=>{
  test('validates provider-measured scores rather than inventing a composite grade',()=>{
    const result=parseSpeechFeedback({status:'ok',engine:'azure-pl-PL-scripted',
      calibration:'uncalibrated',scores:{accuracy:93,fluency:93,completeness:92},
      rawText:'secret transcript never displayed'});
    expect(result).toEqual({status:'ok',engine:'azure-pl-PL-scripted',
      calibration:'uncalibrated',scores:{accuracy:93,fluency:93,completeness:92}});
    expect(JSON.stringify(result)).not.toContain('secret');
  });
  test('inconclusive provider response never becomes a zero score',()=>{
    expect(parseSpeechFeedback({status:'inconclusive',reason:'canceled'})).toEqual({
      status:'inconclusive',reason:'Azure could not complete this assessment. You can replay or try again.'});
    const unknown=parseSpeechFeedback({status:'inconclusive',reason:'PRIVATE-SDK-ERROR-TEXT'});
    expect(unknown.status).toBe('inconclusive');
    expect(JSON.stringify(unknown)).not.toContain('PRIVATE');
    expect(JSON.stringify(unknown)).not.toContain('scores');
  });
  test('rejects incomplete, NaN, non-provider or uncalibrated-looking fake scores',()=>{
    const base={status:'ok',engine:'azure-pl-PL-scripted',calibration:'uncalibrated'};
    for(const scores of [
      {accuracy:93,fluency:93},
      {accuracy:93,fluency:NaN,completeness:92},
      {accuracy:93,fluency:101,completeness:92},
      {accuracy:'93',fluency:93,completeness:92},
    ])expect(()=>parseSpeechFeedback({...base,scores})).toThrow('Assessment response unavailable');
    expect(()=>parseSpeechFeedback({...base,calibration:'certified',scores:{accuracy:93,fluency:93,completeness:92}}))
      .toThrow('Assessment response unavailable');
  });
  test('service disabled by default, no audio network or hidden provider calls',async()=>{
    expect(SPEECH_ASSESSMENT_AVAILABLE).toBe(false);
    const original=globalThis.fetch;
    const spy=vi.fn();
    globalThis.fetch=spy as typeof fetch;
    try{
      const fake={schemaVersion:1,itemId:'a:0',referencePolish:'Dzień dobry',
        wav:new Blob([new Uint8Array([1,2])],{type:'audio/wav'}),
        check:{quality:'usable',sampleRate:16000,seconds:1,rms:.2,clippedFraction:0,reason:''},
      } as AssessmentReadyCapture;
      await expect(requestSpeechFeedback(fake,'not-a-real-token')).rejects.toThrow('unavailable');
      expect(spy).not.toHaveBeenCalled();
    }finally{globalThis.fetch=original;}
  });
  afterEach(()=>vi.restoreAllMocks());
});
