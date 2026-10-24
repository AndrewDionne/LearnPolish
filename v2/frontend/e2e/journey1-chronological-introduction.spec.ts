import {expect,test} from '@playwright/test';

test('C-16B first words introduce exact complete recordings and meanings before Listen answers',async({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('region',{name:'Guided Polish foundations'})
  .getByRole('group',{name:'First expressions practice'}).getByRole('button',{name:/Yes and no/}).click();
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Listen'}).click();
 const intro=page.getByRole('region',{name:'Learn these expressions first'});
 await expect(intro.getByRole('button',{name:'Learn these expressions first'})).toHaveAttribute('aria-expanded','true');
 await expect(intro.locator('.reading-intro-progress')).toHaveText('1 / 2');
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Tak');
 await expect(intro.locator('.reading-intro-english')).toHaveText('Yes');
 await intro.getByRole('button',{name:'Hear line'}).click();
 await intro.getByRole('button',{name:'Next line'}).click();
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Nie');
 await expect(intro.locator('.reading-intro-english')).toHaveText('No');
 await intro.getByRole('button',{name:'Start listening'}).click();
 await expect(intro.getByRole('button',{name:'Learn these expressions first'})).toHaveAttribute('aria-expanded','false');
 await expect(page.getByRole('heading',{name:'What did you hear?'})).toBeVisible();
 const nav=page.getByRole('navigation',{name:'Main navigation'});
 await nav.getByRole('button',{name:'Library'}).click();
 await expect(page.locator('.lesson-tile')).toHaveCount(26);
});

test('C-16B 320px shopping sentence teaching explains grammar and keeps source pronunciation',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 await guide.getByRole('group',{name:'Short sentence practice'})
  .getByRole('button',{name:/Questions in a shop/}).click();
 await expect(page.locator('.polish-text')).toHaveText('Ile to kosztuje?');
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Listen'}).click();
 const intro=page.getByRole('region',{name:'Learn these expressions first'});
 await expect(intro.locator('.reading-intro-progress')).toHaveText('1 / 5');
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Ile to kosztuje?');
 await expect(intro.locator('.reading-intro-english')).toHaveText('How much does this cost?');
 await expect(intro.locator('.reading-intro-cue')).toContainText('costs');
 await intro.getByRole('button',{name:'Hear line'}).click();
 await intro.getByRole('button',{name:'Next line'}).click();
 await expect(intro.locator('.reading-intro-cue')).toContainText('razem');
 await intro.getByRole('button',{name:'Next line'}).click();
 await expect(intro.locator('.reading-intro-polish')).toHaveText('Czy mogę zapłacić kartą?');
 await expect(intro.locator('.reading-intro-cue')).toContainText('by card');
 await intro.getByRole('button',{name:'Listen now'}).click();
 await expect(intro.locator('.reading-intro-cue')).toHaveCount(0);
 await expect(page.getByRole('heading',{name:'What did you hear?'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
});

test('C-16B intro is a guided route aid, not an imposed overlay on the original 26 Library lessons',async({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('button',{name:/Basic conversation: Greetings/}).click();
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Listen'}).click();
 await expect(page.getByRole('region',{name:'Learn these expressions first'})).toHaveCount(0);
 await expect(page.getByRole('heading',{name:'What did you hear?'})).toBeVisible();
});
