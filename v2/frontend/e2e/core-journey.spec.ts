import {expect,test} from '@playwright/test';

test('Library shows source-backed path without exposing any tier classification',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await expect(page.getByRole('heading',{name:'Your path'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Explore more'})).toBeVisible();
  await expect(page.locator('.lesson-tile')).toHaveCount(26);
  await expect(page.locator('.journey-marker')).toHaveCount(21);
  await expect(page.getByRole('group',{name:'Browse learning stage'})).toHaveCount(0);
  for(const label of ['Fundamentals','Basic','Learning']){
    await expect(page.getByRole('heading',{name:label,exact:true})).toHaveCount(0);
  }

  const first=page.locator('.curriculum-section').first().locator('.lesson-tile').first();
  await expect(first).toContainText('Greetings and Introductions');
  await expect(first.locator('.journey-marker')).toHaveClass(/journey-1/);
  const marker=first.locator('.journey-marker');
  await expect(marker).toHaveAttribute('aria-hidden','true');
  await expect(marker).not.toHaveAttribute('title',/.+/);
  await expect(marker).not.toHaveAttribute('aria-label',/.+/);
  await expect(marker.locator('svg')).toHaveAttribute('focusable','false');
  await expect(page.getByRole('button',{name:/Countries in Polish/}).locator('.journey-marker')).toHaveCount(0);
  await expect(page.getByRole('button',{name:/Świętokrzyska Pronunciation Lab/}).locator('.journey-marker')).toHaveCount(0);
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Practice',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Practice.'})).toBeVisible();
});

test('personal content remains separate, writable and without a core marker',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('button',{name:/Create lesson/}).click();
  await page.getByRole('textbox',{name:'Lesson name'}).fill('My travel notes');
  await page.getByRole('textbox',{name:'Polish text'}).fill('Dzień dobry');
  await page.getByRole('textbox',{name:'English meaning'}).fill('Good day');
  await page.getByRole('button',{name:'Create lesson →'}).click();
  await page.getByRole('button',{name:'← Back to library'}).click();
  const personal=page.getByRole('region',{name:'Your lessons'});
  await expect(personal).toContainText('My travel notes');
  await expect(personal.locator('.journey-marker')).toHaveCount(0);
  await expect(page.locator('.journey-marker')).toHaveCount(21);
});

test('320px Library remains navigable without icons creating overflow',async({page})=>{
  await page.setViewportSize({width:320,height:720});
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await expect(page.locator('.journey-marker').first()).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Shopping: Useful Questions');
  await expect(page.locator('.lesson-tile')).toHaveCount(1);
  await expect(page.locator('.journey-marker')).toHaveCount(1);
});
