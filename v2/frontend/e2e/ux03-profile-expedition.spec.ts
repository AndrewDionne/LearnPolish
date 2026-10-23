import {expect,test} from '@playwright/test';

test('Profile, Expedition and Groups prioritize actions rather than repeat-use explanations',async({page,isMobile})=>{
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Profile',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Your profile.'})).toBeVisible();
  await expect(page.getByRole('region',{name:'Learner account'}).getByRole('heading',{name:'Account'})).toBeVisible();
  await expect(page.getByRole('region',{name:'Your learning XP'})).toBeVisible();
  await expect(page.locator('.xp-note')).toHaveCount(0);
  await expect(page.locator('.page-title p')).toHaveCount(0);
  await expect(page.getByText(/Learning progress on this page stays in this browser/)).toBeVisible();

  await nav.getByRole('button',{name:'Expedition',exact:true}).click();
  const map=page.getByRole('region',{name:'Open Poland expedition map'});
  await expect(map.getByRole('heading',{name:'Poland map'})).toBeVisible();
  await expect(map.locator('path[role="button"]')).toHaveCount(16);
  await expect(map.locator('.expedition-progress small')).toHaveCount(0);
  await expect(page.locator('.page-title p')).toHaveCount(0);
  await map.getByRole('button',{name:'Małopolskie'}).click();
  await expect(map.getByRole('heading',{name:'Małopolskie'})).toBeVisible();
  await expect(map.getByRole('progressbar',{name:'Małopolskie unlock progress'})).toBeVisible();

  await page.getByRole('button',{name:/Learning groups & scoreboards/}).click();
  await expect(page.getByRole('heading',{name:'Learning groups.'})).toBeVisible();
  const family=page.getByRole('region',{name:'Family expedition'});
  await expect(family.getByRole('heading',{name:'Learning groups'})).toBeVisible();
  await expect(family.getByText(/Private groups are unavailable/)).toBeVisible();
  await expect(page.locator('.page-title p')).toHaveCount(0);
  await page.getByRole('button',{name:/Back to Poland map/}).click();
  await expect(map.getByRole('heading',{name:'Poland map'})).toBeVisible();
});

test('Region progress is live and local data still distinct from family XP',async({page,isMobile})=>{
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Expedition',exact:true}).click();
  const map=page.getByRole('region',{name:'Open Poland expedition map'});
  await map.getByLabel('Explore another region').selectOption('pomorskie');
  await expect(map.getByRole('heading',{name:'Pomorskie'})).toBeVisible();
  await expect(map.getByText(/Your personal XP and map are saved locally/)).toBeVisible();
  await page.reload();
  await nav.getByRole('button',{name:'Expedition',exact:true}).click();
  await expect(map.getByRole('heading',{name:'Pomorskie'})).toBeVisible();
  await expect(map.getByRole('progressbar',{name:'Pomorskie unlock progress'})).toHaveAttribute('aria-valuenow','0');
});
