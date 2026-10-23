import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';

test('26 original source sets remain discoverable in the simpler journey Library',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const core=page.getByRole('region',{name:'Your path'});
  const extras=page.getByRole('region',{name:'Explore more'});
  await expect(core.locator('.lesson-tile')).toHaveCount(20);
  await expect(extras.locator('.lesson-tile')).toHaveCount(6);
  await expect(page.locator('.lesson-tile')).toHaveCount(26);
  await expect(page.locator('.journey-marker')).toHaveCount(20);
  await expect(page.locator('.curriculum-stage-heading h2')).toHaveText(['Your path','Explore more']);
  await expect(page.getByRole('group',{name:'Browse learning stage'})).toHaveCount(0);
  await expect(core.locator('.lesson-tile').first()).toContainText('Greetings and Introductions');
  await expect(core.getByRole('button',{name:/Numbers Beyond 20/}))
    .toContainText('larger values up to 1,020');
  await expect(extras.getByRole('button',{name:/Warsaw Districts and Landmarks/}))
    .toContainText('districts and a few familiar local landmarks');
  await expect(core.getByRole('button',{name:/Everyday Conversations: Greetings/}))
    .toContainText('Read greetings and introductions');
  await expect(core.getByRole('button',{name:/Greetings and Introductions/}))
    .toContainText('Say hello and goodbye');
  await expect(extras).toContainText('still need review');

  // Searches continue to resolve original file identifiers, not just display titles.
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Food and Dinning');
  await expect(page.locator('.lesson-tile')).toHaveCount(1);
  await expect(core.getByRole('button',{name:/Eating Out: Tables and Food/})).toBeVisible();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Grocery store very basic shopping');
  await expect(page.locator('.lesson-tile')).toHaveCount(1);
  await expect(core.getByRole('button',{name:/At the Grocery Store/})).toBeVisible();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('');
  await page.getByRole('group',{name:'Filter lessons'}).getByRole('button',{name:'Polish sounds'}).click();
  await expect(core.locator('.lesson-tile')).toHaveCount(5);
  await expect(page.getByRole('region',{name:'Explore more'})).toHaveCount(0);
  await page.getByRole('group',{name:'Filter lessons'}).getByRole('button',{name:'All lessons'}).click();
  await expect(page.locator('.lesson-tile')).toHaveCount(26);
});

test('Search and activity filters browse freely without exposing curriculum tier labels',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await expect(page.getByRole('group',{name:'Browse learning stage'})).toHaveCount(0);
  const search=page.getByRole('searchbox',{name:'Search lessons'});
  const filters=page.getByRole('group',{name:'Filter lessons'});
  await expect(page.locator('.lesson-tile')).toHaveCount(26);

  await search.fill('Grocery store very basic shopping');
  await expect(page.locator('.lesson-tile')).toHaveCount(1);
  await expect(page.getByRole('region',{name:'Your path'})).toContainText('At the Grocery Store');
  await search.fill('Countries of the World');
  await expect(page.locator('.lesson-tile')).toHaveCount(1);
  await expect(page.getByRole('region',{name:'Explore more'})).toContainText('Countries in Polish');
  await search.fill('');

  await filters.getByRole('button',{name:'Polish sounds'}).click();
  await expect(page.locator('.lesson-tile')).toHaveCount(5);
  await search.fill('Grocery store very basic shopping');
  await expect(page.getByRole('heading',{name:'No matching lessons'})).toBeVisible();
  await filters.getByRole('button',{name:'All lessons'}).click();
  await expect(page.locator('.lesson-tile')).toHaveCount(1);
  await search.fill('');
  await expect(page.locator('.lesson-tile')).toHaveCount(26);
  await filters.getByRole('button',{name:'Reading'}).click();
  await expect(page.locator('.lesson-tile')).toHaveCount(6);
  await filters.getByRole('button',{name:'All lessons'}).click();
  await expect(page.locator('.lesson-tile')).toHaveCount(26);
});

test('Home to library to Learn and progress survives reload', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByText('Real progress.')).toBeVisible();
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await expect(page.getByRole('heading', { name: /Lesson library/ })).toBeVisible();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Dzień dobry');
  await expect(page.getByText('Greetings and Introductions', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Greetings and Introductions/ }).click();
  await expect(page.getByText('Dzień dobry', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Reveal meaning/ }).click();
  await expect(page.getByText('Good morning / Good day')).toBeVisible();
  await page.getByRole('button', { name: /Got it/ }).click();
  await expect(page.getByText('Dobry wieczór', { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Library' }).first().click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Conversation');
  await expect(page.getByText('1 practised', { exact: false }).first()).toBeVisible();
  expect(errors).toEqual([]);
});

test('numbers 1–20 stays one lesson with natural 1–10 / 11–20 sections across modes', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('numbers 1-20');
  await page.getByRole('button', { name: /numbers 1-20/i }).click();

  const groups = page.getByRole('combobox', {name: 'Practice group'});
  await expect(groups).toBeVisible();
  await expect(groups.locator('option')).toHaveText(['Numbers 1–10', 'Numbers 11–20']);
  await expect(groups).toHaveValue('0');
  await expect(page.locator('.item-count')).toContainText('1');

  // Completing a short session does not modify the 20-item lesson catalog.
  for (let index = 0; index < 10; index++) {
    await page.getByRole('button', { name: /Reveal meaning/ }).click();
    await page.getByRole('button', { name: /Got it/ }).click();
  }
  await expect(page.getByRole('heading', { name: 'Nicely done!' })).toBeVisible();
  await expect(page.getByText('You made it through 10 items')).toBeVisible();
  await page.getByRole('button', { name: 'Continue to Numbers 11–20 →' }).click();
  await expect(groups).toHaveValue('1');
  await expect(page.locator('.item-count')).toContainText('1');
  await expect(page.getByRole('button', { name: 'Speak', exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Speak', exact: true }).click();
  await expect(groups).toHaveValue('1');
  await expect(page.getByRole('button', { name: 'Start recording' })).toBeVisible();
  await page.getByRole('button', { name: 'Listen', exact: true }).click();
  await expect(groups).toHaveValue('1');
  await expect(page.getByText('What did you hear?')).toBeVisible();

  // Learners can return to any part and switching mode stays on that part.
  await groups.selectOption('0');
  await expect(groups).toHaveValue('0');
  await page.getByRole('button', { name: 'Learn', exact: true }).click();
  await expect(groups).toHaveValue('0');
  await expect(page.locator('.item-count')).toContainText('/ 10');
  await page.getByRole('button', { name: 'Library' }).first().click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('numbers 1-20');
  await page.getByRole('button', { name: /numbers 1-20/i }).click();
  // Ten completed items: automatically resume at the unvisited eleven–twenty section.
  await expect(groups).toHaveValue('1');
  await expect(page.locator('.item-count')).toContainText('/ 10');
  expect(errors).toEqual([]);
});

test('ambiguous and unfinished greetings remain one lesson but have no scored or implied reference',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await expect(page.getByRole('combobox',{name:'Practice group'})).toHaveCount(0);
  for(let i=0;i<24;i++){
    await page.getByRole('button',{name:/Skip to next/}).click();
  }
  await expect(page.getByText('Jak ma pan/pani na imię?',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Reference pending'})).toBeDisabled();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  // Existing mode switching intentionally starts from the first expression.
  // Visit the exact original item ID without granting XP to skipped recordings.
  for(let i=0;i<24;i++){
    await page.getByRole('button',{name:'Next',exact:true}).click();
  }
  await expect(page.getByText('Jak ma pan/pani na imię?',{exact:true})).toBeVisible();
  await expect(page.getByText('Reference audio unavailable.')).toBeVisible();
  await expect(page.getByRole('button',{name:'Start recording'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Check my pronunciation'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:/Hear example/})).toHaveCount(0);
  await page.getByRole('button',{name:'Next',exact:true}).click();
  await expect(page.getByText('Mam na imię…',{exact:true})).toBeVisible();
  await expect(page.getByText('Reference audio unavailable.')).toBeVisible();
  await expect(page.getByRole('button',{name:'Check my pronunciation'})).toHaveCount(0);
  await page.getByRole('button',{name:'Listen',exact:true}).click();
  await expect(page.locator('.item-count')).toContainText('/ 24');
  await expect(page.getByText('Jak ma pan/pani na imię?',{exact:true})).toHaveCount(0);
  await expect(page.getByText('Mam na imię…',{exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Learn',exact:true}).click();
  await expect(page.locator('.item-count')).toContainText('/ 26');
});

test('other ambiguous lessons retain all original cards but exclude unverified Listen audio',async({page})=>{
  await page.goto('/');
  for(const fixture of [
    {search:'Streets and Road Words',name:/Streets and Road Words/i,skip:10,phrase:'Jak dojść do …?',listen:25},
    {search:'Eating Out: Tables and Food',name:/Eating Out: Tables and Food/i,skip:2,phrase:'Czy ma pan/pani menu po angielsku?',listen:23}
  ]){
    await page.getByRole('button',{name:'Library'}).first().click();
    await page.getByRole('searchbox',{name:'Search lessons'}).fill(fixture.search);
    await page.getByRole('button',{name:fixture.name}).click();
    await expect(page.getByRole('combobox',{name:'Practice group'})).toHaveCount(0);
    for(let i=0;i<fixture.skip;i++)await page.getByRole('button',{name:/Skip to next/}).click();
    await expect(page.getByText(fixture.phrase,{exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:'Reference pending'})).toBeDisabled();
    await page.getByRole('button',{name:'Speak',exact:true}).click();
    // The existing switch-mode action starts again at the beginning of the same lesson.
    for(let i=0;i<fixture.skip;i++)await page.getByRole('button',{name:'Next',exact:true}).click();
    await expect(page.getByText(fixture.phrase,{exact:true})).toBeVisible();
    await expect(page.getByText('Reference audio unavailable.')).toBeVisible();
    await expect(page.getByRole('button',{name:'Start recording'})).toBeVisible();
    await expect(page.getByRole('button',{name:'Check my pronunciation'})).toHaveCount(0);
    await page.getByRole('button',{name:'Listen',exact:true}).click();
    await expect(page.locator('.item-count')).toContainText('/ '+fixture.listen);
  }
});

test('E2 short dialogues stay inside reading lessons and allow read/listen without new XP',async({page})=>{
  const errors:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Everyday Conversations: Greetings');
  await page.getByRole('button',{name:/Everyday Conversations: Greetings/}).click();
  const selector=page.getByRole('group',{name:'Short conversations'});
  await expect(selector.getByRole('button')).toHaveCount(2);
  await selector.getByRole('button',{name:/How are you/}).click();
  const dialogue=page.getByRole('region',{name:'Short dialogue: How are you?'});
  await expect(dialogue).toBeVisible();
  await expect(dialogue.locator('.micro-dialogue-polish')).toHaveText([
    'Cześć! Jak się masz?', 'Dziękuję, mam się dobrze.'
  ]);
  await expect(dialogue.getByRole('button',{name:'Play Person A turn 1'})).toBeEnabled();
  await expect(dialogue.getByRole('button',{name:'Play Person B turn 2'})).toBeEnabled();
  await expect(dialogue.getByRole('button',{name:'0.5×'})).toHaveCount(0);
  await expect(dialogue.getByRole('button',{name:'1.25×'})).toHaveCount(0);
  await expect(dialogue.getByRole('button',{name:'1×'})).toHaveAttribute('aria-pressed','true');
  await dialogue.getByRole('button',{name:'Listen first'}).click();
  await expect(dialogue.locator('.micro-dialogue-polish')).toHaveCount(0);
  await expect(dialogue.locator('.micro-dialogue-hidden')).toHaveCount(2);
  await expect(dialogue.getByRole('button',{name:'Show English translations'})).toHaveCount(0);
  await expect(dialogue.getByText('How does Person B respond to the greeting?')).toBeVisible();
  await dialogue.getByRole('button',{name:'They say they are feeling well.'}).click();
  await expect(dialogue.getByRole('status')).toContainText('Correct!');
  await expect(dialogue.getByRole('button',{name:'They ask for directions.'})).toBeDisabled();
  await expect(dialogue.locator('.micro-dialogue-polish')).toHaveCount(0);
  await dialogue.getByRole('button',{name:'Reveal Polish dialogue'}).click();
  await expect(dialogue.locator('.micro-dialogue-polish')).toHaveCount(2);
  await dialogue.getByRole('button',{name:'Show English translations'}).click();
  await expect(dialogue.locator('.micro-dialogue-english')).toHaveText([
    'Hi! How are you?', 'Thank you, I am well.'
  ]);
  await dialogue.getByRole('button',{name:'Back to reading'}).click();
  await expect(dialogue).toHaveCount(0);
  await expect(page.getByText('Cześć! Jak się masz?',{exact:true})).toBeVisible();
  await expect(page.locator('.item-count')).toContainText('/ 6');
  await selector.getByRole('button',{name:/What's your name/}).click();
  const names=page.getByRole('region',{name:"Short dialogue: What's your name?"});
  await expect(names.locator('.micro-dialogue-polish')).toHaveText([
      'Cześć, jak masz na imię?', 'Mam na imię Andrew.'
    ]);
  await names.getByRole('button',{name:'Their address.'}).click();
  await expect(names.getByRole('status')).toContainText('Not quite');
  await expect(names.getByRole('status')).toContainText('Mam na imię Andrew');
  await names.getByRole('button',{name:'Listen first'}).click();
  await expect(names.getByRole('status')).toHaveCount(0);
  await expect(names.getByRole('button',{name:'Their name.'})).toBeEnabled();
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('At the Grocery Store');
  await page.getByRole('button',{name:/At the Grocery Store/}).click();
  await page.getByRole('group',{name:'Short conversations'})
    .getByRole('button',{name:/Buying apples/}).click();
  const grocery=page.getByRole('region',{name:'Short dialogue: Buying apples'});
  await expect(grocery.locator('.micro-dialogue-speaker')).toHaveText([
    'Customer','Shop assistant','Customer'
  ]);
  await expect(grocery.locator('.micro-dialogue-polish')).toHaveText([
    'Dzień dobry, poproszę kilogram jabłek.',
    'Jakie jabłka pan lubi? Czerwone czy zielone?',
    'Poproszę czerwone jabłka.'
  ]);
  await grocery.getByRole('button',{name:'Listen first'}).click();
  await expect(grocery.locator('.micro-dialogue-hidden')).toHaveCount(3);
  await expect(grocery.getByRole('button',{name:'Show English translations'})).toHaveCount(0);
  await grocery.getByRole('button',{name:'Red apples.'}).click();
  await expect(grocery.getByRole('status')).toContainText('Correct!');
  await expect(grocery.locator('.micro-dialogue-polish')).toHaveCount(0);
  await grocery.getByRole('button',{name:'Back to reading'}).click();
  await expect(page.locator('.item-count')).toContainText('/ 9');
  expect(errors).toEqual([]);
});

test('E2 turn-taking chooses authentic Polish replies without awarding XP or storing scores', async ({page})=>{
  const errors:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Everyday Conversations: Greetings');
  await page.getByRole('button',{name:/Everyday Conversations: Greetings/}).click();
  const selector=page.getByRole('group',{name:'Short conversations'});
  await selector.getByRole('button',{name:/How are you/}).click();
  const how=page.getByRole('region',{name:'Short dialogue: How are you?'});
  await how.getByRole('button',{name:'Take a turn'}).click();
  await expect(how.getByRole('group',{name:'Choose your Polish reply'}).getByRole('button')).toHaveCount(3);
  await expect(how.getByRole('button',{name:'Play the other speaker'})).toBeEnabled();
  await expect(how.locator('.micro-dialogue-turns')).toHaveCount(0);
  await expect(how.getByText('Cześć! Jak się masz?',{exact:true})).toBeVisible();
  await how.getByRole('group',{name:'Choose your Polish reply'}).getByRole('button',{name:'Mam na imię Andrew.'}).click();
  await expect(how.getByRole('status')).toContainText('Try this reply:');
  await expect(how.getByRole('status')).toContainText('Dziękuję, mam się dobrze.');
  await expect(how.getByRole('button',{name:'Play the correct reply'})).toBeEnabled();
  await how.getByRole('button',{name:'Try the reply again'}).click();
  await how.getByRole('group',{name:'Choose your Polish reply'})
    .getByRole('button',{name:'Dziękuję, mam się dobrze.'}).click();
  await expect(how.getByRole('status')).toContainText('That fits!');
  await how.getByRole('button',{name:'Listen first'}).click();
  await expect(how.getByRole('status')).toHaveCount(0);
  await expect(how.locator('.micro-dialogue-hidden')).toHaveCount(2);
  await how.getByRole('button',{name:'Take a turn'}).click();
  await expect(how.getByRole('group',{name:'Choose your Polish reply'}).getByRole('button')).toHaveCount(3);
  await how.getByRole('button',{name:'Back to reading'}).click();
  await expect(page.locator('.item-count')).toContainText('/ 6');
  await selector.getByRole('button',{name:/What's your name/}).click();
  const names=page.getByRole('region',{name:"Short dialogue: What's your name?"});
  await names.getByRole('button',{name:'Take a turn'}).click();
  await names.getByRole('group',{name:'Choose your Polish reply'})
    .getByRole('button',{name:'Mam na imię Andrew.'}).click();
  await expect(names.getByRole('status')).toContainText('That fits!');
  await page.getByRole('button',{name:'Library'}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('At the Grocery Store');
  await page.getByRole('button',{name:/At the Grocery Store/}).click();
  await page.getByRole('group',{name:'Short conversations'}).getByRole('button',{name:/Buying apples/}).click();
  const apples=page.getByRole('region',{name:'Short dialogue: Buying apples'});
  await apples.getByRole('button',{name:'Take a turn'}).click();
  await expect(apples.getByText('Jakie jabłka pan lubi? Czerwone czy zielone?',{exact:true})).toBeVisible();
  await apples.getByRole('group',{name:'Choose your Polish reply'})
    .getByRole('button',{name:'Poproszę czerwone jabłka.'}).click();
  await expect(apples.getByRole('status')).toContainText('That fits!');
  await apples.getByRole('button',{name:'Back to reading'}).click();
  await expect(page.locator('.item-count')).toContainText('/ 9');
  expect(errors).toEqual([]);
});

test('responsive mobile library and lesson controls', async ({ page, isMobile }) => {
  if (!isMobile) test.skip();
  await page.goto('/');
  await page.getByRole('navigation', { name: 'Mobile navigation' }).getByRole('button', { name: 'Library' }).click();
  await expect(page.getByRole('heading', { name: /Lesson library/ })).toBeVisible();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('numbers 1-20');
  await page.getByRole('button', { name: /numbers 1-20/i }).click();
  await expect(page.getByText('Jeden', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Reveal meaning/ }).click();
  await expect(page.getByText('One', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Got it/ }).click();
  await expect(page.getByText('Dwa', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/mobile-learn.png', fullPage: true });
});

test('create, edit, export, import and delete a personal lesson without deploying', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.getByRole('button', { name: /Create lesson/ }).click();
  await page.getByRole('textbox', { name: 'Lesson name' }).fill('At the bakery');
  await page.getByRole('textbox', { name: 'Polish text' }).fill('Poproszę chleb');
  await page.getByRole('textbox', { name: 'English meaning' }).fill('Bread, please');
  await page.getByRole('button', { name: /Create lesson/ }).click();
  await expect(page.getByText('Poproszę chleb', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Edit lesson' }).click();
  await page.getByRole('textbox', { name: 'Lesson name' }).fill('At the Polish bakery');
  await page.getByRole('textbox', { name: 'English meaning' }).fill('A loaf of bread, please');
  await page.getByRole('button', { name: /Save changes/ }).click();
  await expect(page.getByText('At the Polish bakery', { exact: true }).first()).toBeVisible();

  const exportStarted = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export JSON' }).click();
  const exported = await exportStarted;
  expect(exported.suggestedFilename()).toMatch(/personal_.*\.json/);

  await page.reload();
  await page.getByRole('button', { name: 'Library' }).first().click();
  await expect(page.getByText('At the Polish bakery', { exact: true })).toBeVisible();

  const imported = {
    schemaVersion: 1, id: 'old-portable-id', title: 'Imported lesson',
    kind: 'vocabulary', source: 'personal',
    items: [{ id: 'one', polish: 'Dziękuję', english: 'Thank you', audio: 'https://untrusted.example/audio.mp3' }],
  };
  await page.locator('input[aria-label="Import lesson JSON"]').setInputFiles({
    name: 'import.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(imported)),
  });
  await expect(page.getByText('Imported lesson', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Imported lesson/ }).click();
  await expect(page.getByText('Dziękuję', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /No audio/ })).toBeDisabled();

  page.on('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByText('Imported lesson', { exact: true })).toHaveCount(0);
});


test('Read resumes a saved passage and Listen reveals content only after answering', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Everyday Conversations: Greetings');
  await page.getByRole('button', { name: /Everyday Conversations: Greetings/ }).click();
  await expect(page.getByText('Cześć! Jak się masz?', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Read' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: /Skip to next/ }).click();
  await expect(page.getByText('Dziękuję, mam się dobrze.', { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Library' }).first().click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Everyday Conversations: Greetings');
  await page.getByRole('button', { name: /Everyday Conversations: Greetings/ }).click();
  await expect(page.getByText('Dziękuję, mam się dobrze.', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Listen', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Listen', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('Cześć! Jak się masz?', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: '0.75×' }).click();
  await expect(page.getByRole('button', { name: '0.75×' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('group', { name: /Choose the meaning|Answer the listening question/ }).getByRole('button').first().click();
  await expect(page.locator('.listen-transcript')).toBeVisible();
  await expect(page.getByText('Cześć! Jak się masz?', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Continue/ }).click();
  await expect(page.getByText('What did you hear?')).toBeVisible();
  await expect(page.getByText('Dziękuję, mam się dobrze.', { exact: true })).toHaveCount(0);
  await page.screenshot({ path: 'test-results/listen-practice.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('Listen is unavailable when personal lessons have no trusted audio', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.getByRole('button', { name: /Create lesson/ }).click();
  await page.getByRole('textbox', { name: 'Lesson name' }).fill('No audio yet');
  await page.getByRole('textbox', { name: 'Polish text' }).fill('Jabłko');
  await page.getByRole('textbox', { name: 'English meaning' }).fill('Apple');
  await page.getByRole('button', { name: /Create lesson/ }).click();
  await expect(page.getByRole('button', { name: 'Listen', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'No audio' })).toBeDisabled();
});


test('offline lesson pack is confirmed only after caching and supports an offline reload', async ({ page, context }) => {
  await page.goto('/');
  await page.evaluate(async () => {
    if (!('serviceWorker' in navigator)) throw new Error('Service workers unavailable');
    await navigator.serviceWorker.ready;
  });
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Greetings and Introductions');
  await page.getByRole('button', { name: /Greetings and Introductions/ }).click();
  await page.getByRole('button', { name: /Download for offline/ }).click();
  await expect(page.getByText('Offline ready', { exact: false })).toBeVisible({ timeout: 30000 });
  const storedAudio = await page.evaluate(async () => {
    const cache = await caches.open('ptp-v2-lesson-audio-v1');
    return (await cache.keys()).length;
  });
  expect(storedAudio).toBeGreaterThan(0);
  // The worker may be installed/ready before clients.claim() controls this tab.
  // Wait for control before disconnecting the network.
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  await context.setOffline(true);
  const before = await page.evaluate(async () => {
    const keys = await caches.keys();
    try {
      const response = await fetch('/');
      return { cacheNames: keys, fetchOk: response.ok, status: response.status, controlled: !!navigator.serviceWorker.controller };
    } catch (error) { return { cacheNames: keys, fetchError: String(error), controlled: !!navigator.serviceWorker.controller }; }
  });
  console.log('OFFLINE PRE-RELOAD:', JSON.stringify(before));
  await page.reload();
  const after = await page.evaluate(async () => {
    let cacheInfo = [];
    try { cacheInfo = await caches.keys(); } catch { /* browser error page */ }
    return { href: location.href, title: document.title, body: document.body?.innerText.slice(0, 700), controlled: !!navigator.serviceWorker?.controller, cacheInfo };
  }).catch(error => ({ error: String(error) }));
  console.log('OFFLINE POST-RELOAD:', JSON.stringify(after));
  await expect(page.getByText('Real progress.')).toBeVisible();
  await page.getByRole('button', { name: 'Library' }).first().click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Greetings and Introductions');
  await page.getByRole('button', { name: /Greetings and Introductions/ }).click();
  await expect(page.getByText('Offline ready', { exact: false })).toBeVisible();
  await expect(page.getByText('Dzień dobry', { exact: true })).toBeVisible();
  await context.setOffline(false);
  await page.getByRole('button', { name: 'Remove offline copy' }).click();
  await expect(page.getByRole('button', { name: /Download for offline/ })).toBeVisible();
});


test('Speak Next escapes pending microphone permission and active capture without awarding XP', async ({ page }) => {
  await page.addInitScript(() => {
    (window as any).__stoppedMicrophoneTracks = 0;
    let grantFirst: ((stream: MediaStream) => void) | null = null;
    let calls = 0;
    const makeStream = () => ({
      getTracks: () => [{ stop: () => { (window as any).__stoppedMicrophoneTracks++; } }],
    } as unknown as MediaStream);
    (window as any).__grantPendingMicrophone = () => { grantFirst?.(makeStream()); };
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      configurable: true,
      value: () => ++calls === 1
        ? new Promise<MediaStream>(resolve => { grantFirst = resolve; })
        : Promise.resolve(makeStream()),
    });
    class MockRecorder {
      static isTypeSupported(_mime: string) { return true; }
      mimeType = 'audio/wav';
      state = 'inactive';
      ondataavailable: ((event: {data: Blob}) => void) | null = null;
      onstop: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(_stream: MediaStream, _options?: unknown) {}
      start() { this.state = 'recording'; }
      stop() { this.state = 'inactive'; }
    }
    Object.defineProperty(window, 'MediaRecorder', { configurable: true, value: MockRecorder });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Greetings and Introductions');
  await page.getByRole('button', { name: /Greetings and Introductions/ }).click();
  await page.getByRole('button', { name: 'Speak', exact: true }).click();
  await expect(page.getByText('Dzień dobry', { exact: true })).toBeVisible();

  // A stalled OS/browser permission prompt must not hold the learner hostage.
  await page.getByRole('button', { name: 'Start recording' }).click();
  await expect(page.getByText('Requesting microphone permission…')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Next', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(page.getByText('Dobry wieczór', { exact: true })).toBeVisible();
  await page.evaluate(() => (window as any).__grantPendingMicrophone());
  await page.waitForFunction(() => (window as any).__stoppedMicrophoneTracks === 1);

  // A currently running recording can also be abandoned with the SAME Next.
  await page.getByRole('button', { name: 'Start recording' }).click();
  await expect(page.getByRole('button', { name: 'Stop recording' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Next', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await page.waitForFunction(() => (window as any).__stoppedMicrophoneTracks === 2);

  const expedition = await page.evaluate(() => JSON.parse(localStorage.getItem('ptp-v2-expedition') || '{}'));
  expect((expedition.events || []).filter((event: {mode: string}) => event.mode === 'speak')).toHaveLength(0);
  await expect(page.locator('#personal-speech-replay')).toHaveCount(0);
});

test('Speak records, checks acoustic quality, replays locally, and clears on next phrase', async ({ page }) => {
  await page.addInitScript(() => {
    const length = 16000;
    const bytes = new ArrayBuffer(44 + length * 2);
    const view = new DataView(bytes);
    for (const [pos, chars] of [[0,'RIFF'], [8,'WAVE'], [12,'fmt '], [36,'data']] as const) {
      for (let i = 0; i < chars.length; i++) view.setUint8(pos + i, chars.charCodeAt(i));
    }
    view.setUint32(4, bytes.byteLength - 8, true);
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    view.setUint32(40, length * 2, true);
    for (let i = 0; i < length; i++) view.setInt16(44 + 2 * i, Math.round(5000 * Math.sin(i * .23)), true);
    (window as any).__microphoneTrackStops = 0;
    const fakeStream = {getTracks: () => [{stop: () => { (window as any).__microphoneTrackStops++; }}]};
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      configurable: true, value: async () => fakeStream,
    });
    class MockRecorder {
      static isTypeSupported(_: string) { return true; }
      mimeType = 'audio/wav';
      state = 'inactive';
      ondataavailable: ((event: {data: Blob}) => void) | null = null;
      onstop: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(_stream: unknown, _options?: unknown) {}
      start() { this.state = 'recording'; }
      stop() {
        this.state = 'inactive';
        queueMicrotask(() => {
          this.ondataavailable?.({data: new Blob([bytes], {type: 'audio/wav'})});
          this.onstop?.();
        });
      }
    }
    Object.defineProperty(window, 'MediaRecorder', {configurable: true, value: MockRecorder});
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Explore lessons'}).click();
  await page.getByRole('searchbox', {name: 'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button', {name: /Greetings and Introductions/}).click();
  await page.getByRole('button', {name: 'Speak', exact: true}).click();
  await expect(page.getByText('Dzień dobry', {exact: true})).toBeVisible();
  const guide = page.getByRole('button',{name:/Pronunciation guide/});
  await expect(guide).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('.speak-english-fallback')).toHaveCount(0);
  await expect(page.locator('.lesson-footer')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Export JSON'})).toHaveCount(0);
  await guide.click();
  await expect(guide).toHaveAttribute('aria-pressed','true');
  await expect(page.getByText('jen DOH-brih',{exact:true})).toBeVisible();
  await page.getByRole('button', {name: /Start recording/}).click();
  await expect(page.getByRole('button', {name: 'Stop recording'})).toBeVisible();
  await page.getByRole('button', {name: 'Stop recording'}).click();
  await expect(page.getByText(/Recording ready/)).toBeVisible();
  await expect(page.locator('#personal-speech-replay')).toHaveAttribute('src', /blob:/);
  await expect(page.getByText(/Recording ready/)).toBeVisible();
  await page.getByRole('button', {name:'Next', exact:true}).click();
  await expect(page.getByText('Dobry wieczór', {exact: true})).toBeVisible();
  await expect(guide).toHaveAttribute('aria-pressed','true');
  await expect(page.getByText('DOH-brih VYEH-choor',{exact:true})).toBeVisible();
  await guide.click();
  await expect(page.locator('.speak-english-fallback')).toHaveCount(0);
  await expect(guide).toHaveAttribute('aria-pressed','false');
  const earned = await page.evaluate(() => JSON.parse(localStorage.getItem('ptp-v2-expedition') || '{}'));
  expect(earned.events.some((entry:{mode:string})=>entry.mode==='speak')).toBe(true);
  await expect(page.locator('#personal-speech-replay')).toHaveCount(0);
  const trackStops = await page.evaluate(() => (window as any).__microphoneTrackStops);
  expect(trackStops).toBeGreaterThan(0);
  await page.screenshot({path: 'test-results/speak-capture.png', fullPage: true});
});

test('Speak handles denied microphone permissions without grading or blocking navigation', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'permissions', {
      configurable: true,
      value: {query: async () => ({state: 'denied'})},
    });
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      configurable: true,
      value: async () => { throw new DOMException('Permission denied', 'NotAllowedError'); },
    });
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Explore lessons'}).click();
  await page.getByRole('searchbox', {name: 'Search lessons'}).fill('numbers 1-20');
  await page.getByRole('button', {name: /numbers 1-20/i}).click();
  await page.getByRole('button', {name: 'Speak', exact: true}).click();
  await page.getByRole('button', {name: /Start recording/}).click();
  await expect(page.getByRole('alert')).toContainText('microphone access is blocked for this exact site');
  await page.getByRole('button', {name:'Next', exact:true}).click();
  await expect(page.getByText('Dwa', {exact: true})).toBeVisible();
});


test('Practice review queue targets only due cards and preserves scheduling after reload', async ({page,isMobile}) => {
  const practiceTab=page.getByRole('navigation',{
    name:isMobile?'Mobile navigation':'Main navigation',
  }).getByRole('button',{name:'Practice',exact:true});
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.setItem('ptp-v2-review-schedule', JSON.stringify({
      'Conversation_1:0': {streak: 0, attempts: 1, lastReviewedAt: '2020-01-01T00:00:00.000Z', dueAt: '2020-01-01T00:00:00.000Z'},
      'Conversation_1:1': {streak: 1, attempts: 1, lastReviewedAt: '2020-01-01T00:00:00.000Z', dueAt: '2099-01-01T00:00:00.000Z'},
    }));
  });
  await page.reload();
  await practiceTab.click();
  await expect(page.getByText('1 due now')).toBeVisible();
  await page.getByRole('button', {name:/Greetings and Introductions.*1 expression.*Review/}).click();
  await expect(page.locator('.learning-head h1')).toHaveText('Greetings and Introductions');
  await expect(page.getByText('Dzień dobry', {exact:true})).toBeVisible();
  await page.getByRole('button', {name:/Reveal meaning/}).click();
  await page.getByRole('button', {name:/Got it/}).click();
  await expect(page.getByText('REVIEW COMPLETE', {exact:true})).toBeVisible();
  // A due review now returns directly to Practice, not via the Library.
  await page.getByRole('button', {name:'Back to practice →', exact:true}).click();
  await expect(page.getByRole('heading',{name:'Practice.'})).toBeVisible();
  await expect(page.getByText('0 due now')).toBeVisible();
  await page.reload();
  await practiceTab.click();
  await expect(page.getByText('0 due now')).toBeVisible();
});


test('sound lab compares individually sourced MP3 examples, not bundled phrases', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.locator('.filter-buttons').getByRole('button', { name: 'Polish sounds' }).click();
  await expect(page.getByRole('button', { name: /C, CZ and Ć/ })).toBeVisible();
  await expect(page.getByText('letter recognition', { exact: false })).toHaveCount(0);
  await page.getByRole('button', { name: /C, CZ and Ć/ }).click();
  const lab = page.getByRole('region', { name: 'Compare Polish sounds' });
  await expect(lab).toBeVisible();
  await expect(lab.getByRole('button', { name: 'Play plac' })).toBeVisible();
  await expect(lab.getByRole('button', { name: 'Play Cztery' })).toBeVisible();
  await expect(lab.getByRole('button', { name: 'Play Pięć' })).toBeVisible();
  await lab.getByRole('button', { name: /Cztery/ }).first().click();
  await expect(lab.getByRole('button', { name: /Cztery/ }).first()).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: 'Speak', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Listen', exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/sound-lab.png', fullPage: true });
  expect(errors).toEqual([]);
});


test('full browser-local backup safely restores personal lessons, recall and review dates', async ({ page, isMobile }) => {
  await page.goto('/');
  await page.getByRole('button', {name:'Explore lessons'}).click();
  await page.getByRole('button', {name:/Create lesson/}).click();
  await page.getByRole('textbox', {name:'Lesson name'}).fill('Saved Polish lesson');
  await page.getByRole('textbox', {name:'Polish text'}).fill('Świetnie');
  await page.getByRole('textbox', {name:'English meaning'}).fill('Great');
  await page.getByRole('button', {name:/Create lesson/}).click();
  await page.getByRole('button', {name:/Reveal meaning/}).click();
  await page.getByRole('button', {name:/Got it/}).click();
  await page.getByRole('button', {name:/My progress|Profile/}).last().click();
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', {name:'Export full backup'}).click();
  const file = await downloadEvent;
  expect(file.suggestedFilename()).toBe('path-to-polish-v2-backup.json');
  const bytes = await readFile(await file.path());
  const saved = JSON.parse(bytes.toString('utf8'));
  expect(saved.format).toBe('path-to-polish-v2-local-backup');
  expect(saved.personalLessons).toHaveLength(1);
  expect(Object.keys(saved.progress)).toHaveLength(1);
  expect(Object.keys(saved.reviews)).toHaveLength(1);
  expect(bytes.toString('utf8')).not.toContain('audio/webm');

  await page.evaluate(() => {
    for (const key of ['ptp-v2-personal-lessons','ptp-v2-progress','ptp-v2-review-schedule',
       'ptp-v2-reading-position','ptp-v2-last-lesson']) localStorage.removeItem(key);
  });
  await page.reload();
  await page.getByRole('button', {name:/My progress|Profile/}).last().click();
  await expect(page.getByText('0%')).toBeVisible();
  page.once('dialog', dialog => dialog.accept());
  await page.locator('input[aria-label="Restore from backup"]').setInputFiles({
    name:'backup.json', mimeType:'application/json', buffer:bytes,
  });
  await expect(page.getByText(/Backup restored: 1 personal lessons/)).toBeVisible();
  await expect(page.getByText('100%')).toBeVisible();
  await page.reload();
  await page.getByRole('button', {name:'Library'}).first().click();
  await expect(page.getByText('Saved Polish lesson', {exact:true})).toBeVisible();
  // Target application navigation, not a Library tile whose description
  // happens to contain the word "practice".
  const nav = page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Practice',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Practice.'})).toBeVisible();
  await expect(page.getByText('0 due now')).toBeVisible();
});


test('XP is awarded for actual Learn/Listen responses, but not a skipped Speak attempt', async ({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
 await page.getByRole('button',{name:/Greetings and Introductions/}).click();
 await page.getByRole('button',{name:/Reveal meaning/}).click();
 await page.getByRole('button',{name:/Got it/}).click();
 await page.getByRole('button',{name:'Listen',exact:true}).click();
 await page.getByRole('group',{name:'Choose the meaning'}).getByRole('button').first().click();
 await page.getByRole('button',{name:'Continue →',exact:true}).click();
 await page.getByRole('button',{name:'Speak',exact:true}).click();
 await page.getByRole('button',{name:'Next',exact:true}).click();
 await page.getByRole('button',{name:/My progress|Profile/}).last().click();
 const xp=page.getByRole('region',{name:'Your learning XP'});
 await expect(xp).toContainText('20');
 const state=await page.evaluate(()=>JSON.parse(localStorage.getItem('ptp-v2-expedition')||'{}'));
 expect(state.events.map((e:{mode:string})=>e.mode).sort()).toEqual(['learn','listen']);
 await page.reload();
 await page.getByRole('button',{name:/My progress|Profile/}).last().click();
 await expect(page.getByRole('region',{name:'Your learning XP'})).toContainText('20');
});

test('XP and expedition targets survive full backup and restore; custom weekly goal persists',async ({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Expedition'}).first().click();
 await page.getByLabel('Explore another region').selectOption('podkarpackie');
 await expect(page.getByRole('heading',{name:'Podkarpackie'})).toBeVisible();
 await page.getByRole('button',{name:'Library'}).first().click();
 await page.getByRole('searchbox',{name:'Search lessons'}).fill('Everyday Conversations: Greetings');
 await page.getByRole('button',{name:/Everyday Conversations: Greetings/}).click();
 await page.getByRole('button',{name:'How are you?',exact:true}).click();
 await page.getByRole('button',{name:'Continue →',exact:true}).click();
 await page.getByRole('button',{name:/My progress|Profile/}).last().click();
 await page.getByLabel('My own goal').check();
 await page.getByRole('spinbutton',{name:'Custom weekly XP goal'}).fill('250');
 await page.getByRole('button',{name:'Save goal'}).click();
 const download=page.waitForEvent('download');
 await page.getByRole('button',{name:'Export full backup'}).click();
 const bytes=await readFile(await (await download).path());
 const data=JSON.parse(bytes.toString());
 expect(data.expedition.events).toHaveLength(1);
 expect(data.expedition.selectedRegion).toBe('podkarpackie');
 expect(data.expedition.selfGoal).toBe(250);
 await page.evaluate(()=>localStorage.removeItem('ptp-v2-expedition'));
 await page.reload();
 await page.getByRole('button',{name:/My progress|Profile/}).last().click();
 page.once('dialog',d=>d.accept());
 await page.locator('input[aria-label="Restore from backup"]').setInputFiles({name:'restore.json',mimeType:'application/json',buffer:bytes});
 await expect(page.getByRole('region',{name:'Your learning XP'})).toContainText('240 XP until your weekly goal');
 await expect(page.getByLabel('My own goal')).toBeChecked();
 await expect(page.getByRole('spinbutton',{name:'Custom weekly XP goal'})).toHaveValue('250');
 await page.getByRole('button',{name:'Expedition'}).first().click();
 await expect(page.getByRole('heading',{name:'Podkarpackie'})).toBeVisible();
 await expect(page.getByRole('progressbar',{name:'Podkarpackie unlock progress'})).toHaveAttribute('aria-valuenow','10');
});

test('completed Read lesson hands off to Listen without leaving the lesson', async ({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Everyday Conversations: Greetings');
  await page.getByRole('button',{name:/Everyday Conversations: Greetings/}).click();
  for(let i=0;i<5;i++) await page.getByRole('button',{name:/Skip to next/}).click();
  await page.getByRole('button',{name:/Reveal translation without answering/}).click();
  await page.getByRole('button',{name:/Got it/}).click();
  await expect(page.getByText('SESSION COMPLETE',{exact:true})).toBeVisible();
  const next=page.getByRole('group',{name:'Continue learning in another mode'});
  await expect(next.getByRole('button',{name:'Listen →'})).toBeVisible();
  await next.getByRole('button',{name:'Listen →'}).click();
  await expect(page.getByRole('button',{name:'Listen',exact:true})).toHaveAttribute('aria-pressed','true');
  await expect(page.getByText('What did you hear?')).toHaveCount(0);
  await expect(page.getByRole('button',{name:/Play audio/})).toBeVisible();
});

test('interactive open map permits distant choice and restores destination on reload',async ({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Expedition'}).first().click();
 const map=page.getByRole('region',{name:'Open Poland expedition map'});
 await expect(map.locator('path[role="button"]')).toHaveCount(16);
 await map.getByRole('button',{name:'Małopolskie'}).click();
 await expect(map.getByRole('heading',{name:'Małopolskie'})).toBeVisible();
 await map.getByLabel('Explore another region').selectOption('pomorskie');
 await page.reload();
 await page.getByRole('button',{name:'Expedition'}).first().click();
 await expect(page.getByRole('heading',{name:'Pomorskie'})).toBeVisible();
 await expect(page.getByText(/Your personal XP and map are saved locally/)).toBeVisible();
 await page.screenshot({path:'test-results/open-poland-expedition.png',fullPage:true});
});

test('late microphone permission after leaving Speak stops tracks and cannot award XP', async ({page}) => {
  await page.addInitScript(() => {
    (window as any).__lateTracksStopped = 0;
    (window as any).__resolveLateMicrophone = null;
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      configurable: true,
      value: () => new Promise(resolve => {
        (window as any).__resolveLateMicrophone = () => resolve({
          getTracks: () => [{stop: () => {(window as any).__lateTracksStopped++;}}],
        });
      }),
    });
  });
  const browserErrors: string[] = [];
  page.on('pageerror', e => browserErrors.push(e.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await page.getByRole('button',{name:/Start recording/}).click();
  await expect(page.getByText(/Requesting microphone permission/)).toBeVisible();
  await page.getByRole('button',{name:/Back to library/}).click();
  await page.evaluate(() => (window as any).__resolveLateMicrophone?.());
  await expect.poll(() => page.evaluate(() => (window as any).__lateTracksStopped)).toBe(1);
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('ptp-v2-expedition') || '{}'));
  expect(saved.events).toHaveLength(0);
  expect(browserErrors).toEqual([]);
});


test('unconfigured private family service shows an honest disabled state, not invented leaderboard',async ({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Expedition'}).first().click();
  const section=page.getByRole('region',{name:'Family expedition'});
  await expect(section.getByRole('heading',{name:'Private groups unavailable'})).toBeVisible();
  await expect(section).toContainText('Your own map and XP remain on this device.');
  await expect(section.locator('.family-scoreboard')).toHaveCount(0);
  await expect(section.getByRole('button',{name:'Sign in'})).toHaveCount(0);
  await page.screenshot({path:'test-results/family-disabled-expedition.png',fullPage:true});
});


test('backup restore refuses quota errors without losing current browser progress',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await page.getByRole('button',{name:/Reveal meaning/}).click();
  await page.getByRole('button',{name:/Got it/}).click();
  await page.getByRole('button',{name:/My progress|Profile/}).last().click();
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export full backup'}).click();
  const bytes=await readFile(await (await download).path());
  const keys=['ptp-v2-personal-lessons','ptp-v2-progress','ptp-v2-review-schedule',
    'ptp-v2-reading-position','ptp-v2-expedition','ptp-v2-last-lesson'];
  const original=await page.evaluate(keys=>keys.map(k=>[k,localStorage.getItem(k)]),keys);
  await page.evaluate(()=>{
    const setter=Storage.prototype.setItem;
    let failed=false;
    Storage.prototype.setItem=function(key:string,value:string){
      if(key==='ptp-v2-expedition'&&!failed){
        failed=true;throw new DOMException('Quota exceeded','QuotaExceededError');
      }
      return setter.call(this,key,value);
    };
  });
  page.once('dialog',dialog=>dialog.accept());
  await page.locator('input[aria-label="Restore from backup"]').setInputFiles({
    name:'valid-backup.json',mimeType:'application/json',buffer:bytes
  });
  await expect(page.getByRole('alert')).toContainText('previous saved data was preserved');
  await expect(page.getByText(/Backup restored:/)).toHaveCount(0);
  const after=await page.evaluate(keys=>keys.map(k=>[k,localStorage.getItem(k)]),keys);
  expect(after).toEqual(original);
  await page.reload();
  await page.getByRole('button',{name:/My progress|Profile/}).last().click();
  await expect(page.getByRole('region',{name:'Your learning XP'})).toContainText('10');
  // The quota error occurred only once; the same, verified backup can be retried.
  page.once('dialog',dialog=>dialog.accept());
  await page.locator('input[aria-label="Restore from backup"]').setInputFiles({
    name:'valid-backup.json',mimeType:'application/json',buffer:bytes
  });
  await expect(page.getByText(/Backup restored:/)).toBeVisible();
});


test('offline completion persists exactly once across reconnect and allows deliberate retry',async({page,context})=>{
  await page.goto('/');
  await page.evaluate(async()=>{await navigator.serviceWorker.ready;});
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  // Follow the proven offline readiness gate: cache the actual lesson pack
  // before disconnecting. A registered worker alone is not proof of readiness.
  await page.getByRole('button',{name:/Download for offline/}).click();
  await expect(page.getByText('Offline ready',{exact:false})).toBeVisible({timeout:30000});
  await page.waitForFunction(()=>!!navigator.serviceWorker.controller);
  await page.getByRole('button',{name:/Reveal meaning/}).click();
  await page.getByRole('button',{name:/Got it/}).click();
  await page.waitForFunction(()=>{
    const state=JSON.parse(localStorage.getItem('ptp-v2-expedition')||'{}');
    return state.events?.length===1;
  });
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByText('Real progress.')).toBeVisible();
  // A returning learner sees "Continue learning", not "Explore lessons".
  // Use stable primary navigation to visit a different existing item.
  await page.getByRole('button',{name:'Library',exact:true}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await page.getByRole('button',{name:'Skip to next →'}).click();
  await page.getByRole('button',{name:/Reveal meaning/}).click();
  await page.getByRole('button',{name:/Got it/}).click();
  await page.waitForFunction(()=>{
    const state=JSON.parse(localStorage.getItem('ptp-v2-expedition')||'{}');
    return state.events?.length===2;
  });
  const before=await page.evaluate(()=>({
    xp:JSON.parse(localStorage.getItem('ptp-v2-expedition')||'{}'),
    reviews:JSON.parse(localStorage.getItem('ptp-v2-review-schedule')||'{}'),
    progress:JSON.parse(localStorage.getItem('ptp-v2-progress')||'{}'),
  }));
  expect(before.xp.events).toHaveLength(2);
  expect(Object.values(before.reviews)).toHaveLength(2);
  await context.setOffline(false);
  await page.reload();
  const after=await page.evaluate(()=>({
    xp:JSON.parse(localStorage.getItem('ptp-v2-expedition')||'{}'),
    reviews:JSON.parse(localStorage.getItem('ptp-v2-review-schedule')||'{}'),
    progress:JSON.parse(localStorage.getItem('ptp-v2-progress')||'{}'),
  }));
  expect(after).toEqual(before); // No reconnect replay, synthetic sync or bonus XP.
  await page.getByRole('button',{name:'Library',exact:true}).first().click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await page.getByRole('button',{name:/Reveal meaning/}).click();
  await page.getByRole('button',{name:/Got it/}).click();
  const repeated=await page.evaluate(()=>({
    xp:JSON.parse(localStorage.getItem('ptp-v2-expedition')||'{}'),
    reviews:JSON.parse(localStorage.getItem('ptp-v2-review-schedule')||'{}'),
  }));
  expect(repeated.xp.events).toHaveLength(2); // Already awarded for that item/mode/day.
  const firstId=before.xp.events[0].itemId;
  expect(repeated.reviews[firstId].attempts).toBe(before.reviews[firstId].attempts+1);
});

test('bad JSON and forged backup records preserve all current local practice without confirmation',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await page.getByRole('button',{name:/Reveal meaning/}).click();
  await page.getByRole('button',{name:/Got it/}).click();
  await page.getByRole('button',{name:/My progress|Profile/}).last().click();
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export full backup'}).click();
  const original=JSON.parse((await readFile(await (await download).path())).toString('utf8'));
  const keys=['ptp-v2-personal-lessons','ptp-v2-progress','ptp-v2-review-schedule',
    'ptp-v2-reading-position','ptp-v2-expedition','ptp-v2-last-lesson'];
  const before=await page.evaluate(keys=>keys.map(key=>[key,localStorage.getItem(key)]),keys);
  const corrupted=[
    '{invalid json',
    JSON.stringify({...original,version:999}),
    JSON.stringify({...original,reviews:{'forged:0':{streak:-1,attempts:2,
      lastReviewedAt:'2026-01-01T00:00:00Z',dueAt:'invalid'}}}),
    JSON.stringify({...original,expedition:{...original.expedition,selectedRegion:'fabricated'}}),
    JSON.stringify({...original,expedition:{...original.expedition,
      events:[...original.expedition.events,original.expedition.events[0]]}}),
  ];
  for(const [index,bad] of corrupted.entries()){
    await page.locator('input[aria-label="Restore from backup"]').setInputFiles({
      name:'bad-backup-'+index+'.json',mimeType:'application/json',buffer:Buffer.from(bad)
    });
    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page.getByText(/Backup restored:/)).toHaveCount(0);
    expect(await page.evaluate(keys=>keys.map(key=>[key,localStorage.getItem(key)]),keys)).toEqual(before);
  }
  await page.reload();
  expect(await page.evaluate(keys=>keys.map(key=>[key,localStorage.getItem(key)]),keys)).toEqual(before);
  await page.getByRole('button',{name:/My progress|Profile/}).last().click();
  await expect(page.getByRole('region',{name:'Your learning XP'})).toContainText('10');
});
