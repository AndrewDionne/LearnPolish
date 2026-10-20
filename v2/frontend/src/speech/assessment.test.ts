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
  test('reviewed acoustic syllabus contract preserves exact numbers, nullable measurements and privacy',()=>{
    const evidence={method:'reviewed-acoustic-syllables-v1',
      reference:'Świętokrzyska',
      segments:[{polish:'Świę',score:71.3},{polish:'to',score:88},
                {polish:'krzy',score:null},{polish:'ska',score:92.7}]};
    const result=parseSpeechFeedback({status:'ok',engine:'azure-pl-PL-scripted',
      calibration:'uncalibrated',scores:{accuracy:83,fluency:92,completeness:100},
      syllableFeedback:evidence,DisplayText:'PRIVATE TRANSCRIPTION'});
    expect(result.status).toBe('ok');
    if(result.status==='ok') expect(result.syllableFeedback).toEqual(evidence);
    expect(JSON.stringify(result)).not.toContain('PRIVATE');
  });
  test('incomplete/unreviewed/misaligned phoneme hypotheses cannot enter learner feedback',()=>{
    const base={status:'ok',engine:'azure-pl-PL-scripted',calibration:'uncalibrated',
      scores:{accuracy:84,fluency:100,completeness:100}};
    const valid={method:'reviewed-acoustic-syllables-v1',
      reference:'Świętokrzyska',segments:[
        {polish:'Świę',score:50},{polish:'to',score:50},
        {polish:'krzy',score:0},{polish:'ska',score:100}]};
    for(const candidate of [
      {...valid,method:'whisper-text-edit-v1'},
      {...valid,segments:[{polish:'Świę',score:84},{polish:'to',score:84}]},
      {...valid,segments:valid.segments.map((x,i)=>i===2?{...x,score:NaN}:x)},
      {...valid,segments:valid.segments.map((x,i)=>i===2?{...x,score:-1}:x)},
      {...valid,reference:'other'},
      {...valid,segments:valid.segments.map((x,i)=>i===2?{...x,polish:'cz'}:x)},
      {...valid,segments:null},
    ]){
      const parsed=parseSpeechFeedback({...base,syllableFeedback:candidate});
      expect(parsed.status).toBe('ok');
      if(parsed.status==='ok')expect(parsed.syllableFeedback).toBeUndefined();
    }
    // Even well-formed observed-syllable numbers require the explicit
    // REVIEWED provenance; this is a fixture, not a live provider grade.
    const fakeProvider=parseSpeechFeedback({...base,syllableFeedback:{
      ...valid,method:'azure-pl-PL-scripted'}});
    if(fakeProvider.status==='ok')expect(fakeProvider.syllableFeedback).toBeUndefined();
  });
  test('blended 67 score and colour-only hints remove all transcript/provider internals',()=>{
    const base={status:'ok',engine:'azure-whisper-blend-v1',
      calibration:'experimental-uncalibrated',combined:67,
      colourHints:{method:'whisper-transcript-proxy-v1',reference:'Świętokrzyska',
        segments:[{polish:'Świę',hint:'review'},{polish:'to',hint:'review'},
                  {polish:'krzy',hint:'focus'},{polish:'ska',hint:'close'}]},
      privateTranscript:'DO_NOT_DISPLAY_PRIVATE_TRANSCRIPT',azureAccuracy:84,whisperSimilarity:50};
    const parsed=parseSpeechFeedback(base);
    expect(parsed.status).toBe('ok');
    if(parsed.status==='ok'&&parsed.engine==='azure-whisper-blend-v1'){
      expect(parsed.combined).toBe(67);
      expect(parsed.colourHints.segments.map(p=>p.hint)).toEqual(['review','review','focus','close']);
    }else throw new Error('Expected blended feedback');
    expect(JSON.stringify(parsed)).not.toContain('PRIVATE');
    expect(JSON.stringify(parsed)).not.toContain('azureAccuracy');
    expect(JSON.stringify(parsed)).not.toContain('whisperSimilarity');
    for(const bad of [
      {...base,combined:-1},{...base,combined:101},{...base,combined:NaN},
      {...base,calibration:'certified'},
      {...base,colourHints:{...base.colourHints,reference:'wrong'}},
      {...base,colourHints:{...base.colourHints,segments:[
        ...base.colourHints.segments.slice(0,-1),{polish:'ska',hint:'100%'}]}},
    ])expect(()=>parseSpeechFeedback(bad)).toThrow('Assessment response unavailable');
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
