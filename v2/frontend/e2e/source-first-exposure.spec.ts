import {expect,test} from '@playwright/test';

test('C-16C full original shopping Library begins Listen with 25 whole recorded expressions and source meanings',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('button',{name:'Shopping: Useful Questions'}).click();
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Listen'}).click();
 const intro=page.getByRole('region',{name:'Learn these expressions first'});
 await expect(intro.locator('.reading-intro-progress')).toHaveText('1 / 25');
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Ile to kosztuje?');
 await expect(intro.locator('.reading-intro-english')).toHaveText('How much does this cost?');
 await expect(intro.locator('.reading-intro-cue')).toContainText('Ile asks how much');
 await intro.getByRole('button',{name:'Hear line'}).click();
 await intro.getByRole('button',{name:'Next line'}).click();
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Ile to razem?');
 await intro.getByRole('button',{name:'Listen now'}).click();
 await expect(intro.locator('.reading-intro-cue')).toHaveCount(0);
 await expect(page.getByRole('heading',{name:'What did you hear?'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
});

test('C-16C T01 tourist Listen explains the original greeting before graded question',async({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('button',{name:'Greetings and polite replies: Listen'}).click();
 const intro=page.getByRole('region',{name:'Learn this scene first'});
 await expect(intro.locator('.reading-intro-progress')).toHaveText('1 / 2');
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Cześć! Jak się masz?');
 await expect(intro.locator('.reading-intro-cue')).toContainText('informal');
 await intro.getByRole('button',{name:'Next line'}).click();
 await expect(intro.locator('.reading-intro-english')).toHaveText('Thank you, I am well.');
 await intro.getByRole('button',{name:'Start listening'}).click();
 await expect(page.getByRole('group',{name:'Answer the listening question'})).toBeVisible();
});

test('C-16C T03 numbers 1–10 are introduced from full original recorded words, never fragmented audio',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('button',{name:'Numbers, prices and payment: Listen'}).click();
 const intro=page.getByRole('region',{name:'Learn this scene first'});
 await expect(intro.locator('.reading-intro-progress')).toHaveText('1 / 10');
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Jeden');
 await expect(intro.locator('.reading-intro-english')).toHaveText('One');
 await intro.getByRole('button',{name:'Next line'}).click();
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Dwa');
 await intro.getByRole('button',{name:'Listen now'}).click();
 await expect(page.getByRole('heading',{name:'What did you hear?'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
 await expect(page.getByRole('button',{name:/Play syllable/})).toHaveCount(0);
});

test('C-16C original Library Speak continues to use compact single whole-word audio and English, no repeated primer',async({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('button',{name:'Ordering at a Restaurant'}).click();
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Speak'}).click();
 await expect(page.locator('.speak-meaning')).toBeVisible();
 await expect(page.getByRole('button',{name:'Hear example'})).toBeEnabled();
 await expect(page.getByRole('region',{name:'Learn these expressions first'})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Start recording'})).toBeVisible();
});
