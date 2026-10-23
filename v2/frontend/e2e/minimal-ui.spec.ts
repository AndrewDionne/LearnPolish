import {expect,test} from '@playwright/test';

test('minimal chrome uses meaningful artwork while learning controls remain immediately available',async({page})=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:/Small steps/})).toBeVisible();
  await expect(page.getByText('Local preview')).toHaveCount(0);
  await expect(page.getByText('LEARN WITH CONFIDENCE')).toHaveCount(0);
  await expect(page.getByText('V2 preview')).toHaveCount(0);
  await expect(page.locator('.welcome-art .type-card')).toHaveCount(3);
  await expect(page.locator('.sidebar .nav-icon svg')).toHaveCount(5);
  await expect(page.locator('.mobile-nav svg')).toHaveCount(5);
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();

  await expect(page.locator('.learning-head h1')).toHaveText('Greetings and Introductions');
  await expect(page.locator('.learning-head p')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Reveal meaning'})).toBeVisible();
  await page.getByRole('button',{name:'Listen',exact:true}).click();
  await expect(page.locator('.listening-prompt')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Play audio'})).toBeVisible();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await expect(page.getByRole('button',{name:'Start recording'})).toBeVisible();
  await expect(page.locator('.speak-score-explanation')).toHaveCount(0);
  await expect(page.locator('.speak-latency')).toHaveCount(0);
  await expect(page.locator('.speak-word-score')).toHaveCount(0);
});

test('mobile navigation uses accessible labelled actions, not emoji glyph controls',async({page,isMobile})=>{
  test.skip(!isMobile,'mobile viewport only');
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:'Mobile navigation'});
  for(const label of ['Home','Library','Practice','Expedition','Profile']){
    await expect(nav.getByRole('button',{name:label,exact:true})).toBeVisible();
  }
  await nav.getByRole('button',{name:'Library'}).click();
  await expect(page.getByRole('heading',{name:/Lesson library/})).toBeVisible();
  await expect(nav.getByRole('button',{name:'Library'})).toHaveAttribute('aria-current','page');
});
