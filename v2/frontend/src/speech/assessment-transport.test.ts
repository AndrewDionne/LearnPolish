import {afterEach,describe,expect,test,vi} from 'vitest';
import {encodePcm16Wav,inspectPcm16} from './format';
import type {AssessmentReadyCapture} from './format';

vi.mock('../family/api',()=>({FAMILY_API:'https://private-family.test'}));

const capture=():AssessmentReadyCapture=>{
  const samples=Int16Array.from({length:16000},(_,i)=>Math.round(4000*Math.sin(i/8)));
  return {schemaVersion:1,itemId:'original:0',referencePolish:'Dzień dobry',
    wav:encodePcm16Wav(samples),check:inspectPcm16(samples)};
};
const azure={
  item_id:'original:0',status:'ok',engine:'azure-pl-PL-scripted',
  calibration:'uncalibrated',scores:{accuracy:83,fluency:90,completeness:100},
};
const blend={
  item_id:'original:0',status:'ok',engine:'azure-whisper-blend-v1',
  calibration:'experimental-uncalibrated',combined:67,
  colourHints:{method:'whisper-transcript-proxy-v1',reference:'Dzień dobry',
    segments:[{polish:'Dzień ',hint:'review'},{polish:'dobry',hint:'close'}]},
};
async function ready(){
  vi.stubEnv('VITE_SPEECH_ASSESSMENT_ENABLED','true');
  vi.stubEnv('VITE_SPEECH_BLEND_ENABLED','true');
  vi.resetModules();
  const module=await import('./assessment');
  expect(module.SPEECH_ASSESSMENT_AVAILABLE).toBe(true);
  expect(module.SPEECH_BLEND_AVAILABLE).toBe(true);
  return module.requestSpeechFeedback;
}
function reply(payload:unknown,status=200,headers:Record<string,string>={}){
  return new Response(JSON.stringify(payload),{
    status,headers:{'Content-Type':'application/json',...headers},
  });
}

describe('DPT-04 optional pronunciation transport — fully mocked, no external audio uploads',()=>{
  afterEach(()=>{
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.resetModules();
    vi.restoreAllMocks();
  });

  test('already aborted capture causes no network request',async()=>{
    const request=await ready();
    const spy=vi.fn();
    vi.stubGlobal('fetch',spy);
    const controller=new AbortController();
    controller.abort();
    await expect(request(capture(),'synthetic-token',controller.signal)).rejects.toMatchObject({name:'AbortError'});
    expect(spy).not.toHaveBeenCalled();
  });

  test('in-flight abort cannot surface a grade even if transport resolves afterward',async()=>{
    const request=await ready();
    let resolve!: (value:Response)=>void;
    const pending=new Promise<Response>(done=>{resolve=done;});
    const spy=vi.fn(()=>pending);
    vi.stubGlobal('fetch',spy);
    const controller=new AbortController();
    const attempt=request(capture(),'synthetic-token',controller.signal);
    expect(spy).toHaveBeenCalledTimes(1);
    controller.abort();
    resolve(reply(azure));
    await expect(attempt).rejects.toMatchObject({name:'AbortError'});
  });

  test('network/proxy exceptions are sanitized and never leak a provider transcript',async()=>{
    const request=await ready();
    const spy=vi.fn().mockRejectedValue(new Error('private-endpoint?key=SECRET / spoken transcript'));
    vi.stubGlobal('fetch',spy);
    await expect(request(capture(),'synthetic-token')).rejects.toThrow(
      'Pronunciation assessment could not be completed. Please try again later.');
    expect(spy).toHaveBeenCalledTimes(1); // no silent retry/cost
    try{await request(capture(),'synthetic-token');}catch(e){
      expect(String(e)).not.toContain('SECRET');
      expect(String(e)).not.toContain('transcript');
    }
  });

  test.each([
    [429,'Daily free pronunciation assessment limit reached'],
    [503,'Pronunciation assessment is not available on this server'],
    [401,'Sign in again to request pronunciation feedback'],
    [502,'Pronunciation assessment could not be completed'],
  ])('HTTP %i returns a bounded, user-safe message',async(status,message)=>{
    const request=await ready();
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(reply({error:'SECRET provider trace'},status)));
    await expect(request(capture(),'synthetic-token')).rejects.toThrow(message);
  });

  test('malformed JSON, wrong item and cross-engine responses cannot display a score',async()=>{
    const request=await ready();
    const invalid=[
      new Response('not a JSON document',{status:200}),
      reply({...azure,item_id:'other:8'}),
      reply({...azure,item_id:null}),
      reply({...blend}),
    ];
    const spy=vi.fn().mockImplementation(async()=>invalid.shift());
    vi.stubGlobal('fetch',spy);
    for(let i=0;i<4;i++){
      await expect(request(capture(),'synthetic-token')).rejects.toThrow(
        'Assessment response unavailable.');
    }
    expect(spy).toHaveBeenCalledTimes(4);
  });

  test('blend result requires matching reference and engine, never a swapped card',async()=>{
    const request=await ready();
    const spy=vi.fn()
      .mockResolvedValueOnce(reply({...blend,colourHints:{...blend.colourHints,reference:'Other word',
        segments:[{polish:'Other word',hint:'close'}]}}))
      .mockResolvedValueOnce(reply(azure))
      .mockResolvedValueOnce(reply(blend));
    vi.stubGlobal('fetch',spy);
    await expect(request(capture(),'synthetic-token',undefined,true)).rejects.toThrow(
      'Assessment response unavailable.');
    await expect(request(capture(),'synthetic-token',undefined,true)).rejects.toThrow(
      'Assessment response unavailable.');
    const accepted=await request(capture(),'synthetic-token',undefined,true);
    expect(accepted.status).toBe('ok');
    if(accepted.status==='ok'&&accepted.engine==='azure-whisper-blend-v1'){
      expect(accepted.combined).toBe(67);
    }
  });

  test('one validated WAV is posted to the intended route with only the approved provider consents',async()=>{
    const request=await ready();
    const recordings=capture();
    const spy=vi.fn(async (_url:string)=>reply(azure,200,{'Server-Timing':'speech-sdk;dur=12.4'}));
    vi.stubGlobal('fetch',spy);
    const feedback=await request(recordings,'synthetic-token');
    expect(feedback.status).toBe('ok');
    if(feedback.status==='ok')expect(feedback.timing).toEqual({roundTripMs:expect.any(Number),sdkMs:12});
    expect(spy).toHaveBeenCalledTimes(1);
    const [url,init]=spy.mock.calls[0] as [string,RequestInit];
    expect(url).toBe('https://private-family.test/api/v2/family/speech/assess');
    expect(init.method).toBe('POST');
    expect(init.cache).toBe('no-store');
    const fields=init.body as FormData;
    expect(fields.get('item_id')).toBe('original:0');
    expect(fields.get('approve_azure_audio_upload')).toBe('yes');
    expect(fields.has('approve_groq_audio_upload')).toBe(false);
    const submitted=fields.get('audio');
    expect(submitted).toBeInstanceOf(Blob);
    expect([...new Uint8Array(await (submitted as Blob).arrayBuffer())]).toEqual(
      [...new Uint8Array(await recordings.wav.arrayBuffer())]);
    expect(JSON.stringify(feedback)).not.toContain('synthetic-token');
  });

  test('inconclusive provider reply is not zero, does not retain provider payload',async()=>{
    const request=await ready();
    const spy=vi.fn(async()=>reply({
      item_id:'original:0',status:'inconclusive',reason:'provider_unavailable',
      privateTranscript:'do not keep transcript',scores:{accuracy:0},
    }));
    vi.stubGlobal('fetch',spy);
    const feedback=await request(capture(),'synthetic-token');
    expect(feedback.status).toBe('inconclusive');
    expect(JSON.stringify(feedback)).not.toContain('scores');
    expect(JSON.stringify(feedback)).not.toContain('transcript');
  });
});
