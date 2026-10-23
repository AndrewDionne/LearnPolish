import {expect,test} from '@playwright/test';

test('first tourist unit connects real recorded Listen, Speak and Read material',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const units=page.getByRole('group',{name:'Conversation practice'});
  await expect(units).toBeVisible();
  await expect(units.locator('.tourist-unit-card')).toHaveCount(5);
  await expect(page.locator('.lesson-tile')).toHaveCount(26);
  const buttons=units.getByRole('button');
  await expect(buttons).toHaveCount(13);
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

test('T04 source-only restaurant practice offers Listen and Speak without fabricated waiter dialogue',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const unit=page.locator('.tourist-unit-card').filter({hasText:'Ordering food and drinks'});
  await expect(unit).toBeVisible();
  await expect(unit.getByRole('button',{name:'Ordering food and drinks: Read'})).toHaveCount(0);
  await unit.getByRole('button',{name:'Ordering food and drinks: Listen'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Listen · 1/2');
  await expect(page.locator('.item-count')).toContainText('/ 9');
  await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
  await page.getByRole('group',{name:'Choose the meaning'}).getByRole('button',{name:'A table for one, please'}).click();
  await expect(page.getByText('Poproszę stolik dla jednej osoby',{exact:true})).toBeVisible();
  await page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'}).getByRole('button',{name:'Library'}).click();
  await unit.getByRole('button',{name:'Ordering food and drinks: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/2');
  await expect(page.locator('.item-count')).toContainText('/ 8');
  await expect(page.getByText('Poproszę menu',{exact:true})).toBeVisible();
});

test('T05 grocery story uses original listening and reading, with independent shopping Speak phrases',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const unit=page.locator('.tourist-unit-card').filter({hasText:'Shopping for groceries'});
  await unit.getByRole('button',{name:'Shopping for groceries: Listen'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Listen · 1/3');
  await expect(page.locator('.item-count')).toContainText('/ 6');
  await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
  await page.getByRole('button',{name:'Reveal transcript & translation'}).click();
  await expect(page.getByText('Dzień dobry.',{exact:true})).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await unit.getByRole('button',{name:'Shopping for groceries: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/3');
  await expect(page.locator('.item-count')).toContainText('/ 6');
  await expect(page.getByText('Ile to kosztuje?',{exact:true})).toBeVisible();
  await nav.getByRole('button',{name:'Library'}).click();
  await unit.getByRole('button',{name:'Shopping for groceries: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Read · 3/3');
  await expect(page.getByText('Dzień dobry.',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
  await nav.getByRole('button',{name:'Library'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Conversation_-_shopping');
  await page.getByRole('button',{name:/Shopping: Useful Questions/}).click();
  await expect(page.locator('.unit-practice-head')).toHaveCount(0);
});

test('opening cross-journey T05 source excerpt preserves explicit Home course position',async({page,isMobile})=>{
  await page.goto('/');
  await page.evaluate(()=>localStorage.setItem('ptp-v2-core-continue','Conversation_1'));
  await page.reload();
  await page.getByRole('button',{name:'Continue course'}).isVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await page.getByRole('button',{name:'Shopping for groceries: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Read · 3/3');
  await nav.getByRole('button',{name:'Home'}).click();
  await expect(page.locator('.core-resume-card')).toContainText('Greetings and Introductions');
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue'))).toBe('Conversation_1');
  // The source file may still be independently opened as recent practice.
  await expect(page.locator('.recent-resume-card')).toContainText('Shopping at the Grocery Store');
});
