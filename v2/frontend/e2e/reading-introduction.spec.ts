import {expect,test} from '@playwright/test';

test('C-14 reading preparation teaches every original greeting turn before comprehension',async({page,isMobile})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('button',{name:/Everyday Conversations: Greetings/}).click();
 const intro=page.getByRole('region',{name:'Learn this conversation first'});
 await expect(intro.getByRole('button',{name:'Learn this conversation first'}))
  .toHaveAttribute('aria-expanded','true');
 await expect(intro.locator('.reading-intro-progress')).toHaveText('1 / 6');
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Cześć! Jak się masz?');
 await expect(intro.locator('.reading-intro-english')).toHaveText('Hi! How are you?');
 await intro.getByRole('button',{name:'Hear line'}).click();
 await intro.getByRole('button',{name:'Next line'}).click();
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Dziękuję, mam się dobrze.');
 await expect(intro.locator('.reading-intro-english')).toHaveText('Thank you, I am well.');
 await intro.getByRole('button',{name:'Previous'}).click();
 await expect(intro.locator('.reading-intro-progress')).toHaveText('1 / 6');
 for(let i=0;i<5;i++){
  await intro.getByRole('button',{name:'Next line'}).click();
 }
 await expect(intro.locator('.reading-intro-progress')).toHaveText('6 / 6');
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Przepraszam, nie rozumiem.');
 await intro.getByRole('button',{name:'Start reading'}).click();
 await expect(intro.getByRole('button',{name:'Learn this conversation first'}))
  .toHaveAttribute('aria-expanded','false');
 await expect(page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Read'}))
  .toHaveAttribute('aria-pressed','true');
 await expect(page.locator('.reading-check')).toBeVisible();
 const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
 await nav.getByRole('button',{name:'Library'}).click();
 await expect(page.locator('.lesson-tile')).toHaveCount(26);
});

test('C-14 reading preparation is source-only, optional and usable at 320px without altering tourist Read',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('button',{name:/At the Grocery Store/}).click();
 const intro=page.getByRole('region',{name:'Learn this conversation first'});
 await expect(intro.locator('.reading-intro-progress')).toHaveText('1 / 9');
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Dzień dobry.');
 await intro.getByRole('button',{name:'Next line'}).click();
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Dzień dobry, poproszę kilogram jabłek.');
 await expect(intro.locator('.reading-intro-english')).toHaveText('Good morning, I’d like a kilo of apples, please.');
 await expect(intro.getByRole('button',{name:'Hear line'})).toBeEnabled();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
 await intro.getByRole('button',{name:'Read conversation now'}).click();
 await expect(intro.locator('.reading-intro-polish')).toHaveCount(0);
 await page.getByRole('navigation',{name:'Mobile navigation'}).getByRole('button',{name:'Library'}).click();
 await page.getByRole('button',{name:'Shopping for groceries: Read'}).click();
 await expect(page.getByRole('region',{name:'Learn this conversation first'})).toHaveCount(0);
 await expect(page.locator('.unit-practice-head')).toContainText('Shopping for groceries');
});
