import {expect,test} from '@playwright/test';

test('lesson editor uses shared field labels, borders and touch sizes without changing authoring',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('button',{name:/Create lesson/}).click();
  const panel=page.locator('.author-panel');
  await expect(panel).toBeVisible();
  await expect(page.getByRole('textbox',{name:'Lesson name'})).toBeVisible();
  await expect(page.getByRole('textbox',{name:'Polish text'})).toBeVisible();
  await expect(page.getByRole('textbox',{name:'English meaning'})).toBeVisible();
  const theme=await page.evaluate(()=>{
    const root=getComputedStyle(document.documentElement);
    const input=getComputedStyle(document.querySelector<HTMLElement>('.author-panel input')!);
    const label=getComputedStyle(document.querySelector<HTMLElement>('.author-panel label')!);
    return {fieldRadius:root.getPropertyValue('--ptp-field-radius').trim(),
      fieldBorder:root.getPropertyValue('--ptp-field-border').trim(),
      fieldText:root.getPropertyValue('--ptp-form-text-size').trim(),
      labelSize:root.getPropertyValue('--ptp-form-label-size').trim(),
      inputRadius:input.borderTopLeftRadius,inputFont:input.fontSize,labelFont:label.fontSize};
  });
  expect(theme).toEqual({fieldRadius:'9px',fieldBorder:'#bcd6d1',fieldText:'14px',
    labelSize:'12px',inputRadius:'9px',inputFont:'14px',labelFont:'12px'});
  for(const selector of ['.author-panel input','.author-panel select','.author-panel textarea']){
    const count=await page.locator(selector).count();
    if(count){
      const font=await page.locator(selector).first().evaluate(el=>getComputedStyle(el).fontSize);
      expect(font).toBe('14px');
    }
  }
  const input=page.getByRole('textbox',{name:'Lesson name'});
  await input.focus();
  expect(await input.evaluate(el=>getComputedStyle(el).outlineStyle)).toBe('solid');
  await input.fill('Design system sample');
  await page.getByRole('textbox',{name:'Polish text'}).fill('Dzień dobry');
  await page.getByRole('textbox',{name:'English meaning'}).fill('Good morning');
  await expect(page.getByRole('button',{name:/Create lesson/}).last()).toBeEnabled();
  await page.getByRole('button',{name:/Create lesson/}).last().click();
  await expect(page.getByText('Design system sample',{exact:true}).first()).toBeVisible();
});

test('320px author form preserves fields and actions with no offscreen controls',async({page})=>{
  await page.setViewportSize({width:320,height:720});
  await page.goto('/');
  await page.getByRole('navigation',{name:'Mobile navigation'}).getByRole('button',{name:'Library'}).click();
  await page.getByRole('button',{name:/Create lesson/}).click();
  for(const name of ['Lesson name','Polish text','English meaning']){
    const el=page.getByRole('textbox',{name});
    await expect(el).toBeVisible();
    const rect=await el.boundingBox();
    expect(rect?.width).toBeGreaterThan(100);
    expect(rect?.x).toBeGreaterThanOrEqual(0);
    expect((rect?.x??0)+(rect?.width??0)).toBeLessThanOrEqual(322);
  }
  await expect(page.getByRole('button',{name:/Cancel and return/})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
});

test('signed-out profile keeps account and group boundary without invented fields',async({page,isMobile})=>{
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Profile'}).click();
  await expect(page.getByRole('region',{name:'Learner account'})).toBeVisible();
  await expect(page.getByText(/Learning progress on this page stays in this browser/)).toBeVisible();
  await expect(page.getByRole('textbox',{name:'Display name'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:/Learning groups & scoreboards/})).toBeVisible();
});
