import {expect,test} from '@playwright/test';

test('tourist Resume returns to the first untried source item after skipping, navigating away and reload',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const card=page.locator('.tourist-unit-card').filter({hasText:'Introductions and names'});
  await card.getByRole('button',{name:'Introductions and names: Listen'}).click();
  await expect(page.locator('.item-count')).toContainText('1');
  await page.getByRole('button',{name:'Skip to next →'}).click();
  await page.getByRole('group',{name:'Answer the listening question'})
    .getByRole('button',{name:'Their name'}).click();
  await page.getByRole('button',{name:'Continue →'}).click();
  await expect(page.getByRole('heading',{name:'Nicely done!'})).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await expect(card.locator('.tourist-unit-activity')).toHaveText('1 / 5 tried');
  await expect(card.getByRole('button',{name:'Resume Introductions and names'})).toBeVisible();
  const evidence=await page.evaluate(()=>JSON.parse(localStorage.getItem('ptp-v2-tourist-activity')||'{}'));
  expect(evidence.units.T02.tried).toEqual({listen:['Basic_01R:3']});
  expect(evidence.units.T02.cursor).toEqual({mode:'listen',itemId:'Basic_01R:2'});
  await page.reload();
  await card.getByRole('button',{name:'Resume Introductions and names'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Listen · 1/3');
  await expect(page.locator('.item-count')).toContainText('1');
  await expect(page.locator('.item-count')).toContainText('/ 2');
  await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
  await nav.getByRole('button',{name:'Library'}).click();
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue'))).toBeNull();
  await expect(card.locator('.tourist-unit-activity')).toHaveText('1 / 5 tried');
});

test('Speak Next without a real microphone take is navigation, not unit practice or mastery',async({page,isMobile})=>{
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  const card=page.locator('.tourist-unit-card').filter({hasText:'Numbers, prices and payment'});
  await card.getByRole('button',{name:'Numbers, prices and payment: Speak'}).click();
  await expect(page.getByText('Ile to kosztuje?',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Next',exact:true}).click();
  await expect(page.getByText('Ile to razem?',{exact:true})).toBeVisible();
  await nav.getByRole('button',{name:'Library'}).click();
  await expect(card.locator('.tourist-unit-activity')).toHaveText('0 / 13 tried');
  await page.reload();
  await card.getByRole('button',{name:'Resume Numbers, prices and payment'}).click();
  await expect(page.getByText('Ile to razem?',{exact:true})).toBeVisible();
  await expect(page.locator('.item-count')).toContainText('2');
  const evidence=await page.evaluate(()=>JSON.parse(localStorage.getItem('ptp-v2-tourist-activity')||'{}'));
  expect(evidence.units.T03.tried).toEqual({});
  expect(evidence.units.T03.cursor).toEqual({mode:'speak',itemId:'Conversation_-_shopping:1'});
});

test('source-wide Library history does not fabricate tourist participation, even at 320px',async({page,isMobile})=>{
  await page.setViewportSize({width:320,height:740});
  await page.goto('/');
  await page.evaluate(()=>{
    localStorage.setItem('ptp-v2-progress',JSON.stringify({
      'listen:Basic_01R:2':{seen:4,remembered:4,needsPractice:0,lastSeen:'2026-10-22T11:00:00Z'},
      'read:Basic_01R:3':{seen:3,remembered:3,needsPractice:0,lastSeen:'2026-10-22T11:00:00Z'}
    }));
  });
  await page.reload();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  const card=page.locator('.tourist-unit-card').filter({hasText:'Introductions and names'});
  await expect(card.locator('.tourist-unit-activity')).toHaveCount(0);
  await expect(card.getByRole('button',{name:'Resume Introductions and names'})).toHaveCount(0);
  await card.getByRole('button',{name:'Introductions and names: Read'}).click();
  await nav.getByRole('button',{name:'Library'}).click();
  await expect(card.locator('.tourist-unit-activity')).toHaveText('0 / 5 tried');
  await expect(card.getByRole('button',{name:'Resume Introductions and names'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
  expect(await card.getByRole('button',{name:'Resume Introductions and names'})
    .evaluate(node=>node.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
});
