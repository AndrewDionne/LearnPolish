import {expect,test} from '@playwright/test';

test('C-11 actual recorded request pattern teaches examples then hides Polish until listening-choice response',async({page,isMobile})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 const panel=guide.getByRole('region',{name:'Recorded first sentence patterns'});
 const toggle=panel.getByRole('button',{name:'Build your first sentences'});
 await expect(toggle).toHaveAttribute('aria-expanded','false');
 await toggle.click();
 await expect(toggle).toHaveAttribute('aria-expanded','true');
 const groups=panel.getByRole('group',{name:'Choose a sentence pattern'});
 await expect(groups.getByRole('button')).toHaveCount(5);
 await expect(panel.locator('.sentence-pattern-polish')).toHaveText('Poproszę wodę');
 await expect(panel.locator('.sentence-pattern-polish strong')).toHaveText('Poproszę');
 await expect(panel.locator('.sentence-pattern-meaning')).toHaveText('Water, please');
 await expect(panel.getByRole('button',{name:'Hear sentence'})).toBeEnabled();
 await panel.getByRole('button',{name:'Next example'}).click();
 await expect(panel.locator('.sentence-pattern-polish')).toHaveText('Poproszę kawę');
 await panel.getByRole('button',{name:'Check understanding'}).click();
 await expect(panel.locator('.sentence-pattern-polish')).toHaveCount(0);
 await expect(panel.locator('.sentence-pattern-meaning')).toHaveCount(0);
 await expect(panel.getByText('Listen and choose the meaning.')).toBeVisible();
 const choices=panel.getByRole('group',{name:'Choose the meaning'});
 await expect(choices.getByRole('button')).toHaveCount(2);
 await choices.getByRole('button',{name:'Coffee, please'}).click();
 await expect(panel.locator('.sentence-pattern-reveal')).toContainText('This sentence means:');
 await expect(panel.locator('.sentence-pattern-reveal')).toContainText('Water, please');
 await expect(panel.locator('.sentence-pattern-reveal .sentence-pattern-polish')).toHaveText('Poproszę wodę');
 await panel.getByRole('button',{name:'Next sentence'}).click();
 await expect(panel.locator('.sentence-pattern-heading')).toContainText('2 / 4');
 await expect(panel.locator('.sentence-pattern-polish')).toHaveCount(0);
 const correct=panel.getByRole('group',{name:'Choose the meaning'});
 await correct.getByRole('button',{name:'Coffee, please'}).click();
 await expect(panel.locator('.sentence-pattern-reveal')).toContainText('Correct.');
 await groups.getByRole('button',{name:'Ask where something is'}).click();
 await expect(panel.locator('.sentence-pattern-polish')).toHaveText('Gdzie jest przystanek?');
 await expect(panel.locator('.sentence-pattern-polish strong')).toHaveText('Gdzie jest');
 const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
 await nav.getByRole('button',{name:'Library'}).click();
 await expect(page.locator('.lesson-tile')).toHaveCount(26);
});

test('C-11 four recorded number/quantity variations, completion and mobile no overflow',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const panel=page.getByRole('region',{name:'Recorded first sentence patterns'});
 await panel.getByRole('button',{name:'Build your first sentences'}).click();
 await panel.getByRole('group',{name:'Choose a sentence pattern'})
   .getByRole('button',{name:'Ask for one or two'}).click();
 await expect(panel.locator('.sentence-pattern-polish')).toHaveText('Jeden bilet, proszę');
 await expect(panel.locator('.sentence-pattern-polish strong')).toHaveText('Jeden');
 await panel.getByRole('button',{name:'Next example'}).click();
 await expect(panel.locator('.sentence-pattern-polish')).toHaveText('Dwa bilety, proszę');
 await panel.getByRole('button',{name:'Next example'}).click();
 await expect(panel.locator('.sentence-pattern-polish')).toHaveText('Poproszę stolik dla jednej osoby');
 await panel.getByRole('button',{name:'Next example'}).click();
 await expect(panel.locator('.sentence-pattern-polish strong')).toHaveText('dwóch');
 await panel.locator('.sentence-pattern-next').click();
 const answers=panel.getByRole('group',{name:'Choose the meaning'});
 for(let index=0;index<4;index++){
   await answers.getByRole('button').last().click();
   await panel.getByRole('button',{name:index===3?'Practise again':'Next sentence'}).click();
 }
 await expect(panel.locator('.sentence-pattern-polish')).toHaveText('Jeden bilet, proszę');
 await expect(panel.getByRole('button',{name:'Hear sentence'})).toBeEnabled();
 await expect(page.getByRole('button',{name:/Play syllable/})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
});
