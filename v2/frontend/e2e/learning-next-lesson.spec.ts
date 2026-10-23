import {expect,test} from '@playwright/test';

test('completing a built-in lesson offers the next authored step without forcing progression',async({page,isMobile})=>{
  test.setTimeout(90_000);
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  const skip=page.getByRole('button',{name:'Skip to next →'});
  let skipped=0;
  while(await skip.isEnabled()){
    await skip.click();skipped++;
    if(skipped>100)throw new Error('No lesson end was reached');
  }
  await page.getByRole('button',{name:/Reveal meaning/}).click();
  await page.getByRole('button',{name:/Got it/}).click();
  await expect(page.getByRole('heading',{name:'Nicely done!'})).toBeVisible();
  const next=page.getByRole('button',{name:'Continue to Everyday Conversations: Greetings'});
  await expect(next).toBeVisible();
  await expect(page.getByRole('button',{name:'Back to library →'})).toBeVisible();
  await next.click();
  await expect(page.locator('.crumb')).toContainText('Everyday Conversations: Greetings');
  await expect(page.locator('.item-count')).toContainText('1');
  // Return to Library remains an ordinary path; no hard locks.
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Library',exact:true}).click();
  await expect(page.getByRole('heading',{name:/Lesson library/})).toBeVisible();
  expect(errors).toEqual([]);
});

test('Numbers 1–20 completes the approved first section before offering any other lesson',async({page})=>{
  test.setTimeout(90_000);
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('numbers 1-20');
  await page.getByRole('button',{name:/numbers 1-20/i}).click();
  for(let i=0;i<10;i++){
    await page.getByRole('button',{name:/Reveal meaning/}).click();
    await page.getByRole('button',{name:/Got it/}).click();
  }
  await expect(page.getByRole('heading',{name:'Nicely done!'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Continue to Numbers 11–20 →'})).toBeVisible();
  await expect(page.getByRole('button',{name:/Continue to Numbers Beyond 20/})).toHaveCount(0);
  await page.getByRole('button',{name:'Continue to Numbers 11–20 →'}).click();
  await expect(page.getByText('Jedenaście',{exact:true})).toBeVisible();
});
