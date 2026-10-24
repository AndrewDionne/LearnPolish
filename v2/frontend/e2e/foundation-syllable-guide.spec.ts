import {expect,test} from '@playwright/test';

test('C-07 beginner Speak and Learn reveal segmented spelling but no unreviewed syllable playback',async({page,isMobile})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 await guide.getByRole('group',{name:'First expressions practice'})
   .getByRole('button',{name:/Polite essentials/}).click();
 await expect(page.locator('.polish-text')).toHaveText('Proszę');
 await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
 const toggle=page.getByRole('button',{name:/Pronunciation guide/});
 await expect(toggle).toHaveAttribute('aria-expanded','false');
 await toggle.click();
 await expect(toggle).toHaveAttribute('aria-expanded','true');
 await expect(page.locator('.pronunciation-text-part')).toHaveText(['Pro','szę']);
 await expect(page.getByRole('button',{name:/Play syllable/})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
 await page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Speak'}).click();
 const speakToggle=page.getByRole('button',{name:/Pronunciation guide/});
 await speakToggle.click();
 await expect(page.locator('.speak-word-segment')).toHaveCount(2);
 await expect(page.locator('.speak-word-polish')).toHaveText(['Pro','szę']);
 await expect(page.locator('.syllable-audio-controls')).toHaveCount(0);
 await expect(page.getByRole('button',{name:/Hear example/})).toBeEnabled();
 const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
 await nav.getByRole('button',{name:'Library'}).click();
 await expect(page.locator('.lesson-tile')).toHaveCount(26);
});

test('C-07 full-utterance clips and Polish letter examples are never silently treated as reviewed syllable MP3s',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 const guide=page.getByRole('region',{name:'Guided Polish foundations'});
 await guide.getByRole('button',{name:/Keep building your everyday vocabulary/}).click();
 await guide.getByRole('group',{name:'More recorded beginner practice'})
   .getByRole('button',{name:/Street and place words/}).click();
 await expect(page.locator('.polish-text')).toHaveText('ulica');
 await page.getByRole('button',{name:/Pronunciation guide/}).click();
 await expect(page.locator('.pronunciation-text-part')).toHaveText(['u','li','ca']);
 await expect(page.getByRole('button',{name:/Play syllable/})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
});
