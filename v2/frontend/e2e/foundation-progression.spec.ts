import {expect,test} from '@playwright/test';

test('C-12: First words → Basic vocabulary → First sentences / basic grammar appear in that order',async({page,isMobile})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 const phases=guide.locator('.foundation-path-stage');
 await expect(phases).toHaveCount(3);
 await expect(phases.locator('h4')).toHaveText([
   'First words','Basic vocabulary','First sentences / basic grammar'
 ]);
 const first=phases.nth(0).getByRole('group',{name:'First expressions practice'});
 await expect(first.getByRole('button')).toHaveCount(3);
 await expect(first.getByRole('button').first()).toContainText('Yes and no');
 await expect(first.getByRole('button').nth(1)).toContainText('Polite essentials');
 await expect(first.getByRole('button').last()).toContainText('Hello and goodbye');
 const second=phases.nth(1);
 const toggle=second.getByRole('button',{name:'Keep building your everyday vocabulary'});
 await expect(toggle).toHaveAttribute('aria-expanded','false');
 await toggle.click();
 const vocabulary=second.getByRole('group',{name:'More recorded beginner practice'});
 await expect(vocabulary.getByRole('button')).toHaveCount(3);
 await expect(vocabulary.getByRole('button').first()).toContainText('Street and place words');
 await expect(vocabulary.getByRole('button').nth(1)).toContainText('Getting around: first words');
 await expect(vocabulary.getByRole('button').nth(2)).toContainText('More everyday replies');
 const phrases=phases.nth(2).getByRole('group',{name:'Short sentence practice'});
 await expect(phrases.getByRole('button')).toHaveCount(3);
 await expect(phrases.getByRole('button').first()).toContainText('Simple food requests');
 await expect(phrases.getByRole('button').nth(1)).toContainText('Questions in a shop');
 await expect(phrases.getByRole('button').last()).toContainText('Asking where things are');
 const grammar=phases.nth(2).getByRole('region',{name:'Recorded first sentence patterns'});
 await expect(grammar.getByRole('button',{name:'Build your first sentences'}))
   .toHaveAttribute('aria-expanded','false');
 await first.getByRole('button',{name:/Yes and no/}).click();
 await expect(page.locator('.polish-text')).toHaveText('Tak');
 await expect(page.locator('.unit-practice-head')).toContainText('1/2');
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Listen'}).click();
 await expect(page.getByRole('heading',{name:'What did you hear?'})).toBeVisible();
 const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
 await nav.getByRole('button',{name:'Library'}).click();
 await expect(page.locator('.lesson-tile')).toHaveCount(26);
});

test('C-12: completion of final basic vocabulary group introduces grammar BEFORE sentence applications',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 await guide.getByRole('button',{name:'Keep building your everyday vocabulary'}).click();
 await guide.getByRole('group',{name:'More recorded beginner practice'})
  .getByRole('button',{name:/More everyday replies/}).click();
 await expect(page.locator('.polish-text')).toHaveText('Może');
 for(let i=0;i<5;i++){
   await page.getByRole('button',{name:/Reveal meaning/}).click();
   await page.getByRole('button',{name:/Got it/}).click();
 }
 await expect(page.getByRole('heading',{name:'Nicely done!'})).toBeVisible();
 await page.getByRole('button',{name:/Next: First sentences \/ basic grammar/}).click();
 const grammar=page.getByRole('region',{name:'Recorded first sentence patterns'});
 await expect(grammar.getByRole('button',{name:'Build your first sentences'}))
   .toHaveAttribute('aria-expanded','true');
 await expect(grammar.locator('.sentence-pattern-polish')).toHaveText('Poproszę wodę');
 await expect(page.locator('.foundation-path-stage h4')).toHaveText([
  'First words','Basic vocabulary','First sentences / basic grammar'
 ]);
 await expect(page.getByRole('button',{name:/Play syllable/})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
});
