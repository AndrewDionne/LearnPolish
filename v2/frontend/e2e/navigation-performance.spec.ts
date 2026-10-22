import {expect,test} from '@playwright/test';

const routes=[
  {name:'Library',heading:/Lesson library/},
  {name:'Practice',heading:/Keep it fresh/},
  {name:'Expedition',heading:/Your Poland expedition/},
  {name:'Profile',heading:/Your profile/},
  {name:'Home',heading:/Small steps/},
] as const;

test('synthetic route transitions retain keyboard focus, learning data and bounded navigation latency',async({page,isMobile})=>{
  test.setTimeout(90_000);
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  const main=page.locator('#main-content');
  await expect(page.getByRole('heading',{name:/Small steps/})).toBeVisible();
  const before=await page.evaluate(()=>({
    progress:localStorage.getItem('ptp-v2-progress'),
    xp:localStorage.getItem('ptp-v2-expedition'),
    reviews:localStorage.getItem('ptp-v2-review-schedule'),
  }));
  const samples:{route:string;ms:number}[]=[];
  for(let round=0;round<3;round++){
    for(const route of routes){
      const started=Date.now();
      await nav.getByRole('button',{name:route.name,exact:true}).click();
      await expect(page.getByRole('heading',{name:route.heading}).first()).toBeVisible();
      await expect(main).toBeFocused();
      const ms=Date.now()-started;
      samples.push({route:route.name,ms});
      // Generous guard against an unusable/hung screen, not a production SLA.
      expect(ms,'Synthetic route stalled: '+route.name).toBeLessThan(5000);
    }
  }
  const times=samples.map(s=>s.ms).sort((a,b)=>a-b);
  const median=times[Math.floor(times.length/2)];
  const p95=times[Math.ceil(.95*times.length)-1];
  console.log('NAVIGATION_BASELINE '+JSON.stringify({viewport:isMobile?'mobile':'desktop',medianMs:median,p95Ms:p95,maxMs:times.at(-1),samples}));
  const after=await page.evaluate(()=>({
    progress:localStorage.getItem('ptp-v2-progress'),
    xp:localStorage.getItem('ptp-v2-expedition'),
    reviews:localStorage.getItem('ptp-v2-review-schedule'),
  }));
  expect(after).toEqual(before);
  expect(errors).toEqual([]);
});

test('rapid route and lesson-mode changes settle on the latest destination without awarding XP',async({page,isMobile})=>{
  test.setTimeout(90_000);
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library',exact:true}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await expect(page.getByRole('button',{name:'Learn',exact:true})).toHaveAttribute('aria-pressed','true');
  const original=await page.evaluate(()=>({
    xp:localStorage.getItem('ptp-v2-expedition'),
    progress:localStorage.getItem('ptp-v2-progress'),
    reviews:localStorage.getItem('ptp-v2-review-schedule'),
  }));
  // Dispatch multiple navigation intents inside the same browser task to
  // exercise React's batched updates, rather than slowing each action down.
  await page.evaluate(()=>{
    const tabs=['Listen','Speak','Learn','Listen','Speak'];
    for(const name of tabs){
      const button=[...document.querySelectorAll<HTMLButtonElement>('button')]
        .find(b=>b.textContent?.trim()===name && b.hasAttribute('aria-pressed'));
      button?.click();
    }
  });
  await expect(page.getByRole('button',{name:'Speak',exact:true})).toHaveAttribute('aria-pressed','true');
  await page.evaluate(()=>{
    const nav=document.querySelector('nav[aria-label="Main navigation"]')
      ||document.querySelector('nav[aria-label="Mobile navigation"]');
    for(const label of ['Practice','Expedition','Library','Profile']){
      [...(nav?.querySelectorAll('button')||[])].find(b=>b.textContent?.includes(label))?.click();
    }
  });
  await expect(page.getByRole('heading',{name:/Your profile/})).toBeVisible();
  await expect(page.locator('#main-content')).toBeFocused();
  await expect(page.getByRole('heading',{name:/Your Poland expedition/})).toHaveCount(0);
  expect(await page.evaluate(()=>({
    xp:localStorage.getItem('ptp-v2-expedition'),
    progress:localStorage.getItem('ptp-v2-progress'),
    reviews:localStorage.getItem('ptp-v2-review-schedule'),
  }))).toEqual(original);
  expect(errors).toEqual([]);
});
