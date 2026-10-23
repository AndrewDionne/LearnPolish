import {expect,test} from '@playwright/test';

test('first tourist unit connects real recorded Listen, Speak and Read material',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const units=page.getByRole('group',{name:'Conversation practice'});
  await expect(units).toBeVisible();
  await expect(units.locator('.tourist-unit-card')).toHaveCount(3);
  await expect(page.locator('.lesson-tile')).toHaveCount(26);
  const buttons=units.getByRole('button');
  await expect(buttons).toHaveCount(8);
  await units.getByRole('button',{name:'Greetings and polite replies: Listen'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Greetings and polite replies');
  await expect(page.locator('.unit-practice-head')).toContainText('Listen · 1/3');
  await expect(page.locator('.item-count')).toContainText('/ 2');
  await expect(page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Listen'})).toHaveAttribute('aria-pressed','true');
  // Existing audio and comprehension controls, not a new synthetic question engine.
  await expect(page.locator('.listening-card')).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await units.getByRole('button',{name:'Greetings and polite replies: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/3');
  await expect(page.locator('.item-count')).toContainText('/ 5');
  await expect(page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Speak'})).toHaveAttribute('aria-pressed','true');
  await nav.getByRole('button',{name:'Library'}).click();
  await units.getByRole('button',{name:'Greetings and polite replies: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Read · 3/3');
  await expect(page.locator('.item-count')).toContainText('/ 4');
  await expect(page.getByText('Cześć! Jak się masz?',{exact:true})).toBeVisible();
  await expect(page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Read'})).toHaveAttribute('aria-pressed','true');
});

test('unit progression offers the next source-backed step without a completion grade',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('button',{name:'Introductions and names: Listen'}).click();
  await expect(page.locator('.item-count')).toContainText('/ 2');
  // Skip advances navigation only. The final item needs deliberate response.
  await page.getByRole('button',{name:'Skip to next →'}).click();
  await page.getByRole('group',{name:'Answer the listening question'})
    .getByRole('button',{name:'Their name'}).click();
  await page.getByRole('button',{name:'Continue →'}).click();
  await expect(page.getByRole('heading',{name:'Nicely done!'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Continue with Speak →'})).toBeVisible();
  await page.getByRole('button',{name:'Continue with Speak →'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/3');
  await expect(page.locator('.item-count')).toContainText('/ 1');
  await expect(page.getByText('Jak masz na imię?',{exact:true})).toBeVisible();
});

test('numbers-and-prices pilot is source-only and does not invent a reading scene',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const unit=page.locator('.tourist-unit-card').filter({hasText:'Numbers, prices and payment'});
  await expect(unit.getByRole('button',{name:'Numbers, prices and payment: Read'})).toHaveCount(0);
  await unit.getByRole('button',{name:'Numbers, prices and payment: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/2');
  await expect(page.locator('.item-count')).toContainText('/ 3');
  await expect(page.getByText('Ile to kosztuje?',{exact:true})).toBeVisible();
  await expect(page.locator('.lesson-meter')).toBeVisible();
  await page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'}).getByRole('button',{name:'Library'}).click();
  await page.getByRole('button',{name:/Numbers 1-20/}).click();
  await expect(page.getByRole('combobox',{name:'Practice group'})).toBeVisible();
  await expect(page.locator('.unit-practice-head')).toHaveCount(0);
});

test('320px unit actions stay in view and personal Library remains separate',async({page})=>{
  await page.setViewportSize({width:320,height:740});
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await expect(page.getByRole('button',{name:'Greetings and polite replies: Listen'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
  await page.getByRole('button',{name:'Greetings and polite replies: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
});
