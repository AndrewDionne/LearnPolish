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

function requestedItemId(route:import('@playwright/test').Route):string{
  const body=route.request().postDataBuffer()?.toString('latin1')??'';
  const match=/name="item_id"\r?\n\r?\n([^\r\n]+)/.exec(body);
  if(!match)throw new Error('Synthetic speech request omitted item_id');
  return match[1];
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
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
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
      item_id:requestedItemId(route),status:'ok',engine:'azure-pl-PL-scripted',calibration:'uncalibrated',
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
  await expect(page.getByRole('status').getByText('Pronunciation estimate')).toBeVisible();
  await expect(page.locator('.speak-word-score-primary')).toHaveText('93/100');
  await expect(page.locator('.speak-word-score-primary')).toHaveAttribute('aria-label','Azure word pronunciation accuracy estimate: 93 out of 100');
  await expect(page.locator('.speak-word-score')).toHaveCount(0);
  await expect(page.getByText('82.0 / 100')).not.toBeVisible();
  await expect(page.getByText('90.0 / 100')).not.toBeVisible();
  await page.locator('.speak-score-explanation summary').click();
  await expect(page.getByText(/not a syllable rating or pass\/fail grade/)).toBeVisible();
  await expect(page.getByText('82.0 / 100')).toBeVisible();
  await expect(page.getByText('90.0 / 100')).toBeVisible();
  await expect(page.getByText('DO_NOT_DISPLAY_PRIVATE_TRANSCRIPT')).toHaveCount(0);
  expect(calls).toBe(1);
  await page.getByRole('button',{name:'Next',exact:true}).click();
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
          body:JSON.stringify({item_id:requestedItemId(route),status:'inconclusive',reason:'no_match'})})
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
  await page.getByRole('button',{name:'Next',exact:true}).click();
  await expect(page.getByText('Dobry wieczór',{exact:true})).toBeVisible();
});

test('Świętokrzyska is a real built-in Świętokrzyska Pronunciation Lab item with opt-in timing, not fake native audio',async({page})=>{
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
      body:JSON.stringify({item_id:requestedItemId(route),status:'ok',engine:'azure-pl-PL-scripted',
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
  // Owner-approved minimal Speak: guide genuinely OFF by default,
  // no extra hero/export/footer and no second visible copy of the word.
  const guideToggle = page.getByRole('button',{name:/Pronunciation guide/});
  await expect(guideToggle).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('.speak-guided-word')).toHaveCount(0);
  await expect(page.locator('.speak-word-english')).toHaveCount(0);
  await expect(page.getByText('Practise speaking',{exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Export JSON'})).toHaveCount(0);
  await expect(page.locator('.lesson-footer')).toHaveCount(0);
  await expect(page.getByText(/Native reference audio is not available/)).toHaveCount(0);
  await expect(page.getByText(/Read the Polish word/)).toHaveCount(0);
  await expect(page.getByText('Street and metro station in Warsaw')).toBeVisible();
  expect(calls).toBe(0);
  await guideToggle.click();
  await expect(guideToggle).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.speak-word-segment')).toHaveCount(4);
  await expect(page.locator('.speak-word-english')).toHaveText(['shfyehn','toh','KSHIH','skah']);
  await expect(page.locator('.speak-word-segment.stressed')).toContainText('krzy');
  await guideToggle.click();
  await expect(guideToggle).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('.speak-word-english')).toHaveCount(0);
  expect(calls).toBe(0);
  const privacy = page.locator('.speak-private-details');
  await expect(privacy).not.toHaveAttribute('open');
  await privacy.locator('summary').click();
  await expect(privacy).toContainText('No native example is available');
  await expect(page.locator('.benchmark-export')).toHaveCount(0);
  await privacy.locator('summary').click();
  await expect(page.getByRole('button',{name:'Check my pronunciation'})).toHaveCount(0);
  await recordValidTake(page);
  expect(calls).toBe(0);
  await page.getByRole('button',{name:'Check my pronunciation'}).click();
  await expect(page.locator('.speak-word-score-primary')).toHaveText('77/100');
  await expect(page.getByText(/Azure SDK call 4\.0 s/)).toBeVisible();
  await expect(page.getByText('NEVER-DISPLAY-RAW-SPEECH')).toHaveCount(0);
  expect(calls).toBe(1);
  await page.getByRole('button',{name:/Record another take/}).click();
  await expect(page.locator('.speak-latency')).toHaveCount(0);
  await expect(page.locator('.speak-scores')).toHaveCount(0);
});



test('reserved acoustic-score UI aligns exact syllables with guide OFF/ON and clears on retry',async({page})=>{
  await installSyntheticMicrophone(page);
  // Synthetic contract fixture only. Production Azure pl-PL adapter does NOT
  // return verified syllabus scores, and no real voice/provider is contacted.
  await page.route('**/api/v2/family/speech/assess',route=>route.fulfill({
    status:200,contentType:'application/json',
    body:JSON.stringify({
      item_id:requestedItemId(route),status:'ok',engine:'azure-pl-PL-scripted',calibration:'uncalibrated',
      scores:{accuracy:81,fluency:90,completeness:100},
      syllableFeedback:{method:'reviewed-acoustic-syllables-v1',
        reference:'Świętokrzyska',
        segments:[{polish:'Świę',score:71.2},{polish:'to',score:88.3},
                  {polish:'krzy',score:null},{polish:'ska',score:95}]},
      rawTranscript:'NEVER DISPLAY THIS',
    }),
  }));
  await connectPrivateAdult(page);
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Świętokrzyska');
  await page.getByRole('button',{name:/Świętokrzyska Pronunciation Lab/}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  const toggle=page.getByRole('button',{name:/Pronunciation guide/});
  await expect(toggle).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('.speak-word-score')).toHaveCount(0);
  await recordValidTake(page);
  await page.getByRole('button',{name:'Check my pronunciation'}).click();
  await expect(page.locator('.speak-word-score')).toHaveText(['71%','88%','—','95%']);
  await expect(page.locator('.speak-word-polish')).toHaveText(['Świę','to','krzy','ska']);
  await expect(page.locator('.speak-word-english')).toHaveCount(0);
  await expect(page.getByText('NEVER DISPLAY THIS')).toHaveCount(0);
  await toggle.click();
  await expect(page.locator('.speak-word-english')).toHaveText(['shfyehn','toh','KSHIH','skah']);
  await expect(page.locator('.speak-word-score')).toHaveCount(4);
  await toggle.click();
  await expect(page.locator('.speak-word-english')).toHaveCount(0);
  await expect(page.locator('.speak-word-score')).toHaveCount(4);
  await page.getByRole('button',{name:/Record another take/}).click();
  await expect(page.locator('.speak-word-score')).toHaveCount(0);
  await expect(page.locator('.speak-scores')).toHaveCount(0);
  await expect(toggle).toHaveAttribute('aria-pressed','false');
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
