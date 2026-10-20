import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import path from 'node:path';

function fakeWav(){
  const samples=16000*2;
  const out=Buffer.alloc(44+samples*2);
  out.write('RIFF',0);out.writeUInt32LE(out.length-8,4);out.write('WAVE',8);
  out.write('fmt ',12);out.writeUInt32LE(16,16);out.writeUInt16LE(1,20);
  out.writeUInt16LE(1,22);out.writeUInt32LE(16000,24);
  out.writeUInt32LE(32000,28);out.writeUInt16LE(2,32);
  out.writeUInt16LE(16,34);out.write('data',36);out.writeUInt32LE(samples*2,40);
  for(let i=0;i<samples;i++)out.writeInt16LE(Math.round(4400*Math.sin(.17*i)),44+i*2);
  return out;
}
const localHtml='file://'+path.resolve('../../v2/benchmarks/syllable_listening_lab.html');

test('offline original-WAV audition listens to 4 real byte intervals and exports timings only',async({page})=>{
  const remote:string[]=[];
  page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url());});
  await page.goto(localHtml);
  await expect(page.getByText(/No Whisper guess, Azure request/)).toBeVisible();
  await expect(page.locator('button[data-segment]')).toHaveCount(4);
  await page.locator('#wav').setInputFiles({
    name:'private-original.wav',mimeType:'audio/wav',buffer:fakeWav()
  });
  await expect(page.getByText(/Loaded locally/)).toBeVisible();
  await expect(page.locator('button[data-segment="2"]')).toBeEnabled();
  await page.locator('button[data-segment="2"]').click();
  await page.locator('#stop').click();
  await page.locator('#cut2').fill('1.01');
  await expect(page.locator('#cut2 + output')).toContainText('1.01');
  const pending=page.waitForEvent('download');
  await page.locator('#save').click();
  const download=await pending;
  expect(download.suggestedFilename()).toBe('ptp-private-syllable-timings.json');
  const stream=await download.createReadStream();
  const chunks:Buffer[]=[];
  for await(const c of stream)chunks.push(Buffer.from(c));
  const raw=Buffer.concat(chunks).toString('utf8');
  const timing=JSON.parse(raw);
  expect(timing.method).toBe('manual-syllable-audition-v1');
  expect(timing.syllables).toEqual(['Świę','to','krzy','ska']);
  expect(timing.intervals).toHaveLength(4);
  expect(timing.intervals[1].endSeconds).toBeCloseTo(1.01,2);
  expect(timing.scores).toBeNull();
  expect(timing.sourceSha256).toMatch(/^[0-9a-f]{64}$/);
  expect(timing.sourceBytes).toBe(fakeWav().length);
  expect(raw).not.toContain('RIFF');
  expect(raw).not.toContain('fakeWav');
  expect(remote).toEqual([]);
});

test('offline listener rejects unsupported/invalid input rather than making fake clips',async({page})=>{
  const remote:string[]=[];
  page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url());});
  await page.goto(localHtml);
  await page.locator('#wav').setInputFiles({
    name:'not-a-voice.wav',mimeType:'audio/wav',buffer:Buffer.from('fake')
  });
  await expect(page.locator('#status')).toContainText('Choose a WAV smaller than 10 MB.');
  await expect(page.locator('#save')).toBeDisabled();
  await expect(page.locator('button[data-segment="0"]')).toBeDisabled();
  expect(remote).toEqual([]);
});
