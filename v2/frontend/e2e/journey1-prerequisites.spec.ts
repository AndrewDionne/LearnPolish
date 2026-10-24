import {expect,test} from '@playwright/test';

test('C-13: beginner grammar examples now precede their corresponding shopping/location applications',async({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 const section=guide.locator('.foundation-path-stage').nth(2);
 const patterns=section.getByRole('region',{name:'Recorded first sentence patterns'});
 const applications=section.getByRole('group',{name:'Short sentence practice'});
 await expect(patterns.getByRole('button',{name:'Build your first sentences'})).toBeVisible();
 await expect(applications.getByRole('button')).toHaveCount(3);
 const patternY=await patterns.boundingBox(),applicationY=await applications.boundingBox();
 expect(patternY).not.toBeNull();expect(applicationY).not.toBeNull();
 expect(patternY!.y).toBeLessThan(applicationY!.y);
 await patterns.getByRole('button',{name:'Build your first sentences'}).click();
 const list=patterns.getByRole('group',{name:'Choose a sentence pattern'});
 await expect(list.getByRole('button')).toHaveCount(7);
 await list.getByRole('button',{name:'Ask where something is'}).click();
 await patterns.getByRole('button',{name:'Next example'}).click();
 await patterns.getByRole('button',{name:'Next example'}).click();
 await patterns.getByRole('button',{name:'Next example'}).click();
 await expect(patterns.locator('.sentence-pattern-polish')).toHaveText('Gdzie jest apteka?');
 await patterns.getByRole('button',{name:'Next example'}).click();
 await expect(patterns.locator('.sentence-pattern-polish')).toHaveText('Gdzie mogę kupić bilet?');
 await list.getByRole('button',{name:'Ask how much something costs'}).click();
 await expect(patterns.locator('.sentence-pattern-polish')).toHaveText('Ile to kosztuje?');
 await list.getByRole('button',{name:'Ask a yes-or-no question'}).click();
 await expect(patterns.locator('.sentence-pattern-polish')).toHaveText('Czy to pociąg do Warszawy?');
 await expect(patterns.locator('.sentence-pattern-polish strong')).toHaveText('Czy to');
 await expect(page.getByRole('button',{name:/Play syllable/})).toHaveCount(0);
});

test('C-13: grammar completed then continue into original full-word recorded sentence exercises',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 const panel=guide.getByRole('region',{name:'Recorded first sentence patterns'});
 await panel.getByRole('button',{name:'Build your first sentences'}).click();
 await panel.getByRole('group',{name:'Choose a sentence pattern'})
  .getByRole('button',{name:'Ask for one or two'}).click();
 await panel.getByRole('button',{name:'Check understanding'}).click();
 for(let i=0;i<4;i++){
   await panel.getByRole('group',{name:'Choose the meaning'}).getByRole('button').last().click();
   if(i<3)await panel.getByRole('button',{name:'Next sentence'}).click();
 }
 await expect(panel.getByRole('button',{name:'Continue to sentence practice'})).toBeVisible();
 await panel.getByRole('button',{name:'Continue to sentence practice'}).click();
 await expect(page.locator('.unit-practice-head')).toContainText('Simple food requests');
 await expect(page.locator('.polish-text')).toHaveText('Poproszę wodę');
 await expect(page.locator('.unit-practice-head')).toContainText('1/5');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
});
