import {expect,test} from '@playwright/test';

test('catalog failure offers an in-app retry that restores learning without resetting progress',async({page,isMobile})=>{
  const pageErrors:string[]=[];
  page.on('pageerror',e=>pageErrors.push(e.message));
  const savedProgress=JSON.stringify({
    'Conversation_1:0':{seen:2,remembered:1,needsPractice:1,lastSeen:'2026-10-20T12:00:00.000Z'}
  });
  await page.addInitScript(progress=>{
    if(!sessionStorage.getItem('ptp-v2-retry-fixture')){
      localStorage.setItem('ptp-v2-progress',progress);
      sessionStorage.setItem('ptp-v2-retry-fixture','seeded');
    }
  },savedProgress);
  let attempts=0;
  await page.route('**/generated/lessons.json',async route=>{
    attempts++;
    if(attempts<=2)await route.fulfill({
      status:503,contentType:'application/json',body:'{"error":"temporary outage"}'
    });
    else await route.continue();
  });
  await page.goto('/');
  const error=page.getByRole('alert');
  await expect(error).toContainText('Lessons could not load');
  await expect(error).toContainText('Your progress and personal lessons remain stored in this browser');
  await expect(error.getByRole('button',{name:'Retry loading lessons'})).toBeVisible();
  expect(attempts).toBe(1);
  await expect(page.getByText('Gathering your lessons…')).toHaveCount(0);
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-progress'))).toBe(savedProgress);

  await error.getByRole('button',{name:'Retry loading lessons'}).click();
  await expect(error).toContainText('Lessons could not load');
  expect(attempts).toBe(2);
  // An unsuccessful retry must not silently spin, erase progress, or hide retry.
  await expect(error.getByRole('button',{name:'Retry loading lessons'})).toBeEnabled();
  await expect(page.getByRole('heading',{name:/Small steps/})).toHaveCount(0);

  await error.getByRole('button',{name:'Retry loading lessons'}).click();
  await expect(page.getByRole('heading',{name:/Small steps/})).toBeVisible();
  await expect(error).toHaveCount(0);
  expect(attempts).toBe(3);
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-progress'))).toBe(savedProgress);
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library',exact:true}).click();
  await expect(page.getByRole('searchbox',{name:'Search lessons'})).toBeVisible();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await expect(page.getByText('Dzień dobry',{exact:true})).toBeVisible();
  expect(pageErrors).toEqual([]);
});
