import {expect,test} from '@playwright/test';

test('Listen returns a short immediate result and a single next action',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Everyday Conversations: Greetings');
  await page.getByRole('button',{name:/Everyday Conversations: Greetings/}).click();
  await page.getByRole('button',{name:'Listen',exact:true}).click();
  await expect(page.locator('.listening-answer')).toHaveCount(0);
  await page.getByRole('group',{name:/Choose the meaning|Answer the listening question/})
    .getByRole('button').first().click();
  const result=page.locator('.listening-answer');
  await expect(result).toBeVisible();
  await expect(result.getByRole('status')).toHaveText(/^(Correct!|Not quite)$/);
  await expect(result.locator('.listen-transcript')).toContainText('Cześć! Jak się masz?');
  await expect(result.locator('.listen-english')).not.toBeEmpty();
  await expect(result.locator('.comprehension-feedback')).toHaveCount(0);
  await expect(result.locator('.card-label')).toHaveCount(0);
  await expect(result.getByRole('button',{name:'Continue →'})).toBeVisible();
  await result.getByRole('button',{name:'Continue →'}).click();
  await expect(page.locator('.listening-answer')).toHaveCount(0);
  await expect(page.locator('.item-count')).toContainText('2');
});

test('Read shows an objective short result without advice and advances on Continue',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Everyday Conversations: Greetings');
  await page.getByRole('button',{name:/Everyday Conversations: Greetings/}).click();
  for(let i=0;i<5;i++)await page.getByRole('button',{name:/Skip to next/}).click();
  await expect(page.locator('.reading-check-options button').first()).toBeVisible();
  await page.locator('.reading-check-options button').first().click();
  await expect(page.locator('.reading-check-result')).toHaveText(/^(Correct!|Not quite)$/);
  await expect(page.locator('.reading-check-result p')).toHaveCount(1);
  await expect(page.locator('.translation p')).toHaveCount(1);
  await expect(page.getByRole('button',{name:'Continue →'})).toBeVisible();
  await page.getByRole('button',{name:'Continue →'}).click();
  await expect(page.getByRole('heading',{name:'Nicely done!'})).toBeVisible();
  await expect(page.locator('.mode-handoff>strong')).toHaveCount(0);
});

test('Reviewable mode actions retain direct previous/skip with no duplicated stats',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  const nav=page.locator('.lesson-footer');
  await expect(nav.locator('span')).toHaveCount(0);
  await expect(nav.getByRole('button',{name:'Previous'})).toBeDisabled();
  await expect(nav.getByRole('button',{name:/Skip to next/})).toBeVisible();
  await page.getByRole('button',{name:/Reveal meaning/}).click();
  await expect(page.getByRole('button',{name:/Needs practice/})).toBeVisible();
  await expect(page.getByRole('button',{name:/Got it/})).toBeVisible();
  await page.getByRole('button',{name:/Got it/}).click();
  await expect(page.locator('.item-count')).toContainText('2');
});
