import {expect,test} from '@playwright/test';

test('C-06 first-word sequence opens 32 existing full recorded words through real modes',async({page,isMobile})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 const toggle=guide.getByRole('button',{name:/Keep building your everyday vocabulary/});
 await expect(toggle).toHaveAttribute('aria-expanded','false');
 await toggle.click();
 await expect(toggle).toHaveAttribute('aria-expanded','true');
 const more=guide.getByRole('group',{name:'More recorded beginner practice'});
 await expect(more.getByRole('button')).toHaveCount(6);
 await more.getByRole('button',{name:/Street and place words/}).click();
 await expect(page.locator('.unit-practice-head')).toContainText('Street and place words');
 await expect(page.locator('.unit-practice-head')).toContainText('1/6');
 await expect(page.locator('.polish-text')).toHaveText('ulica');
 await expect(page.getByRole('combobox',{name:'Practice group'})).toHaveCount(0);
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Listen'}).click();
 await expect(page.locator('.unit-practice-head')).toContainText('Street and place words');
 await expect(page.getByRole('heading',{name:'What did you hear?'})).toBeVisible();
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Speak'}).click();
 await expect(page.locator('.unit-practice-head')).toContainText('1/6');
 const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
 await nav.getByRole('button',{name:'Library'}).click();
 await expect(page.locator('.lesson-tile')).toHaveCount(26);
 const again=page.getByRole('region',{name:'Guided Polish foundations'});
 await again.getByRole('button',{name:/Keep building your everyday vocabulary/}).click();
 await again.getByRole('group',{name:'More recorded beginner practice'})
   .getByRole('button',{name:/Simple food requests/}).click();
 await expect(page.locator('.polish-text')).toHaveText('Poproszę wodę');
 await expect(page.locator('.unit-practice-head')).toContainText('1/5');
});

test('C-06 source-only practice sequence advances to next real group without fake new lesson',async({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 await guide.getByRole('button',{name:/Keep building your everyday vocabulary/}).click();
 await guide.getByRole('group',{name:'More recorded beginner practice'})
   .getByRole('button',{name:/More everyday replies/}).click();
 await expect(page.locator('.polish-text')).toHaveText('Może');
 for(let i=0;i<5;i++){
   await page.getByRole('button',{name:/Reveal meaning/}).click();
   await page.getByRole('button',{name:/Got it/}).click();
 }
 await expect(page.getByRole('heading',{name:'Nicely done!'})).toBeVisible();
 await page.getByRole('button',{name:/Next: Simple food requests/}).click();
 await expect(page.locator('.unit-practice-head')).toContainText('Simple food requests');
 await expect(page.locator('.polish-text')).toHaveText('Poproszę wodę');
 await expect(page.locator('.unit-practice-head')).toContainText('1/5');
});

test('C-06 first-word disclosure fits a narrow mobile screen without staging labels',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 await guide.getByRole('button',{name:/Keep building your everyday vocabulary/}).click();
 await expect(guide.getByRole('group',{name:'More recorded beginner practice'}).getByRole('button')).toHaveCount(6);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
 await expect(guide.getByText('Beginning',{exact:true})).toHaveCount(0);
 await expect(guide.getByText('Extended stay',{exact:true})).toHaveCount(0);
});
