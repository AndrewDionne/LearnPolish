import {expect,test} from '@playwright/test';

test('C-05: three beginner sessions use original recordings, real Learn/Listen/Speak, no new lesson tiles',async({page,isMobile})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 const starters=guide.getByRole('group',{name:'First expressions practice'});
 await expect(starters.getByRole('button')).toHaveCount(3);
 await starters.getByRole('button',{name:/Hello and goodbye/}).click();
 await expect(page.locator('.unit-practice-head')).toContainText('Hello and goodbye');
 await expect(page.locator('.item-count')).toContainText('1');
 await expect(page.locator('.item-count')).toContainText('3');
 await expect(page.locator('.polish-text')).toHaveText('Dzień dobry');
 await expect(page.getByRole('combobox',{name:'Practice group'})).toHaveCount(0);
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Listen'}).click();
 await expect(page.locator('.unit-practice-head')).toContainText('Hello and goodbye');
 await expect(page.getByRole('heading',{name:'What did you hear?'})).toBeVisible();
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Speak'}).click();
 await expect(page.locator('.unit-practice-head')).toContainText('1/3');
 const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
 await nav.getByRole('button',{name:'Library'}).click();
 const again=page.getByRole('region',{name:'Guided Polish foundations'});
 await again.getByRole('group',{name:'First expressions practice'})
   .getByRole('button',{name:/Yes and no/}).click();
 await expect(page.locator('.unit-practice-head')).toContainText('Yes and no');
 await expect(page.locator('.unit-practice-head')).toContainText('1/2');
 await expect(page.locator('.polish-text')).toHaveText('Tak');
 await nav.getByRole('button',{name:'Library'}).click();
 await expect(page.locator('.lesson-tile')).toHaveCount(26);
});

test('C-05: original expressions remain accessible as complete legacy lesson after starter session',async({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 await guide.getByRole('group',{name:'First expressions practice'})
   .getByRole('button',{name:/Polite essentials/}).click();
 await expect(page.locator('.polish-text')).toHaveText('Proszę');
 await expect(page.locator('.unit-practice-head')).toContainText('1/3');
 await page.getByRole('button',{name:'Back to library'}).click();
 const full=page.getByRole('region',{name:'Guided Polish foundations'});
 await full.locator('.foundation-guide-step').first().click();
 await expect(page.locator('.learning-head h1')).toContainText('Greetings');
 await expect(page.locator('.unit-practice-head')).toHaveCount(0);
 await expect(page.locator('.item-count')).not.toContainText('/ 3');
});
