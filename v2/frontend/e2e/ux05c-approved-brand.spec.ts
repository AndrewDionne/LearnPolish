import {expect,test} from '@playwright/test';

test('approved geometric P is the one-tile identity on desktop and mobile',async({page,isMobile})=>{
  await page.goto('/');
  const sidebarMark=page.locator('.sidebar .brand-symbol .brand-mark');
  const mobileMark=page.locator('.topbar .mobile-brand .brand-mark');

  await expect(page.locator('.sidebar .brand-symbol')).not.toContainText('p.');
  await expect(page.locator('.sidebar .brand-name')).toHaveText('path to polish');
  for(const mark of [sidebarMark,mobileMark]){
    await expect(mark).toHaveAttribute('viewBox','0 0 256 256');
    await expect(mark.locator('rect')).toHaveCount(1);
    await expect(mark.locator('path')).toHaveCount(1);
    await expect(mark.locator('circle')).toHaveCount(1);
    await expect(mark.locator('path')).toHaveAttribute('d',
      'M55 35 H129 C178 35 218 62 218 100 C218 146 179 164 127 164 H88 V197 H185 V221 H55 V164 H35 V139 H55 Z M88 62 V139 H124 C165 139 185 128 185 101 C185 75 166 62 124 62 Z');
    await expect(mark.locator('circle')).toHaveAttribute('fill','#72D5BB');
  }

  if(isMobile){
    await expect(mobileMark).toBeVisible();
    await expect(sidebarMark).toBeHidden();
    const box=await mobileMark.boundingBox();
    expect(box?.width).toBeGreaterThanOrEqual(28);
    expect(box?.height).toBeGreaterThanOrEqual(28);
    await page.getByRole('navigation',{name:'Mobile navigation'})
      .getByRole('button',{name:'Library'}).click();
    await expect(mobileMark).toBeVisible();
  }else{
    await expect(sidebarMark).toBeVisible();
    await expect(mobileMark).toBeHidden();
    const homeBrand=page.getByRole('button',{name:/path to polish/i});
    await expect(homeBrand).toBeVisible();
    await homeBrand.click();
    await expect(page.getByRole('heading',{name:/Small steps/})).toBeVisible();
  }
});

test('cache-busted favicon and approved primary signature both load as SVGs',async({page})=>{
  await page.goto('/');
  const icon=page.locator('link[rel="icon"][type="image/svg+xml"]');
  await expect(icon).toHaveCount(1);
  const path=await icon.getAttribute('href');
  expect(path).toMatch(/brand-mark\.svg\?v=geometric-p$/);
  const response=await page.request.get(new URL(path!,page.url()).toString());
  expect(response.ok()).toBe(true);
  expect(response.headers()['content-type']).toContain('image/svg+xml');
  const body=await response.text();
  expect(body).toContain('viewBox="0 0 256 256"');
  expect(body).toContain('M55 35 H129 C178 35');
  expect(body).toContain('cx="209" cy="209" r="12"');
  expect((body.match(/<circle /g)||[])).toHaveLength(1);

  const signature=await page.request.get(new URL('path-to-polish-signature.svg',page.url()).toString());
  expect(signature.ok()).toBe(true);
  const signatureSvg=await signature.text();
  expect(signatureSvg).toContain('viewBox="0 0 1480 370"');
  expect(signatureSvg).toContain('>Path to Polish</text>');
  expect(signatureSvg).toContain('cx="1403" cy="312"');
});

test('320px header preserves branded mark, navigation and no horizontal overflow',async({page})=>{
  await page.setViewportSize({width:320,height:700});
  await page.goto('/');
  const mobileMark=page.locator('.topbar .mobile-brand svg');
  await expect(mobileMark).toBeVisible();
  await expect(mobileMark.locator('circle')).toHaveCount(1);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  await page.getByRole('navigation',{name:'Mobile navigation'}).getByRole('button',{name:'Expedition'}).click();
  await expect(mobileMark).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
});
