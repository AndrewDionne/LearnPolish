test('Sound Lab emphasizes only authored source letters without modifying full Polish audio targets', async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('C, CZ');
  await page.getByRole('button',{name:/C, CZ and Ć/}).click();
  const groups=page.locator('.contrast-group');
  await expect(groups).toHaveCount(3);
  await expect(groups.nth(0).locator('.sound-focus-letters')).toHaveText(['c','c']);
  await expect(groups.nth(1).locator('.sound-focus-letters')).toHaveText(['Cz','Cz']);
  await expect(groups.nth(2).locator('.sound-focus-letters')).toHaveText(['ć','ć']);
  await expect(groups.nth(1).locator('.contrast-focus',{hasText:'Cztery'})).toBeVisible();
  await expect(groups.nth(1).locator('.contrast-focus',{hasText:'Czechy'})).toBeVisible();
  await groups.nth(1).getByRole('button',{name:/Cztery/}).first().click();
  await expect(groups.nth(1).locator('.contrast-example.chosen')).toContainText('Cztery');
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('KRZY');
  await page.getByRole('button',{name:/KRZY and PRZY/}).click();
  await expect(page.locator('.sound-focus-letters')).toHaveText(['krzy','Krzy','Przy','przy']);
  await expect(page.locator('.contrast-focus',{hasText:'ulica Świętokrzyska'})).toBeVisible();
});

import {expect,test} from '@playwright/test';

// Offline, synthetic speech only. No real microphone, Azure, Groq, login, or scores.
async function installSyntheticMicrophone(page:import('@playwright/test').Page){
  await page.addInitScript(()=>{
    const count=16000, bytes=new ArrayBuffer(44+count*2), v=new DataView(bytes);
    for (const [offset,word] of [[0,'RIFF'],[8,'WAVE'],[12,'fmt '],[36,'data']] as const) {
      for(let i=0;i<word.length;i++)v.setUint8(offset+i,word.charCodeAt(i));
    }
    v.setUint32(4,bytes.byteLength-8,true);v.setUint32(16,16,true);
    v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,16000,true);
    v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);
    v.setUint32(40,count*2,true);
    for(let i=0;i<count;i++)v.setInt16(44+i*2,Math.round(5500*Math.sin(i*.2)),true);
    const stream={getTracks:()=>[{stop:()=>{}}]};
    Object.defineProperty(navigator.mediaDevices,'getUserMedia',{
      configurable:true,value:async()=>stream,
    });
    class Recorder {
      static isTypeSupported(_:string){return true;}
      mimeType='audio/wav';state='inactive';
      ondataavailable:((event:{data:Blob})=>void)|null=null;
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

async function readyTake(page:import('@playwright/test').Page){
  await page.getByRole('button',{name:/Start recording|Record another take/}).click();
  await page.getByRole('button',{name:'Stop recording'}).click();
  await expect(page.getByText(/Recording captured/)).toBeVisible();
}

test('Świętokrzyska → focused KRZY sounds → original word without losing the guide',async({page})=>{
  await installSyntheticMicrophone(page);
  let uploads=0;
  await page.route('**/api/v2/family/speech/assess',route=>{uploads++;return route.abort();});
  await page.goto('/');
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Świętokrzyska Pronunciation Lab');
  await page.getByRole('button',{name:/Świętokrzyska Pronunciation Lab/}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await expect(page.getByText('Świętokrzyska',{exact:true})).toBeVisible();
  const toggle=page.getByRole('button',{name:/Pronunciation guide/});
  await toggle.click();
  await expect(page.locator('.speak-word-segment')).toHaveCount(4);
  await expect(page.getByRole('button',{name:/Practise krzy sounds/})).toHaveCount(0);
  await readyTake(page);
  await expect(page.locator('.speak-scores')).toHaveCount(0);
  await page.getByRole('button',{name:/Practise krzy sounds/}).click();

  await expect(page.getByRole('button',{name:/Back to Świętokrzyska/})).toBeVisible();
  await expect(page.getByRole('button',{name:'Speak',exact:true})).toHaveAttribute('aria-pressed','true');
  await expect(page.getByText('ulica Świętokrzyska',{exact:true})).toBeVisible();
  await expect(page.locator('.speak-word-segment')).toHaveCount(0);
  await expect(page.locator('.item-count')).toContainText('1');
  await page.getByRole('button',{name:'Sounds',exact:true}).click();
  await expect(page.locator('.contrast-group')).toHaveCount(1);
  await expect(page.locator('.contrast-group-label')).toContainText('KRZY');
  await expect(page.getByRole('button',{name:'Play ulica Świętokrzyska'})).toBeEnabled();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await readyTake(page);
  await page.getByRole('button',{name:'Next',exact:true}).click();
  await expect(page.getByText('Krzysztof Wiśniewski',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Next',exact:true}).click();
  await expect(page.getByRole('button',{name:/Return to Świętokrzyska/})).toBeVisible();
  await page.getByRole('button',{name:/Return to Świętokrzyska/}).click();
  await expect(page.locator('.speak-word-segment')).toHaveCount(4);
  await expect(page.getByRole('button',{name:/Pronunciation guide/})).toHaveAttribute('aria-pressed','true');
  await expect(page.getByRole('button',{name:'Start recording'})).toBeVisible();
  await expect(page.locator('#personal-speech-replay')).toHaveCount(0);
  await expect(page.locator('.speak-scores')).toHaveCount(0);
  expect(uploads).toBe(0);
});

test('sound lesson is browsable directly, and abandoning a detour does not leave a stale return link',async({page})=>{
  await installSyntheticMicrophone(page);
  await page.goto('/');
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('KRZY');
  await page.getByRole('button',{name:/KRZY and PRZY/}).click();
  await expect(page.locator('.contrast-group')).toHaveCount(2);
  await expect(page.getByRole('button',{name:/Back to library/})).toBeVisible();
  await expect(page.getByRole('button',{name:/Back to Świętokrzyska/})).toHaveCount(0);
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await expect(page.getByText('ulica Świętokrzyska',{exact:true})).toBeVisible();
  await readyTake(page);
  await expect(page.locator('.speak-scores')).toHaveCount(0);
  await page.getByRole('button',{name:/Back to library/}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Świętokrzyska Pronunciation Lab');
  await page.getByRole('button',{name:/Świętokrzyska Pronunciation Lab/}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await readyTake(page);
  await page.getByRole('button',{name:/Practise krzy sounds/}).click();
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('KRZY');
  await page.getByRole('button',{name:/KRZY and PRZY/}).click();
  await expect(page.getByRole('button',{name:/Back to Świętokrzyska/})).toHaveCount(0);
  await expect(page.locator('.contrast-group')).toHaveCount(2);
});
