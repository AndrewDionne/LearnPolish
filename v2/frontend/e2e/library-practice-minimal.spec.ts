import {expect,test} from '@playwright/test';

test('Library prioritizes lessons while occasional author tools stay discoverable',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await expect(page.getByRole('heading',{name:/Lesson library/})).toBeVisible();
  await expect(page.locator('.page-title p')).toHaveCount(0);
  await expect(page.locator('.library-summary')).toHaveCount(0);
  await expect(page.locator('.curriculum-stage-heading p')).toHaveCount(0);
  await expect(page.locator('.curriculum-stage-heading > span')).toHaveCount(0);
  await expect(page.getByRole('button',{name:/Create lesson/})).toBeVisible();
  await expect(page.locator('input[aria-label="Import lesson JSON"]')).toHaveCount(1);
  await page.getByRole('group',{name:'Browse learning stage'})
    .getByRole('button',{name:'Fundamentals'}).click();
  await expect(page.locator('.lesson-tile')).toHaveCount(12);
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await expect(page.getByRole('button',{name:/Greetings and Introductions/})).toBeVisible();
});

test('Practice leads with due reviews and studied lessons, with detailed statistics in Profile',async({page,isMobile})=>{
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Practice'}).click();
  await expect(page.getByRole('heading',{name:'Practice.'})).toBeVisible();
  await expect(page.getByText('0 due now')).toBeVisible();
  await expect(page.locator('.stats-row')).toHaveCount(0);
  await expect(page.getByText('Self-rated recall')).toHaveCount(0);
  await nav.getByRole('button',{name:'Profile'}).click();
  await expect(page.getByText('Self-rated recall')).toBeVisible();
  await nav.getByRole('button',{name:'Library'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await page.getByRole('button',{name:'Reveal meaning'}).click();
  await page.getByRole('button',{name:/Got it/}).click();
  await nav.getByRole('button',{name:'Practice'}).click();
  await expect(page.locator('.lesson-grid .lesson-tile')).toHaveCount(1);
  await expect(page.getByRole('heading',{name:'Continue learning'})).toBeVisible();
  await page.locator('.lesson-grid .lesson-tile').first().click();
  await expect(page.locator('.learning-head h1')).toHaveText('Greetings and Introductions');
});
