import {expect,test} from '@playwright/test';

test('foundations-first guided practice opens authentic full source lessons and preserves tourist entry',async({page,isMobile})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 await expect(guide).toBeVisible();
 await expect(guide.getByRole('heading',{name:'Start with the essentials'})).toBeVisible();
 await expect(guide.locator('.foundation-guide-step')).toHaveCount(4);
 await guide.getByRole('button',{name:'See all 20 steps'}).click();
 await expect(guide.locator('.foundation-guide-step')).toHaveCount(20);
 await expect(guide.locator('.foundation-guide-step').first()).toContainText('Greetings and everyday words');
 await expect(guide.locator('.foundation-guide-step').nth(6)).toContainText('Numbers 1–20');
 await expect(guide.locator('.foundation-guide-step').nth(16)).toContainText('Use a greeting');
 await guide.getByRole('button',{name:/Numbers 1–20/}).click();
 await expect(page.locator('.learning-head h1')).toHaveText('Numbers 1-20');
 await expect(page.getByRole('combobox',{name:'Practice group'})).toBeVisible();
 await expect(page.getByRole('combobox',{name:'Practice group'}).locator('option')).toHaveCount(2);
 const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
 await nav.getByRole('button',{name:'Library'}).click();
 const again=page.getByRole('region',{name:'Guided Polish foundations'});
 await again.getByRole('button',{name:'See all 20 steps'}).click();
 await again.locator('.foundation-guide-step').nth(16).click();
 await expect(page.locator('.unit-practice-head')).toContainText('Greetings and polite replies');
 await expect(page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Listen'}))
   .toHaveAttribute('aria-pressed','true');
 await nav.getByRole('button',{name:'Library'}).click();
 await expect(page.getByRole('group',{name:'Conversation practice'}).locator('.tourist-unit-card')).toHaveCount(8);
 await expect(page.locator('.lesson-tile')).toHaveCount(26);
});

test('foundations guide fits 320px, stays source-only and does not expose three-journey tier labels',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 await guide.getByRole('button',{name:'See all 20 steps'}).click();
 await expect(guide.locator('.foundation-guide-step')).toHaveCount(20);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
 for(const label of ['Beginning','Middle','End','Visiting tourists','Extended stay','Living in Poland']){
  await expect(guide.getByText(label,{exact:true})).toHaveCount(0);
 }
 await guide.getByRole('button',{name:'Show less'}).click();
 await expect(guide.locator('.foundation-guide-step')).toHaveCount(4);
 await page.getByRole('searchbox',{name:'Search lessons'}).fill('Museum');
 await expect(guide).toHaveCount(0);
 await expect(page.locator('.lesson-tile')).toHaveCount(1);
});
