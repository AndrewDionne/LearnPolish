import {expect,test} from '@playwright/test';

test('primary, secondary and import actions share the same touch and typography scale',async({page,isMobile})=>{
  await page.goto('/');
  const metrics=async(selector:string)=>page.locator(selector).first().evaluate(el=>{
    const css=getComputedStyle(el);
    const rect=el.getBoundingClientRect();
    return {height:rect.height,font:css.fontSize,radius:css.borderTopLeftRadius,
      minHeight:css.minHeight,display:css.display,color:css.color};
  });
  const primary=await metrics('.hero-button');
  expect(primary.height).toBeGreaterThanOrEqual(44);
  expect(primary.font).toBe('13px');
  expect(primary.radius).toBe('11px');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  const secondary=await metrics('.library-author-actions .secondary-action');
  const imported=await metrics('.library-author-actions .import-button');
  for(const style of [secondary,imported]){
    expect(style.height).toBeGreaterThanOrEqual(44);
    expect(style.font).toBe(primary.font);
    expect(style.radius).toBe(primary.radius);
    expect(style.minHeight).toBe('44px');
  }
  await expect(page.getByRole('button',{name:/Create lesson/})).toBeVisible();
  await expect(page.locator('input[aria-label="Import lesson JSON"]')).toHaveCount(1);

  const rootTokens=await page.evaluate(()=>{
    const t=getComputedStyle(document.documentElement);
    return ['--ptp-font-body','--ptp-font-display','--ptp-primary','--ptp-focus',
      '--ptp-border','--ptp-page-title','--ptp-target-size'].map(name=>[name,t.getPropertyValue(name).trim()]);
  });
  expect(rootTokens.every(([,value])=>Boolean(value))).toBe(true);
  if(isMobile){
    const nav=page.getByRole('navigation',{name:'Mobile navigation'});
    await expect(nav.getByRole('button',{name:'Library'})).toHaveAttribute('aria-current','page');
  }
});

test('Profile, family and expedition share surface tokens without hiding account or map actions',async({page,isMobile})=>{
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Profile',exact:true}).click();
  const profile=page.locator('.learner-profile');
  const boxStyle=async(selector:string)=>page.locator(selector).first().evaluate(el=>{
    const css=getComputedStyle(el);return {bg:css.backgroundColor,border:css.borderTopColor,radius:css.borderTopLeftRadius};
  });
  const expected=await boxStyle('.learner-profile');
  expect(expected).toEqual({bg:'rgb(255, 255, 255)',border:'rgb(220, 233, 229)',radius:'16px'});
  await nav.getByRole('button',{name:'Expedition',exact:true}).click();
  expect(await boxStyle('.expedition-panel')).toEqual(expected);
  await page.getByRole('button',{name:/Learning groups & scoreboards/}).click();
  expect(await boxStyle('.family-panel')).toEqual(expected);
  await expect(page.getByRole('heading',{name:'Learning groups.'})).toBeVisible();
});

test('320px keeps heading hierarchy, accessible controls and approved geometric P',async({page})=>{
  await page.setViewportSize({width:320,height:720});
  await page.goto('/');
  await expect(page.locator('.mobile-brand .brand-mark')).toBeVisible();
  await expect(page.locator('.mobile-brand .brand-mark circle')).toHaveCount(1);
  const nav=page.getByRole('navigation',{name:'Mobile navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  const headings=await page.locator('.page-title h1,.curriculum-stage-heading h2').evaluateAll(els=>
    els.map(el=>({tag:el.tagName,font:parseFloat(getComputedStyle(el).fontSize)})));
  expect(headings.some(x=>x.tag==='H1')).toBe(true);
  expect(headings.some(x=>x.tag==='H2')).toBe(true);
  expect(Math.max(...headings.filter(x=>x.tag==='H1').map(x=>x.font)))
    .toBeGreaterThan(Math.max(...headings.filter(x=>x.tag==='H2').map(x=>x.font)));
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(322);
  await expect(page.getByRole('button',{name:/Create lesson/})).toBeVisible();
  const secondary=page.getByRole('button',{name:/Create lesson/});
  const bounds=await secondary.boundingBox();
  expect(bounds?.height).toBeGreaterThanOrEqual(44);
});
