import {expect,test} from '@playwright/test';

test('Home course continuation survives personal lesson authoring and reload',async({page,isMobile})=>{
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Explore lessons'})).toBeVisible();
  await expect(page.locator('.core-resume-card')).toContainText('Greetings and Introductions');
  await expect(page.locator('.recent-resume-card')).toHaveCount(0);

  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  for(const phrase of ['Dzień dobry','Dobry wieczór']){
    await expect(page.getByText(phrase,{exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Reveal meaning'}).click();
    await page.getByRole('button',{name:/Got it/}).click();
  }
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await page.getByRole('button',{name:/Create lesson/}).click();
  await page.getByRole('textbox',{name:'Lesson name'}).fill('My travel notes');
  await page.getByRole('textbox',{name:'Polish text'}).fill('Miłego dnia');
  await page.getByRole('textbox',{name:'English meaning'}).fill('Have a nice day');
  await page.getByRole('button',{name:'Create lesson →'}).click();
  await expect(page.locator('.learning-head h1')).toHaveText('My travel notes');
  await nav.getByRole('button',{name:'Home'}).click();
  await expect(page.getByRole('button',{name:'Continue course'})).toBeVisible();
  await expect(page.locator('.core-resume-card')).toContainText('Greetings and Introductions');
  await expect(page.locator('.core-resume-card')).toContainText('Next: item 3');
  await expect(page.locator('.recent-resume-card')).toContainText('My travel notes');
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue'))).toBe('Conversation_1');

  await page.reload();
  await expect(page.locator('.core-resume-card')).toContainText('Next: item 3');
  await expect(page.locator('.recent-resume-card')).toContainText('My travel notes');
  await page.locator('.recent-resume-card').click();
  await expect(page.locator('.learning-head h1')).toHaveText('My travel notes');
  await nav.getByRole('button',{name:'Home'}).click();
  await page.locator('.core-resume-card').click();
  await expect(page.getByText('Cześć',{exact:true})).toBeVisible();
  await expect(page.locator('.item-count')).toContainText('3');
});

test('Opening supplementary content never replaces the chosen core lesson',async({page,isMobile})=>{
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('numbers 1-20');
  await page.getByRole('button',{name:/Numbers 1-20/i}).click();
  await expect(page.getByRole('combobox',{name:'Practice group'})).toHaveValue('0');
  await nav.getByRole('button',{name:'Library'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Countries in Polish');
  await page.getByRole('button',{name:/Countries in Polish/}).click();
  await nav.getByRole('button',{name:'Home'}).click();
  await expect(page.locator('.core-resume-card')).toContainText('Numbers 1-20');
  await expect(page.locator('.recent-resume-card')).toContainText('Countries in Polish');
  await page.getByRole('button',{name:'Continue course'}).click();
  await expect(page.getByRole('combobox',{name:'Practice group'})).toHaveValue('0');
  await expect(page.locator('.learning-head h1')).toHaveText('Numbers 1-20');
});

test('Old browser progress migrates to core without copying personal or optional lesson position',async({page})=>{
  await page.goto('/');
  await page.evaluate(()=>{
    localStorage.setItem('ptp-v2-progress',JSON.stringify({
      'Conversation_1:0':{seen:1,remembered:1,needsPractice:0,lastSeen:'2026-10-22T13:00:00Z'},
      'numbers_1-20:0':{seen:1,remembered:1,needsPractice:0,lastSeen:'2026-10-23T13:00:00Z'},
    }));
    localStorage.setItem('ptp-v2-last-lesson','Countries_of_the_World');
    localStorage.removeItem('ptp-v2-core-continue');
  });
  await page.reload();
  await expect(page.locator('.core-resume-card')).toContainText('Numbers 1-20');
  await expect(page.locator('.recent-resume-card')).toContainText('Countries in Polish');
  await page.getByRole('button',{name:'Continue course'}).click();
  await expect(page.locator('.learning-head h1')).toHaveText('Numbers 1-20');
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue'))).toBe('numbers_1-20');
});

test('Small-screen Home keeps both available continuation actions accessible',async({page})=>{
  await page.setViewportSize({width:320,height:720});
  await page.goto('/');
  await expect(page.locator('.core-resume-card')).toBeVisible();
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Countries in Polish');
  await page.getByRole('button',{name:/Countries in Polish/}).click();
  await page.getByRole('navigation',{name:'Mobile navigation'}).getByRole('button',{name:'Home'}).click();
  await expect(page.locator('.core-resume-card')).toBeVisible();
  await expect(page.locator('.recent-resume-card')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
  const details=await page.locator('.core-resume-card,.recent-resume-card').evaluateAll(nodes=>
    nodes.map(node=>({height:node.getBoundingClientRect().height,
      label:node.textContent||''})));
  expect(details).toHaveLength(2);
  for(const data of details)expect(data.height).toBeGreaterThanOrEqual(44);
});
