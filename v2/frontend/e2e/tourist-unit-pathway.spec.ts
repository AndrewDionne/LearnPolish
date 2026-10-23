import {expect,test} from '@playwright/test';

test('first tourist unit connects real recorded Listen, Speak and Read material',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const units=page.getByRole('group',{name:'Conversation practice'});
  await expect(units).toBeVisible();
  await expect(units.locator('.tourist-unit-card')).toHaveCount(8);
  await expect(page.locator('.lesson-tile')).toHaveCount(26);
  const buttons=units.getByRole('button');
  await expect(buttons).toHaveCount(22);
  await units.getByRole('button',{name:'Greetings and polite replies: Listen'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Greetings and polite replies');
  await expect(page.locator('.unit-practice-head')).toContainText('Listen · 1/3');
  await expect(page.locator('.item-count')).toContainText('/ 2');
  await expect(page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Listen'})).toHaveAttribute('aria-pressed','true');
  // Existing audio and comprehension controls, not a new synthetic question engine.
  await expect(page.locator('.listening-card')).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await units.getByRole('button',{name:'Greetings and polite replies: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/3');
  await expect(page.locator('.item-count')).toContainText('/ 5');
  await expect(page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Speak'})).toHaveAttribute('aria-pressed','true');
  await nav.getByRole('button',{name:'Library'}).click();
  await units.getByRole('button',{name:'Greetings and polite replies: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Read · 3/3');
  await expect(page.locator('.item-count')).toContainText('/ 4');
  await expect(page.getByText('Cześć! Jak się masz?',{exact:true})).toBeVisible();
  await expect(page.getByRole('group',{name:'Learning modes'}).getByRole('button',{name:'Read'})).toHaveAttribute('aria-pressed','true');
});

test('unit progression offers the next source-backed step without a completion grade',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('button',{name:'Introductions and names: Listen'}).click();
  await expect(page.locator('.item-count')).toContainText('/ 2');
  // Skip advances navigation only. The final item needs deliberate response.
  await page.getByRole('button',{name:'Skip to next →'}).click();
  await page.getByRole('group',{name:'Answer the listening question'})
    .getByRole('button',{name:'Their name'}).click();
  await page.getByRole('button',{name:'Continue →'}).click();
  await expect(page.getByRole('heading',{name:'Nicely done!'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Continue with Speak →'})).toBeVisible();
  await page.getByRole('button',{name:'Continue with Speak →'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/3');
  await expect(page.locator('.item-count')).toContainText('/ 1');
  await expect(page.getByText('Jak masz na imię?',{exact:true})).toBeVisible();
});

test('numbers-and-prices pilot is source-only and does not invent a reading scene',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const unit=page.locator('.tourist-unit-card').filter({hasText:'Numbers, prices and payment'});
  await expect(unit.getByRole('button',{name:'Numbers, prices and payment: Read'})).toHaveCount(0);
  await unit.getByRole('button',{name:'Numbers, prices and payment: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/2');
  await expect(page.locator('.item-count')).toContainText('/ 3');
  await expect(page.getByText('Ile to kosztuje?',{exact:true})).toBeVisible();
  await expect(page.locator('.lesson-meter')).toBeVisible();
  await page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'}).getByRole('button',{name:'Library'}).click();
  await page.getByRole('button',{name:/Numbers 1-20/}).click();
  await expect(page.getByRole('combobox',{name:'Practice group'})).toBeVisible();
  await expect(page.locator('.unit-practice-head')).toHaveCount(0);
});

test('320px unit actions stay in view and personal Library remains separate',async({page})=>{
  await page.setViewportSize({width:320,height:740});
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await expect(page.getByRole('button',{name:'Greetings and polite replies: Listen'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
  await page.getByRole('button',{name:'Greetings and polite replies: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
});

test('T04 source-only restaurant practice offers Listen and Speak without fabricated waiter dialogue',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const unit=page.locator('.tourist-unit-card').filter({hasText:'Ordering food and drinks'});
  await expect(unit).toBeVisible();
  await expect(unit.getByRole('button',{name:'Ordering food and drinks: Read'})).toHaveCount(0);
  await unit.getByRole('button',{name:'Ordering food and drinks: Listen'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Listen · 1/2');
  await expect(page.locator('.item-count')).toContainText('/ 9');
  await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
  await page.getByRole('group',{name:'Choose the meaning'}).getByRole('button',{name:'A table for one, please'}).click();
  await expect(page.getByText('Poproszę stolik dla jednej osoby',{exact:true})).toBeVisible();
  await page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'}).getByRole('button',{name:'Library'}).click();
  await unit.getByRole('button',{name:'Ordering food and drinks: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/2');
  await expect(page.locator('.item-count')).toContainText('/ 8');
  await expect(page.getByText('Poproszę menu',{exact:true})).toBeVisible();
});

test('T05 grocery story uses original listening and reading, with independent shopping Speak phrases',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const unit=page.locator('.tourist-unit-card').filter({hasText:'Shopping for groceries'});
  await unit.getByRole('button',{name:'Shopping for groceries: Listen'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Listen · 1/3');
  await expect(page.locator('.item-count')).toContainText('/ 6');
  await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
  await page.getByRole('button',{name:'Reveal transcript & translation'}).click();
  await expect(page.getByText('Dzień dobry.',{exact:true})).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await unit.getByRole('button',{name:'Shopping for groceries: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/3');
  await expect(page.locator('.item-count')).toContainText('/ 6');
  await expect(page.getByText('Ile to kosztuje?',{exact:true})).toBeVisible();
  await nav.getByRole('button',{name:'Library'}).click();
  await unit.getByRole('button',{name:'Shopping for groceries: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Read · 3/3');
  await expect(page.getByText('Dzień dobry.',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
  await nav.getByRole('button',{name:'Library'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Conversation_-_shopping');
  await page.getByRole('button',{name:/Shopping: Useful Questions/}).click();
  await expect(page.locator('.unit-practice-head')).toHaveCount(0);
});

test('opening cross-journey T05 source excerpt preserves explicit Home course position',async({page,isMobile})=>{
  await page.goto('/');
  await page.evaluate(()=>localStorage.setItem('ptp-v2-core-continue','Conversation_1'));
  await page.reload();
  await expect(page.getByRole('button',{name:'Continue course'})).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await page.getByRole('button',{name:'Shopping for groceries: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Read · 3/3');
  await nav.getByRole('button',{name:'Home'}).click();
  await expect(page.locator('.core-resume-card')).toContainText('Greetings and Introductions');
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue'))).toBe('Conversation_1');
  // The source file may still be independently opened as recent practice.
  await expect(page.locator('.recent-resume-card')).toContainText('At the Grocery Store');
});

test('T06 uses original recorded route exchange and Speak directions without invented left/right text',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const card=page.locator('.tourist-unit-card').filter({hasText:'Finding your way to the centre'});
  await expect(card).toBeVisible();
  await card.getByRole('button',{name:'Finding your way to the centre: Listen'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Listen · 1/3');
  await expect(page.locator('.item-count')).toContainText('/ 5');
  await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
  await page.getByRole('button',{name:'Reveal transcript & translation'}).click();
  await expect(page.getByText('Przepraszam, czy mogę zadać pytanie?',{exact:true})).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await card.getByRole('button',{name:'Finding your way to the centre: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/3');
  await expect(page.locator('.item-count')).toContainText('/ 6');
  await expect(page.getByText('Gdzie jest przystanek?',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'▶ Hear example'})).toBeVisible();
  await nav.getByRole('button',{name:'Library'}).click();
  await card.getByRole('button',{name:'Finding your way to the centre: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Read · 3/3');
  await expect(page.locator('.item-count')).toContainText('/ 5');
  await expect(page.getByText('Przepraszam, czy mogę zadać pytanie?',{exact:true})).toBeVisible();
  await nav.getByRole('button',{name:'Library'}).click();
  await expect(card.locator('.tourist-unit-activity')).toHaveText('0 / 16 tried');
  await expect(card.getByRole('button',{name:'Resume Finding your way to the centre'})).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue'))).toBeNull();
});

test('T06 remains optional and its route source never repositions an already chosen core course',async({page,isMobile})=>{
  await page.goto('/');
  await page.evaluate(()=>localStorage.setItem('ptp-v2-core-continue','Conversation_1'));
  await page.reload();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  const card=page.locator('.tourist-unit-card').filter({hasText:'Finding your way to the centre'});
  await card.getByRole('button',{name:'Finding your way to the centre: Read'}).click();
  await nav.getByRole('button',{name:'Home'}).click();
  await expect(page.locator('.core-resume-card')).toContainText('Greetings and Introductions');
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue'))).toBe('Conversation_1');
});

test('T07 recorded transport scene connects Listen and Read to ticket-machine response and original spoken ticket requests',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const card=page.locator('.tourist-unit-card').filter({hasText:'Taking a tram and buying a ticket'});
  await expect(card).toBeVisible();
  await card.getByRole('button',{name:'Taking a tram and buying a ticket: Listen'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Listen · 1/3');
  await expect(page.locator('.item-count')).toContainText('/ 8');
  await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
  // A real source-backed question about onboard ticket purchases is the sixth
  // original turn, not a newly generated cashier or ticket-price reply.
  for(let i=0;i<5;i++)await page.getByRole('button',{name:'Skip to next →'}).click();
  await page.getByRole('button',{name:'Reveal transcript & translation'}).click();
  await expect(page.getByText('Czy mogę kupić bilet w tramwaju?',{exact:true})).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await card.getByRole('button',{name:'Taking a tram and buying a ticket: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/3');
  await expect(page.locator('.item-count')).toContainText('/ 8');
  await expect(page.getByText('Na którą linię?',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'▶ Hear example'})).toBeVisible();
  await nav.getByRole('button',{name:'Library'}).click();
  await card.getByRole('button',{name:'Taking a tram and buying a ticket: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Read · 3/3');
  await expect(page.locator('.item-count')).toContainText('/ 8');
  await expect(page.getByText('Przepraszam, czy mogę zadać pytanie?',{exact:true})).toBeVisible();
  await nav.getByRole('button',{name:'Library'}).click();
  await expect(card.locator('.tourist-unit-activity')).toHaveText('0 / 24 tried');
  await expect(card.getByRole('button',{name:'Resume Taking a tram and buying a ticket'})).toBeVisible();
});

test('T07 source-mode practice never shifts explicitly selected Home course cursor',async({page,isMobile})=>{
  await page.goto('/');
  await page.evaluate(()=>localStorage.setItem('ptp-v2-core-continue','Conversation_1'));
  await page.reload();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await page.getByRole('button',{name:'Taking a tram and buying a ticket: Read'}).click();
  await nav.getByRole('button',{name:'Home'}).click();
  await expect(page.locator('.core-resume-card')).toContainText('Greetings and Introductions');
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue'))).toBe('Conversation_1');
});

test('T08 museum source visit has recorded ticket, hours and cloakroom Listen/Read, with generic source-backed Speak',async({page,isMobile})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const card=page.locator('.tourist-unit-card').filter({hasText:'Museum tickets and visitor information'});
  await expect(card).toBeVisible();
  await card.getByRole('button',{name:'Museum tickets and visitor information: Listen'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Listen · 1/3');
  await expect(page.locator('.item-count')).toContainText('/ 9');
  await expect(page.getByRole('button',{name:'Play audio'})).toBeEnabled();
  for(let i=0;i<3;i++)await page.getByRole('button',{name:'Skip to next →'}).click();
  await page.getByRole('button',{name:'Reveal transcript & translation'}).click();
  await expect(page.getByText('Do której godziny muzeum jest otwarte?',{exact:true})).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await card.getByRole('button',{name:'Museum tickets and visitor information: Speak'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Speak · 2/3');
  await expect(page.locator('.item-count')).toContainText('/ 7');
  await expect(page.getByText('Jeden bilet, proszę',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'▶ Hear example'})).toBeVisible();
  await nav.getByRole('button',{name:'Library'}).click();
  await card.getByRole('button',{name:'Museum tickets and visitor information: Read'}).click();
  await expect(page.locator('.unit-practice-head')).toContainText('Read · 3/3');
  await expect(page.locator('.item-count')).toContainText('/ 9');
  await expect(page.getByText('Dzień dobry, poproszę dwa bilety do muzeum.',{exact:true})).toBeVisible();
  await nav.getByRole('button',{name:'Library'}).click();
  await expect(card.locator('.tourist-unit-activity')).toHaveText('0 / 25 tried');
  await expect(card.getByRole('button',{name:'Resume Museum tickets and visitor information'})).toBeVisible();
});

test('T08 source activity leaves existing Home course cursor and unrelated ticket unit history untouched',async({page,isMobile})=>{
  await page.goto('/');
  await page.evaluate(()=>{
    localStorage.setItem('ptp-v2-core-continue','Conversation_1');
    localStorage.setItem('ptp-v2-tourist-activity',JSON.stringify({
      version:1,units:{T07:{tried:{speak:['Getting_Around_1:6']},
        cursor:{mode:'speak',itemId:'Getting_Around_1:7'}}}
    }));
  });
  await page.reload();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  const t07=page.locator('.tourist-unit-card').filter({hasText:'Taking a tram and buying a ticket'});
  await expect(t07.locator('.tourist-unit-activity')).toHaveText('1 / 24 tried');
  await page.getByRole('button',{name:'Museum tickets and visitor information: Speak'}).click();
  await nav.getByRole('button',{name:'Home'}).click();
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-core-continue'))).toBe('Conversation_1');
  const state=await page.evaluate(()=>JSON.parse(localStorage.getItem('ptp-v2-tourist-activity')||'{}'));
  expect(state.units.T07.tried).toEqual({speak:['Getting_Around_1:6']});
  expect(state.units.T08.tried).toEqual({});
});
