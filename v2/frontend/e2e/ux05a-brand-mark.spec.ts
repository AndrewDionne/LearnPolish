import {expect,test} from '@playwright/test';

test('p-route identity shares one vector shape across desktop and compact mobile chrome',async({page,isMobile})=>{
  await page.goto('/');
  const sidebarMark=page.locator('.sidebar .brand-symbol .brand-mark');
  const mobileMark=page.locator('.topbar .mobile-brand .brand-mark');

  await expect(page.locator('.sidebar .brand-symbol')).not.toContainText('p.');
  await expect(page.locator('.sidebar .brand-name')).toHaveText('path to polish');
  await expect(sidebarMark.locator('path')).toHaveCount(3);
  await expect(sidebarMark.locator('circle')).toHaveCount(2);
  await expect(mobileMark.locator('path')).toHaveCount(3);
  await expect(mobileMark.locator('circle')).toHaveCount(2);
  if(isMobile){
    await expect(mobileMark).toBeVisible();
    await expect(sidebarMark).toBeHidden();
    const box=await mobileMark.boundingBox();
    expect(box?.width).toBeGreaterThanOrEqual(28);
    expect(box?.height).toBeGreaterThanOrEqual(28);
    await page.getByRole('navigation',{name:'Mobile navigation'}).getByRole('button',{name:'Library'}).click();
    await expect(mobileMark).toBeVisible();
  }else{
    await expect(sidebarMark).toBeVisible();
    await expect(mobileMark).toBeHidden();
    await expect(page.getByRole('button',{name:/path to polish/i})).toBeVisible();
    await page.getByRole('button',{name:/path to polish/i}).click();
    await expect(page.getByRole('heading',{name:/Small steps/})).toBeVisible();
  }
});

test('brand favicon is resolvable and remains legible without an icon font',async({page})=>{
  await page.goto('/');
  const icon=page.locator('link[rel="icon"][type="image/svg+xml"]');
  await expect(icon).toHaveCount(1);
  const path=await icon.getAttribute('href');
  expect(path).toMatch(/brand-mark\.svg$/);
  const response=await page.request.get(new URL(path!,page.url()).toString());
  expect(response.ok()).toBe(true);
  expect(response.headers()['content-type']).toContain('image/svg+xml');
  const body=await response.text();
  expect(body).toContain('viewBox="0 0 64 64"');
  expect(body).toContain('M17 16v38');
  expect((body.match(/<circle /g)||[])).toHaveLength(2);
});

test('320px header retains a path icon and does not introduce horizontal overflow',async({page})=>{
  await page.setViewportSize({width:320,height:700});
  await page.goto('/');
  await expect(page.locator('.topbar .mobile-brand svg')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  await page.getByRole('navigation',{name:'Mobile navigation'}).getByRole('button',{name:'Expedition'}).click();
  await expect(page.locator('.topbar .mobile-brand svg')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
});
