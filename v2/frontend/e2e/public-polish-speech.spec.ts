import {existsSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
import {test,expect} from '@playwright/test';

const dir=process.env.PTP_PUBLIC_POLISH_WAV_DIR;
test.skip(!dir || !existsSync(join(dir,'manifest.json')),
  'Explicit public-domain native Polish WAV fixture preparation required');

test('two actual public-domain Polish voices pass Learn/Speak capture and next-phrase UI',async({page})=>{
  if(!dir)throw new Error('Missing explicitly prepared fixture directory');
  const manifest=JSON.parse(readFileSync(join(dir,'manifest.json'),'utf8')) as {
    status:string;clips:Array<{id:string;text:string;wav:string;seconds:number;license:string}>
  };
  expect(manifest.status).toBe('public_reference_audio_only');
  expect(manifest.clips.map(x=>x.text)).toEqual(['Dzień dobry','Dobry wieczór']);
  expect(manifest.clips.every(x=>x.license==='Public domain'&&x.seconds>=.6&&x.seconds<=10)).toBe(true);

  // Keep bytes in the test runner. Page receives sample bytes ONLY as a
  // synthetic microphone, never via a remote model or browser HTTP upload.
  const encoded=manifest.clips.map(c=>readFileSync(join(dir,c.wav)).toString('base64'));
  await page.addInitScript((args:{recordings:string[]})=>{
    const samples=args.recordings.map(value=>Uint8Array.from(atob(value),c=>c.charCodeAt(0)));
    let next=0;
    (window as unknown as {__publicPolishClipCount:number}).__publicPolishClipCount=samples.length;
    const stream={getTracks:()=>[{stop:()=>{}}]};
    Object.defineProperty(navigator.mediaDevices,'getUserMedia',{
      configurable:true,value:async()=>stream
    });
    class NaturalVoiceRecorder {
      static isTypeSupported(mime:string){return mime==='audio/wav';}
      mimeType='audio/wav';state='inactive';
      ondataavailable:((event:{data:Blob})=>void)|null=null;
      onstop:(()=>void)|null=null;
      onerror:(()=>void)|null=null;
      constructor(_stream:unknown,_options?:unknown){}
      start(){this.state='recording';}
      stop(){
        this.state='inactive';
        const sample=samples[Math.min(next++,samples.length-1)];
        queueMicrotask(()=>{
          this.ondataavailable?.({data:new Blob([sample],{type:'audio/wav'})});
          this.onstop?.();
        });
      }
    }
    Object.defineProperty(window,'MediaRecorder',{configurable:true,value:NaturalVoiceRecorder});
  },{recordings:encoded});
  let providerCalls=0;
  await page.route('**/api/v2/family/speech/assess',route=>{
    providerCalls++;
    return route.abort();
  });
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  for(let index=0;index<manifest.clips.length;index++){
    await expect(page.getByText(manifest.clips[index].text,{exact:true})).toBeVisible();
    await page.getByRole('button',{name:/Start recording/}).click();
    await expect(page.getByRole('button',{name:'Stop recording'})).toBeVisible();
    await page.getByRole('button',{name:'Stop recording'}).click();
    await expect(page.getByText(/Recording ready/)).toBeVisible();
    await expect(page.locator('#personal-speech-replay')).toHaveAttribute('src',/blob:/);
    await expect(page.getByText(/Recording ready/)).toBeVisible();
    await expect(page.locator('.speak-scores')).toHaveCount(0);
    if(index===0){
      await page.getByRole('button',{name:'Next',exact:true}).click();
      await expect(page.locator('#personal-speech-replay')).toHaveCount(0);
    }
  }
  expect(providerCalls).toBe(0);
  await page.screenshot({path:'test-results/public-polish-native-capture.png',fullPage:true});
});
