import {expect,test} from '@playwright/test';

test('changing modes, replaying and leaving a lesson never overlap audio streams',async({page,isMobile})=>{
  const errors:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  // Deterministic audio lifecycle witness; not an acoustic quality assessment.
  // The app still calls the same native Audio.play/pause/load surfaces.
  await page.addInitScript(()=>{
    const active=new Set<HTMLMediaElement>();
    const status={starts:0,stops:0,active:0,maxActive:0};
    Object.defineProperty(window,'__ptpAudioLifecycle',{value:status,configurable:true});
    HTMLMediaElement.prototype.play=function(){
      active.add(this);status.starts++;
      status.active=active.size;status.maxActive=Math.max(status.maxActive,status.active);
      return Promise.resolve();
    };
    HTMLMediaElement.prototype.pause=function(){
      active.delete(this);status.stops++;status.active=active.size;
    };
  });
  const state=()=>page.evaluate(()=>(
    window as typeof window & {__ptpAudioLifecycle:{
      starts:number;stops:number;active:number;maxActive:number;
    }}
  ).__ptpAudioLifecycle);
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await page.getByRole('button',{name:/Play audio/}).first().click();
  await expect(page.getByRole('button',{name:/Playing audio/})).toBeVisible();
  expect((await state()).active).toBe(1);
  // Replay the same item. The previous element must be stopped first.
  await page.getByRole('button',{name:/Playing audio/}).click();
  await expect(page.getByRole('button',{name:/Playing audio/})).toBeVisible();
  expect((await state()).maxActive).toBe(1);
  await page.getByRole('button',{name:'Listen',exact:true}).click();
  expect((await state()).active).toBe(0);
  await page.getByRole('button',{name:/Play audio/}).first().click();
  await expect(page.getByRole('button',{name:/Playing audio/})).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Profile',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Your profile'})).toBeVisible();
  const after=await state();
  expect(after.starts).toBe(3);
  expect(after.active).toBe(0);
  expect(after.maxActive).toBe(1);
  expect(after.stops).toBeGreaterThanOrEqual(3);
  expect(errors).toEqual([]);
});
