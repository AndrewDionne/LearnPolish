import {test,expect} from '@playwright/test';

// Synthetic WAV and intercepted HTTP ONLY. Never call Azure/Groq or use user audio.
test.skip(!process.env.VITE_FAMILY_API_URL ||
          process.env.VITE_SPEECH_ASSESSMENT_ENABLED!=='true' ||
          process.env.VITE_SPEECH_BLEND_ENABLED!=='true',
          'Requires isolated opt-in two-provider browser fixture');

const ok=(body:unknown)=>({status:200,contentType:'application/json',body:JSON.stringify(body)});

async function syntheticMicrophone(page:import('@playwright/test').Page){
  await page.addInitScript(()=>{
    const count=16000,bytes=new ArrayBuffer(44+count*2),v=new DataView(bytes);
    for(const [at,part] of [[0,'RIFF'],[8,'WAVE'],[12,'fmt '],[36,'data']] as const)
      for(let i=0;i<part.length;i++)v.setUint8(at+i,part.charCodeAt(i));
    v.setUint32(4,bytes.byteLength-8,true);v.setUint32(16,16,true);
    v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,16000,true);
    v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);
    v.setUint32(40,count*2,true);
    for(let i=0;i<count;i++)v.setInt16(44+i*2,Math.round(5500*Math.sin(i*.2)),true);
    Object.defineProperty(navigator.mediaDevices,'getUserMedia',{
      configurable:true,value:async()=>({getTracks:()=>[{stop:()=>{}}]})});
    class FakeRecorder{
      static isTypeSupported(_:string){return true;}
      mimeType='audio/wav';state='inactive';
      ondataavailable:((e:{data:Blob})=>void)|null=null;
      onstop:(()=>void)|null=null;
      constructor(_stream:unknown,_options?:unknown){}
      start(){this.state='recording';}
      stop(){this.state='inactive';queueMicrotask(()=>{
        this.ondataavailable?.({data:new Blob([bytes],{type:'audio/wav'})});
        this.onstop?.();
      });}
    }
    Object.defineProperty(window,'MediaRecorder',{configurable:true,value:FakeRecorder});
  });
}
async function connect(page:import('@playwright/test').Page){
  await page.route('**/api/v2/family/health',r=>r.fulfill(ok({
    ok:true,email_verification_available:true,password_recovery_available:true})));
  await page.route('**/api/v2/family/login',r=>r.fulfill(ok({
    token:'synthetic-browser-session'})));
  await page.route('**/api/v2/family/me',r=>r.fulfill(ok({
    user:{id:1,name:'Test adult'},families:[{id:9,name:'Study group',can_invite:true}]})));
  await page.route('**/api/v2/family/groups/9/summary',r=>r.fulfill(ok({
    group:{id:9,name:'Study group',can_invite:true},members:[],regions:[],
    totals:{weekly_xp:0,regions_unlocked:0},recognition:{improvement:'pending_validated_evidence'}})));
  await page.goto('/');
  await page.getByRole('button',{name:'Expedition'}).first().click();
  const panel=page.getByRole('region',{name:'Family expedition'});
  await panel.getByRole('button',{name:'Sign in',exact:true}).click();
  await panel.getByLabel('Email').fill('adult@example.test');
  await panel.getByLabel('Password').fill('test-only-passphrase');
  await panel.getByRole('button',{name:'Sign in to family'}).click();
  await panel.getByLabel('Choose family group').selectOption('9');
  await panel.getByRole('checkbox',{name:/Contribute my/}).check();
}
async function record(page:import('@playwright/test').Page){
  await page.getByRole('button',{name:/Start recording|Record another take/}).click();
  await page.getByRole('button',{name:'Stop recording'}).click();
  await expect(page.getByText(/Recording captured/)).toBeVisible();
}

test('normal Speak shows coloured source syllables with gaps and only 67 combined, consented twice',async({page})=>{
  await syntheticMicrophone(page);
  let calls=0;
  await page.route('**/api/v2/family/speech/assess-blend',async route=>{
    calls++;
    const req=route.request();
    expect(req.method()).toBe('POST');
    expect(req.headers().authorization).toBe('Bearer synthetic-browser-session');
    const form=req.postDataBuffer()?.toString('latin1')??'';
    expect(form).toContain('approve_azure_audio_upload');
    expect(form).toContain('approve_groq_audio_upload');
    expect(form).toContain('yes');
    expect(form).toContain('speak_swietokrzyska:0');
    expect(form).toContain('RIFF');
    await route.fulfill(ok({
      status:'ok',engine:'azure-whisper-blend-v1',calibration:'experimental-uncalibrated',
      combined:67,colourHints:{method:'whisper-transcript-proxy-v1',reference:'Świętokrzyska',
        segments:[{polish:'Świę',hint:'review'},{polish:'to',hint:'review'},
                  {polish:'krzy',hint:'focus'},{polish:'ska',hint:'close'}]},
      privateTranscript:'NEVER SHOW PRIVATE TRANSCRIPTION',azureAccuracy:84,whisperSimilarity:50
    }));
  });
  await page.route('**/api/v2/family/speech/assess',async _=>{throw new Error('Unexpected Azure-only route')});
  await connect(page);
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Świętokrzyska');
  await page.getByRole('button',{name:/Świętokrzyska/}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  expect(calls).toBe(0);
  await record(page);
  await expect(page.getByText(/Azure and Groq Whisper for estimated feedback/)).toBeVisible();
  await page.getByRole('button',{name:'Check my pronunciation'}).click();
  await expect(page.locator('.speak-blended-part')).toHaveText(['Świę','to','krzy','ska']);
  await expect(page.locator('.speak-blended-part.review')).toHaveCount(2);
  await expect(page.locator('.speak-blended-part.focus')).toHaveCount(1);
  await expect(page.locator('.speak-blended-part.close')).toHaveCount(1);
  await expect(page.locator('.speak-word-score-primary')).toHaveText('67/100');
  await expect(page.locator('.speak-word-score')).toHaveCount(0);
  await expect(page.locator('.speak-score-explanation')).toHaveCount(0);
  await expect(page.locator('.speak-blended-word')).toHaveCSS('gap',/.+/);
  await expect(page.getByText('NEVER SHOW PRIVATE TRANSCRIPTION')).toHaveCount(0);
  await expect(page.getByText('84/100')).toHaveCount(0);
  await expect(page.getByText('50/100')).toHaveCount(0);
  expect(calls).toBe(1);
  await page.getByRole('button',{name:/Record another take/}).click();
  await expect(page.locator('.speak-blended-word')).toHaveCount(0);
  await expect(page.locator('.speak-scores')).toHaveCount(0);
  expect(calls).toBe(1);
});
