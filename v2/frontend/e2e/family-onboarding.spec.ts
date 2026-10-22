import {test,expect} from '@playwright/test';

// This test exercises the private family UI using inert, local-only API fixtures.
// It must not run against the public unconfigured V2 preview.
test.skip(!process.env.VITE_FAMILY_API_URL, 'Requires the isolated connected family browser job');

const json=(value:unknown)=>({status:200,contentType:'application/json',body:JSON.stringify(value)});

test('registration and returning-member sign-in show only the relevant fields',async({page})=>{
  await page.route('**/api/v2/family/health',route=>route.fulfill(json({
    ok:true,password_recovery_available:true,email_verification_available:true
  })));
  await page.goto('/');
  await page.getByRole('button',{name:'Expedition'}).first().click();
  const panel=page.getByRole('region',{name:'Family expedition'});
  await expect(panel.getByLabel('Display name')).toBeVisible();
  await expect(panel.getByRole('button',{name:'Create account'})).toBeVisible();
  await panel.getByRole('button',{name:'Sign in',exact:true}).click();
  await expect(panel.getByLabel('Display name')).toHaveCount(0);
  await expect(panel.getByRole('button',{name:'Sign in to family'})).toBeVisible();
  await panel.getByRole('button',{name:'Create account'}).click();
  await expect(panel.getByLabel('Display name')).toBeVisible();
  await expect(panel.getByRole('button',{name:'Create account'})).toBeVisible();
});

test('an invite never follows a learner into another family, even after a late API reply',async({page})=>{
  await page.route('**/api/v2/family/health',route=>route.fulfill(json({
    ok:true,email_verification_available:true,password_recovery_available:true
  })));
  await page.route('**/api/v2/family/login',route=>route.fulfill(json({token:'isolated-test-session'})));
  const families=[{id:1,name:'Family A',can_invite:true},{id:2,name:'Family B',can_invite:true}];
  await page.route('**/api/v2/family/me',route=>route.fulfill(json({
    families,user:{id:1}
  })));
  await page.route('**/api/v2/family/groups/*/summary',route=>{
    const parts=new URL(route.request().url()).pathname.split('/');
    const id=Number(parts[parts.length-2]);
    const group=families.find(item=>item.id===id);
    if(!group)return route.fulfill({status:404,body:'{}'});
    return route.fulfill(json({group,members:[],regions:[],
      totals:{weekly_xp:0,regions_unlocked:0},recognition:{improvement:'pending'}}));
  });
  let releaseFirst:()=>void=()=>{};
  const firstHeld=new Promise<void>(resolve=>{releaseFirst=resolve;});
  let invitationCount=0;
  await page.route('**/api/v2/family/groups/1/invite',async route=>{
    invitationCount++;
    if(invitationCount===1)await firstHeld;
    await route.fulfill(json({code:'example-private-invitation-code'}));
  });

  await page.goto('/');
  await page.getByRole('button',{name:'Expedition'}).first().click();
  const panel=page.getByRole('region',{name:'Family expedition'});
  await panel.getByRole('button',{name:'Sign in',exact:true}).click();
  await panel.getByLabel('Email').fill('member@example.test');
  await panel.getByLabel('Password').fill('example-only-passphrase');
  await panel.getByRole('button',{name:'Sign in to family'}).click();
  const selector=panel.getByLabel('Choose family group');
  await expect(selector.locator('option')).toHaveCount(3);
  await selector.selectOption('1');
  await expect(panel.getByRole('heading',{name:'Family A'})).toBeVisible();
  const firstRequest=page.waitForRequest('**/api/v2/family/groups/1/invite');
  await panel.getByRole('button',{name:'Create one-use family invite'}).click();
  await firstRequest;
  await selector.selectOption('2');
  releaseFirst();
  await expect(panel.getByRole('heading',{name:'Family B'})).toBeVisible();
  await expect(panel.locator('.family-invite')).toHaveCount(0);
  await selector.selectOption('1');
  await expect(panel.getByRole('heading',{name:'Family A'})).toBeVisible();
  await panel.getByRole('button',{name:'Create one-use family invite'}).click();
  await expect(panel.locator('.family-invite code')).toHaveText('example-private-invitation-code');
  await expect(panel.getByRole('button',{name:'Copy invitation code'})).toBeVisible();
  await selector.selectOption('2');
  await expect(panel.locator('.family-invite')).toHaveCount(0);
});

test('private profile edits display name and shows only joined learning groups',async({page})=>{
  await page.route('**/api/v2/family/health',route=>route.fulfill(json({
    ok:true,email_verification_available:true,password_recovery_available:true
  })));
  await page.route('**/api/v2/family/login',route=>route.fulfill(json({token:'profile-test-session'})));
  let name='Example learner';
  const groups=[{id:7,name:'Polish study team',can_invite:true}];
  await page.route('**/api/v2/family/me',route=>route.fulfill(json({
    user:{id:13,name,email:'learner@example.test'},families:groups
  })));
  await page.route('**/api/v2/family/account/profile',route=>{
    const payload=route.request().postDataJSON() as {name:string};
    expect(route.request().headers().authorization).toBe('Bearer profile-test-session');
    name=payload.name;
    return route.fulfill(json({user:{id:13,name,email:'learner@example.test'}}));
  });
  await page.route('**/api/v2/family/groups/7/summary',route=>route.fulfill(json({
    group:groups[0],members:[{id:13,name,weekly_xp:10,active_days:1,highest_tier:1,team_xp:10}],
    regions:[],totals:{weekly_xp:10,regions_unlocked:0},
    recognition:{improvement:'pending_validated_evidence'}
  })));

  await page.goto('/');
  await page.getByRole('button',{name:'Expedition'}).first().click();
  const panel=page.getByRole('region',{name:'Family expedition'});
  await panel.getByRole('button',{name:'Sign in',exact:true}).click();
  await panel.getByLabel('Email').fill('learner@example.test');
  await panel.getByLabel('Password').fill('example-only-passphrase');
  await panel.getByRole('button',{name:'Sign in to family'}).click();
  await page.getByRole('button',{name:'Profile'}).first().click();
  const profile=page.getByRole('region',{name:'Learner account'});
  await expect(profile.getByLabel('Account email')).toHaveValue('learner@example.test');
  await expect(profile.getByText('1 learning group')).toBeVisible();
  await expect(profile.getByRole('list',{name:'Joined learning groups'}))
    .toContainText('Polish study team');
  await profile.getByLabel('Display name').fill('Confident beginner');
  await profile.getByRole('button',{name:'Save display name'}).click();
  await expect(profile.getByText('Display name updated for your learning groups.')).toBeVisible();
  await profile.getByRole('button',{name:/Learning groups & scoreboards/}).click();
  await expect(page.getByRole('heading',{name:'Learning groups'})).toBeVisible();
  await expect(page.getByRole('heading',{name:/Your Poland expedition/})).toHaveCount(0);
  const groupTop=await page.getByRole('heading',{name:'Learning groups'})
    .evaluate(element=>element.getBoundingClientRect().top);
  expect(groupTop).toBeGreaterThanOrEqual(0);
  expect(groupTop).toBeLessThan(300); // New destination is actually in view, not merely in DOM.
  await expect(page.getByRole('button',{name:'Expedition'}).first()).toHaveAttribute('aria-current','page');
  await panel.getByLabel('Choose family group').selectOption('7');
  await expect(panel.getByRole('heading',{name:'Polish study team'})).toBeVisible();
  await expect(panel.getByRole('list',{name:'Effort leaderboard'}))
    .toContainText('Confident beginner (you)');
  await expect(panel.getByText('Group scoreboards · 1 learner · current group only')).toBeVisible();
  await page.getByRole('button',{name:'Back to Poland map'}).click();
  await expect(page.getByRole('heading',{name:/Your Poland expedition/})).toBeVisible();
  await page.getByRole('button',{name:/Learning groups & scoreboards/}).first().click();
  await expect(page.getByRole('heading',{name:'Learning groups'})).toBeVisible();
});
