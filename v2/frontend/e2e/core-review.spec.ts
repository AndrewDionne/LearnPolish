import {expect,test} from '@playwright/test';

const seed=async(page:import('@playwright/test').Page)=>{
  await page.goto('/');
  await page.evaluate(()=>{
    const due='2026-10-22T08:00:00.000Z';
    const record=()=>({streak:0,attempts:1,lastReviewedAt:due,dueAt:due});
    localStorage.setItem('ptp-v2-review-schedule',JSON.stringify({
      'Conversation_1:0':record(), 'numbers_1-20:0':record(),
      'personal_review:0':record(), 'Countries_of_the_World:0':record()
    }));
    localStorage.setItem('ptp-v2-personal-lessons',JSON.stringify([{
      schemaVersion:1,id:'personal_review',source:'personal',kind:'vocabulary',
      title:'My extra vocabulary',items:[{id:'personal_review:0',polish:'Tak',english:'Yes'}]
    }]));
    localStorage.setItem('ptp-v2-core-continue','Conversation_-_shopping');
  });
  await page.reload();
};

test('Home opens one voluntary core review run, moving across existing due source lessons without looping misses',async({page,isMobile})=>{
  await seed(page);
  await expect(page.locator('.review-home')).toContainText('2 due on your path');
  await expect(page.locator('.review-home')).toContainText('2 in other lessons');
  await page.locator('.review-home').click();
  await expect(page.locator('.learning-head h1')).toHaveText('Greetings and Introductions');
  await expect(page.getByText('Dzień dobry',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:/Reveal meaning/}).click();
  await page.getByRole('button',{name:'Needs practice'}).click();
  await expect(page.getByRole('heading',{name:'Nicely done!'})).toBeVisible();
  await page.getByRole('button',{name:'Continue scheduled review →'}).click();
  await expect(page.locator('.learning-head h1')).toHaveText('Numbers 1-20');
  await expect(page.getByText('Jeden',{exact:true})).toBeVisible();
  await expect(page.getByRole('combobox',{name:'Practice group'})).toHaveCount(0);
  await page.getByRole('button',{name:/Reveal meaning/}).click();
  await page.getByRole('button',{name:/Got it/}).click();
  await expect(page.getByRole('button',{name:'Continue scheduled review →'})).toHaveCount(0);
  await page.getByRole('button',{name:'Back to practice →'}).click();
  await expect(page.getByRole('heading',{name:'Practice.'})).toBeVisible();
  // The unsuccessful first recall is still due, but has not looped inside this run.
  await expect(page.getByRole('region',{name:'Core course scheduled review'})).toContainText('1 due now');
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue')))
    .toBe('Conversation_-_shopping');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Home'}).click();
  await expect(page.locator('.core-resume-card')).toContainText('Shopping: Useful Questions');
});

test('Practice keeps personal and supplementary due items outside the core one-tap run',async({page,isMobile})=>{
  await seed(page);
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Practice'}).click();
  const core=page.getByRole('region',{name:'Core course scheduled review'});
  const personal=page.getByRole('region',{name:'Personal lesson scheduled review'});
  const extras=page.getByRole('region',{name:'Other lesson scheduled review'});
  await expect(core).toContainText('2 due now');
  await expect(personal).toContainText('My extra vocabulary');
  await expect(extras).toContainText('Countries in Polish');
  await core.getByRole('button',{name:/Review 2 expressions/}).click();
  await expect(page.locator('.learning-head h1')).toHaveText('Greetings and Introductions');
  await nav.getByRole('button',{name:'Practice'}).click();
  await personal.getByRole('button',{name:/My extra vocabulary/}).click();
  await expect(page.locator('.learning-head h1')).toHaveText('My extra vocabulary');
  await expect(page.getByRole('button',{name:'Continue scheduled review →'})).toHaveCount(0);
  await nav.getByRole('button',{name:'Practice'}).click();
  await extras.getByRole('button',{name:/Countries in Polish/}).click();
  await expect(page.locator('.learning-head h1')).toHaveText('Countries in Polish');
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue')))
    .toBe('Conversation_-_shopping');
});

test('At 320px the due lanes stay usable and the course review remains opt-in',async({page})=>{
  await page.setViewportSize({width:320,height:720});
  await seed(page);
  const nav=page.getByRole('navigation',{name:'Mobile navigation'});
  await nav.getByRole('button',{name:'Practice'}).click();
  await expect(page.getByRole('region',{name:'Core course scheduled review'})).toBeVisible();
  await expect(page.getByRole('region',{name:'Personal lesson scheduled review'})).toBeVisible();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth);
  expect(overflow).toBeLessThanOrEqual(322);
  const target=page.getByRole('region',{name:'Core course scheduled review'}).getByRole('button',{name:/Review 2 expressions/});
  await expect(target).toBeVisible();
  expect(await target.evaluate(node=>node.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
});
