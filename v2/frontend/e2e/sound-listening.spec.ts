import {expect,test} from '@playwright/test';

test('C-09: recognize sounds from original Polish whole-word recordings, then compare',async({page,isMobile})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Library'}).first().click();
 await page.getByRole('searchbox',{name:'Search lessons'}).fill('C, CZ');
 await page.getByRole('button',{name:/C, CZ and Ć/}).click();
 const switcher=page.getByRole('group',{name:'Sound learning activity'});
 await expect(switcher.getByRole('button',{name:'Compare words'})).toHaveAttribute('aria-pressed','true');
 await switcher.getByRole('button',{name:'Test my ear'}).click();
 await expect(switcher.getByRole('button',{name:'Test my ear'})).toHaveAttribute('aria-pressed','true');
 await expect(page.locator('.contrast-group')).toHaveCount(0);
 // The ordinary source flashcard must NOT reveal the written answer below quiz.
 await expect(page.locator('.polish-text')).toHaveCount(0);
 const quiz=page.locator('.sound-ear-quiz');
 await expect(quiz.locator('.sound-ear-progress')).toHaveText('1 / 6');
 await expect(quiz.getByRole('button',{name:'Hear word'})).toBeEnabled();
 await expect(quiz.getByText('plac',{exact:true})).toHaveCount(0);
 await quiz.getByRole('button',{name:'Hear word'}).click();
 await quiz.getByRole('button',{name:'CZ',exact:true}).click();
 await expect(quiz.locator('.sound-ear-answer')).toContainText('This recording demonstrates:');
 await expect(quiz.locator('.sound-ear-answer')).toContainText('plac');
 await expect(quiz.locator('.sound-ear-word .sound-focus-letters')).toHaveText('c');
 await quiz.getByRole('button',{name:'Next word'}).click();
 await expect(quiz.locator('.sound-ear-progress')).toHaveText('2 / 6');
 await expect(quiz.getByText('Cztery',{exact:true})).toHaveCount(0);
 await quiz.getByRole('button',{name:'CZ',exact:true}).click();
 await expect(quiz.locator('.sound-ear-answer')).toContainText('Correct.');
 await expect(quiz.locator('.sound-ear-word .sound-focus-letters')).toHaveText('Cz');
 await switcher.getByRole('button',{name:'Compare words'}).click();
 await expect(page.locator('.contrast-group')).toHaveCount(3);
 await expect(page.locator('.polish-text')).toBeVisible();
 await expect(page.getByRole('heading',{name:'Hear sounds in real words'})).toBeVisible();
 const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
 await nav.getByRole('button',{name:'Library'}).click();
 await page.getByRole('searchbox',{name:'Search lessons'}).fill('');
 await expect(page.locator('.lesson-tile')).toHaveCount(26);
});

test('C-09: complete a two-sound contrast check with no fabricated syllable recording or pronunciation score',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('region',{name:'Guided Polish foundations'})
   .getByRole('button',{name:/Hear L and Ł/}).click();
 await page.getByRole('button',{name:'Test my ear'}).click();
 const quiz=page.locator('.sound-ear-quiz');
 await expect(quiz.locator('.sound-ear-progress')).toHaveText('1 / 4');
 for(const label of ['L','Ł','L','Ł']){
   await quiz.getByRole('button',{name:label,exact:true}).click();
   await quiz.getByRole('button',{name:/Next word|Finish/}).click();
 }
 await expect(quiz.getByText('All recorded examples complete.')).toBeVisible();
 await expect(quiz.getByRole('button',{name:'Practise again'})).toBeEnabled();
 await expect(page.locator('.speak-scores')).toHaveCount(0);
 await expect(page.getByRole('button',{name:/Play syllable/})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
 await quiz.getByRole('button',{name:'Practise again'}).click();
 await expect(quiz.locator('.sound-ear-progress')).toHaveText('1 / 4');
});
