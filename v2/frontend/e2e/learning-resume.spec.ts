import {expect,test} from '@playwright/test';

test('Home Continue finds the first new expression after reload while Library still opens normally',async({page,isMobile})=>{
  const errors:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  for(const expected of ['Dzień dobry','Dobry wieczór']){
    await expect(page.getByText(expected,{exact:true})).toBeVisible();
    await page.getByRole('button',{name:/Reveal meaning/}).click();
    await page.getByRole('button',{name:/Got it/}).click();
  }
  await expect(page.getByText('Cześć',{exact:true})).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Home',exact:true}).click();
  const resume=page.locator('.resume-card');
  await expect(resume).toContainText('2 of');
  await expect(resume).toContainText('Next: item 3');
  await page.reload();
  await expect(page.getByRole('button',{name:'Continue course'})).toBeVisible();
  await page.getByRole('button',{name:'Continue course'}).click();
  await expect(page.getByText('Cześć',{exact:true})).toBeVisible();
  await expect(page.locator('.item-count')).toContainText('3');

  // Opening a lesson from the Library is a separate, deliberate fresh session,
  // not an implicit skip based on previous Learn records.
  await nav.getByRole('button',{name:'Library',exact:true}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await expect(page.getByText('Dzień dobry',{exact:true})).toBeVisible();
  await expect(page.locator('.item-count')).toContainText('1');
  expect(errors).toEqual([]);
});

test('Home Continue respects the approved Numbers 1–10 then 11–20 sections',async({page,isMobile})=>{
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('numbers 1-20');
  await page.getByRole('button',{name:/numbers 1-20/i}).click();
  for(let i=0;i<10;i++){
    await page.getByRole('button',{name:/Reveal meaning/}).click();
    await page.getByRole('button',{name:/Got it/}).click();
  }
  await expect(page.getByRole('heading',{name:'Nicely done!'})).toBeVisible();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Home',exact:true}).click();
  await expect(page.locator('.resume-card')).toContainText('Next: item 11');
  await page.locator('.resume-card').click();
  await expect(page.getByRole('combobox',{name:'Practice group'})).toHaveValue('1');
  await expect(page.locator('.item-count')).toContainText('1');
  await expect(page.getByText('Jedenaście',{exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});
