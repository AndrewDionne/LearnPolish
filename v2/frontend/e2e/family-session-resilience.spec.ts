import {test,expect} from '@playwright/test';

// These are isolated private-API fixtures, never public profile/scoreboard data.
test.skip(!process.env.VITE_FAMILY_API_URL,'Requires the private connected browser CI lane');
const json=(data:unknown,status=200)=>({status,contentType:'application/json',body:JSON.stringify(data)});
const groups=[{id:1,name:'Study Group A',can_invite:true},{id:2,name:'Study Group B',can_invite:true}];
const summary=(id:number)=>({
  group:groups[id-1],members:[{id:9,name:id===1?'Member A':'Member B',
    weekly_xp:id===1?100:20,active_days:2,highest_tier:2,team_xp:10}],
  totals:{weekly_xp:id===1?100:20,regions_unlocked:0},regions:[],
  recognition:{improvement:'pending_validated_evidence'}
});
async function seed(page:import('@playwright/test').Page,activeGroup=1){
  await page.goto('/');
  await page.evaluate(id=>{
    sessionStorage.setItem('ptp-v2-family-session','test-group-session');
    sessionStorage.setItem('ptp-v2-family-group',String(id));
    sessionStorage.setItem('ptp-v2-family-sharing','yes');
  },activeGroup);
  await page.reload();
  await page.getByRole('button',{name:'Expedition'}).first().click();
  return page.getByRole('region',{name:'Family expedition'});
}

test('a delayed summary from Group A cannot overwrite Group B or restart sharing',async({page})=>{
  let releaseA:()=>void=()=>{};
  const heldA=new Promise<void>(resolve=>{releaseA=resolve;});
  await page.route('**/api/v2/family/me',route=>route.fulfill(json({
    user:{id:9,name:'Learner'},families:groups
  })));
  await page.route('**/api/v2/family/groups/*/summary',async route=>{
    const id=Number(new URL(route.request().url()).pathname.split('/').at(-2));
    if(id===1)await heldA;
    await route.fulfill(json(summary(id)));
  });
  const panel=await seed(page);
  const selected=panel.getByLabel('Choose family group');
  await expect(selected.locator('option')).toHaveCount(3);
  await selected.selectOption('2');
  await expect(panel.getByText('20 weekly family XP')).toBeVisible();
  await expect(panel.getByRole('list',{name:'Effort leaderboard'})).toContainText('Member B');
  await expect(panel.getByRole('checkbox',{name:/Contribute my/})).not.toBeChecked();
  const lateA=page.waitForResponse('**/api/v2/family/groups/1/summary');
  releaseA();await lateA;
  await expect(panel.getByText('100 weekly family XP')).toHaveCount(0);
  await expect(panel.getByRole('list',{name:'Effort leaderboard'})).not.toContainText('Member A');
  const storage=await page.evaluate(()=>({
    group:sessionStorage.getItem('ptp-v2-family-group'),
    sharing:sessionStorage.getItem('ptp-v2-family-sharing')
  }));
  expect(storage).toEqual({group:'2',sharing:null});
});

test('a delayed summary cannot repopulate rankings after sign out',async({page})=>{
  let release:()=>void=()=>{};
  const held=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/v2/family/me',route=>route.fulfill(json({
    user:{id:9,name:'Learner'},families:groups
  })));
  await page.route('**/api/v2/family/groups/1/summary',async route=>{
    await held;await route.fulfill(json(summary(1)));
  });
  await page.route('**/api/v2/family/logout',route=>route.fulfill(json({ok:true})));
  const panel=await seed(page);
  await expect(panel.getByLabel('Choose family group').locator('option')).toHaveCount(3);
  await panel.getByRole('button',{name:'Sign out'}).click();
  await expect(panel.getByRole('button',{name:'Sign in',exact:true})).toBeVisible();
  const late=page.waitForResponse('**/api/v2/family/groups/1/summary');
  release();await late;
  await expect(panel.getByText('100 weekly family XP')).toHaveCount(0);
  await expect(panel.getByRole('checkbox',{name:/Contribute my/})).toHaveCount(0);
  expect(await page.evaluate(()=>sessionStorage.getItem('ptp-v2-family-session'))).toBeNull();
});

test('expired private session clears scoreboard and refuses cached sharing',async({page})=>{
  let rejectAccount:()=>void=()=>{};
  const held=new Promise<void>(resolve=>{rejectAccount=resolve;});
  await page.route('**/api/v2/family/me',async route=>{
    await held;await route.fulfill(json({error:'unauthorized'},401));
  });
  await page.route('**/api/v2/family/groups/1/summary',route=>route.fulfill(json(summary(1))));
  const panel=await seed(page);
  await expect(panel.getByText('100 weekly family XP')).toBeVisible();
  const meResponse=page.waitForResponse('**/api/v2/family/me');
  rejectAccount();await meResponse;
  await expect(panel.getByText('Session expired — sign in again.')).toBeVisible();
  await expect(panel.getByText('100 weekly family XP')).toHaveCount(0);
  await expect(panel.getByRole('checkbox',{name:/Contribute my/})).toHaveCount(0);
  const storage=await page.evaluate(()=>({
    token:sessionStorage.getItem('ptp-v2-family-session'),
    group:sessionStorage.getItem('ptp-v2-family-group'),
    sharing:sessionStorage.getItem('ptp-v2-family-sharing')
  }));
  expect(storage.token).toBeNull();
  expect(storage.group).toBeNull();
  expect(storage.sharing).not.toBe('yes');
});

test('late group-creation response cannot change group chosen while creating',async({page})=>{
  let release:()=>void=()=>{};
  const held=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/v2/family/me',route=>route.fulfill(json({
    user:{id:9,name:'Learner'},families:groups
  })));
  await page.route('**/api/v2/family/groups/*/summary',route=>{
    const id=Number(new URL(route.request().url()).pathname.split('/').at(-2));
    return route.fulfill(json(summary(id)));
  });
  await page.route('**/api/v2/family/groups',async route=>{
    await held;await route.fulfill(json({id:3,name:'Late group',can_invite:true}));
  });
  const panel=await seed(page);
  const selector=panel.getByLabel('Choose family group');
  await expect(panel.getByText('100 weekly family XP')).toBeVisible();
  await panel.locator('summary').filter({hasText:'Manage learning groups and invitations'}).click();
  await panel.getByLabel('New family group').fill('Late group');
  const sent=page.waitForRequest('**/api/v2/family/groups');
  await panel.getByRole('button',{name:'Create group'}).click();
  await sent;
  await selector.selectOption('2');
  await expect(panel.getByText('20 weekly family XP')).toBeVisible();
  const late=page.waitForResponse('**/api/v2/family/groups');
  release();await late;
  await expect(selector).toHaveValue('2');
  await expect(panel.getByText('20 weekly family XP')).toBeVisible();
  await expect(panel.getByText('Late group')).toHaveCount(0);
});

test('temporary identity verification failure hides private state without pretending logout',async({page})=>{
  let releaseAccount:()=>void=()=>{};
  const held=new Promise<void>(resolve=>{releaseAccount=resolve;});
  await page.route('**/api/v2/family/me',async route=>{
    await held;await route.fulfill(json({error:'service_unavailable'},503));
  });
  await page.route('**/api/v2/family/groups/1/summary',route=>route.fulfill(json(summary(1))));
  const panel=await seed(page);
  await expect(panel.getByText('100 weekly family XP')).toBeVisible();
  const late=page.waitForResponse('**/api/v2/family/me');
  releaseAccount();await late;
  await expect(panel.getByText('Unable to verify your account. Refresh the page or sign in again.')).toBeVisible();
  await expect(panel.getByText('100 weekly family XP')).toHaveCount(0);
  await expect(panel.getByLabel('Choose family group')).toHaveValue('0');
  await expect(panel.getByRole('checkbox',{name:/Contribute my/})).toHaveCount(0);
  const stored=await page.evaluate(()=>({
    token:sessionStorage.getItem('ptp-v2-family-session'),
    group:sessionStorage.getItem('ptp-v2-family-group'),
    sharing:sessionStorage.getItem('ptp-v2-family-sharing')
  }));
  expect(stored.token).toBe('test-group-session'); // Temporary outage does not revoke server session.
  expect(stored.group).toBeNull();
  expect(stored.sharing).toBeNull();
});
