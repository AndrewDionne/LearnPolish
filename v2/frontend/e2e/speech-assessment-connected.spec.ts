import {test,expect} from '@playwright/test';

// Entirely synthetic microphone and stubbed provider response. No learner audio,
// keys, external provider calls, or billing in this browser test.
test.skip(!process.env.VITE_FAMILY_API_URL || process.env.VITE_SPEECH_ASSESSMENT_ENABLED!=='true',
  'Requires explicitly configured connected-browser pronunciation test');

function installSyntheticMicrophone(page:import('@playwright/test').Page){
  return page.addInitScript(()=>{
    const count=16000;
    const bytes=new ArrayBuffer(44+count*2);
    const v=new DataView(bytes);
    for(const [offset,value] of [[0,'RIFF'],[8,'WAVE'],[12,'fmt '],[36,'data']] as const){
      for(let i=0;i<value.length;i++)v.setUint8(offset+i,value.charCodeAt(i));
    }
    v.setUint32(4,bytes.byteLength-8,true);v.setUint32(16,16,true);
    v.setUint16(20,1,true);v.setUint16(22,1,true);
    v.setUint32(24,16000,true);v.setUint32(28,32000,true);
    v.setUint16(32,2,true);v.setUint16(34,16,true);
    v.setUint32(40,count*2,true);
    for(let i=0;i<count;i++)v.setInt16(44+i*2,Math.round(5500*Math.sin(i*.2)),true);
    const stream={getTracks:()=>[{stop:()=>{}}]};
    Object.defineProperty(navigator.mediaDevices,'getUserMedia',{
      configurable:true,value:async()=>stream,
    });
    class Recorder {
      static isTypeSupported(_:string){return true;}
      mimeType='audio/wav';state='inactive';
      ondataavailable:((e:{data:Blob})=>void)|null=null;
      onstop:(()=>void)|null=null;
      onerror:(()=>void)|null=null;
      constructor(_stream:unknown,_options?:unknown){}
      start(){this.state='recording';}
      stop(){
        this.state='inactive';
        queueMicrotask(()=>{
          this.ondataavailable?.({data:new Blob([bytes],{type:'audio/wav'})});
          this.onstop?.();
        });
      }
    }
    Object.defineProperty(window,'MediaRecorder',{configurable:true,value:Recorder});
  });
}

async function connectPrivateAdult(page:import('@playwright/test').Page){
  const json=(body:unknown)=>({status:200,contentType:'application/json',body:JSON.stringify(body)});
  await page.route('**/api/v2/family/health',route=>route.fulfill(json({
    ok:true,email_verification_available:true,password_recovery_available:true
  })));
  await page.route('**/api/v2/family/login',route=>route.fulfill(json({token:'synthetic-browser-session'})));
  await page.route('**/api/v2/family/me',route=>route.fulfill(json({
    user:{id:1,name:'Test adult'},families:[{id:9,name:'Study group',can_invite:true}]
  })));
  await page.route('**/api/v2/family/groups/9/summary',route=>route.fulfill(json({
    group:{id:9,name:'Study group',can_invite:true},members:[],regions:[],
    totals:{weekly_xp:0,regions_unlocked:0},recognition:{improvement:'pending_validated_evidence'}
  })));
  await page.goto('/');
  await page.getByRole('button',{name:'Expedition'}).first().click();
  const panel=page.getByRole('region',{name:'Family expedition'});
  await panel.getByRole('button',{name:'Sign in',exact:true}).click();
  await panel.getByLabel('Email').fill('adult@example.test');
  await panel.getByLabel('Password').fill('test-only-passphrase');
  await panel.getByRole('button',{name:'Sign in to family'}).click();
  await panel.getByLabel('Choose family group').selectOption('9');
  await panel.getByRole('checkbox',{name:/Contribute my/}).check();
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Conversation 1');
  await page.getByRole('button',{name:/Conversation 1/}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await expect(page.getByText('Dzień dobry',{exact:true})).toBeVisible();
}

async function recordValidTake(page:import('@playwright/test').Page){
  await page.getByRole('button',{name:/Start recording|Record another take/}).click();
  await page.getByRole('button',{name:'Stop recording'}).click();
  await expect(page.getByText(/Recording captured/)).toBeVisible();
}

test('explicit consent -> native Azure numbers -> replay/next without fabricated grade or hidden second request',async({page})=>{
  await installSyntheticMicrophone(page);
  let calls=0;
  await page.route('**/api/v2/family/speech/assess',async route=>{
    calls++;
    const r=route.request();
    expect(r.method()).toBe('POST');
    expect(r.headers().authorization).toBe('Bearer synthetic-browser-session');
    const body=r.postDataBuffer()?.toString('latin1')??'';
    expect(body).toContain('approve_azure_audio_upload');
    expect(body).toContain('yes');
    expect(body).toContain('item_id');
    expect(body).toContain('RIFF');
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
      status:'ok',engine:'azure-pl-PL-scripted',calibration:'uncalibrated',
      scores:{accuracy:93,fluency:82,completeness:90},
      rawText:'DO_NOT_DISPLAY_PRIVATE_TRANSCRIPT'
    })});
  });
  await connectPrivateAdult(page);
  await expect(page.getByRole('button',{name:'Check my pronunciation'})).toHaveCount(0);
  await recordValidTake(page);
  await expect(page.getByRole('button',{name:'Check my pronunciation'})).toBeVisible();
  expect(calls).toBe(0);
  await page.getByRole('button',{name:'Check my pronunciation'}).click();
  await expect(page.getByText('93.0 / 100')).toBeVisible();
  await expect(page.getByText('82.0 / 100')).toBeVisible();
  await expect(page.getByText('90.0 / 100')).toBeVisible();
  await expect(page.getByText(/not been calibrated/)).toBeVisible();
  await expect(page.getByText('DO_NOT_DISPLAY_PRIVATE_TRANSCRIPT')).toHaveCount(0);
  expect(calls).toBe(1);
  await page.getByRole('button',{name:/Next phrase/}).click();
  await expect(page.getByText('Dobry wieczór',{exact:true})).toBeVisible();
  await expect(page.locator('.speak-scores')).toHaveCount(0);
  await expect(page.locator('#personal-speech-replay')).toHaveCount(0);
  expect(calls).toBe(1);
  await page.screenshot({path:'test-results/speak-azure-e2e.png',fullPage:true});
});

test('inconclusive and quota outcomes stay ungraded; new take clears old feedback',async({page})=>{
  await installSyntheticMicrophone(page);
  let calls=0;
  await page.route('**/api/v2/family/speech/assess',route=>{
    calls++;
    return calls===1
      ? route.fulfill({status:200,contentType:'application/json',
          body:JSON.stringify({status:'inconclusive',reason:'no_match'})})
      : route.fulfill({status:429,contentType:'application/json',body:'{}'});
  });
  await connectPrivateAdult(page);
  await recordValidTake(page);
  await page.getByRole('button',{name:'Check my pronunciation'}).click();
  await expect(page.getByText(/could not recognize enough speech/)).toBeVisible();
  await expect(page.getByText(/This is not a score of zero/)).toBeVisible();
  await expect(page.locator('.speak-scores')).toHaveCount(0);
  await page.getByRole('button',{name:/Record another take/}).click();
  await expect(page.getByText(/This is not a score of zero/)).toHaveCount(0);
  await page.getByRole('button',{name:'Stop recording'}).click();
  await expect(page.getByText(/Recording captured/)).toBeVisible();
  await page.getByRole('button',{name:'Check my pronunciation'}).click();
  await expect(page.getByText(/Daily free pronunciation assessment limit reached/)).toBeVisible();
  expect(calls).toBe(2);
  await expect(page.locator('.speak-scores')).toHaveCount(0);
  await page.getByRole('button',{name:/Next phrase/}).click();
  await expect(page.getByText('Dobry wieczór',{exact:true})).toBeVisible();
});

test('Świętokrzyska is a real built-in Speak test item with opt-in timing, not fake native audio',async({page})=>{
  await installSyntheticMicrophone(page);
  let calls=0;
  await page.route('**/api/v2/family/speech/assess', async route=>{
    calls++;
    const body=route.request().postDataBuffer()?.toString('latin1')??'';
    expect(body).toContain('speak_swietokrzyska:0');
    expect(body).toContain('approve_azure_audio_upload');
    await route.fulfill({
      status:200,contentType:'application/json',
      headers:{'Server-Timing':'speech-sdk;dur=4020.0','Access-Control-Expose-Headers':'Server-Timing'},
      body:JSON.stringify({status:'ok',engine:'azure-pl-PL-scripted',
        calibration:'uncalibrated',scores:{accuracy:77,fluency:88,completeness:100},
        rawText:'NEVER-DISPLAY-RAW-SPEECH'}),
    });
  });
  await connectPrivateAdult(page);
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Świętokrzyska');
  await page.getByRole('button',{name:/Świętokrzyska/}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await expect(page.getByText('Świętokrzyska',{exact:true})).toBeVisible();
  await expect(page.getByText(/Native reference audio is not available/)).toBeVisible();
  await expect(page.getByText(/Read the Polish word/)).toBeVisible();
  await expect(page.getByRole('button',{name:'Check my pronunciation'})).toHaveCount(0);
  await recordValidTake(page);
  expect(calls).toBe(0);
  await page.getByRole('button',{name:'Check my pronunciation'}).click();
  await expect(page.getByText('77.0 / 100')).toBeVisible();
  await expect(page.getByText(/Azure SDK call 4\.0 s/)).toBeVisible();
  await expect(page.getByText('NEVER-DISPLAY-RAW-SPEECH')).toHaveCount(0);
  expect(calls).toBe(1);
  await page.getByRole('button',{name:/Record another take/}).click();
  await expect(page.locator('.speak-latency')).toHaveCount(0);
  await expect(page.locator('.speak-scores')).toHaveCount(0);
});



test('site permission allowed but macOS/browser rejects mic shows distinct diagnostic, no Azure call',async({page})=>{
  await page.addInitScript(()=>{
    Object.defineProperty(navigator,'permissions',{
      configurable:true,value:{
        query:async()=>({state:'granted'}),
      },
    });
    Object.defineProperty(navigator.mediaDevices,'getUserMedia',{
      configurable:true,value:async()=>{
        throw new DOMException('TEST ONLY: inaccessible microphone','NotAllowedError');
      },
    });
  });
  let azureCalls=0;
  await page.route('**/api/v2/family/speech/assess',route=>{
    azureCalls++;
    return route.fulfill({status:500,body:'no calls expected'});
  });
  await page.goto('/');
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Świętokrzyska');
  await page.getByRole('button',{name:/Świętokrzyska/}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await page.getByRole('button',{name:/Start recording/}).click();
  await expect(page.getByRole('alert')).toContainText('already has microphone permission');
  await expect(page.getByRole('alert')).toContainText('Privacy & Security');
  await expect(page.getByRole('alert')).toContainText('Sound → Input');
  await expect(page.getByRole('button',{name:/Start recording/})).toBeEnabled();
  expect(azureCalls).toBe(0);
});
