import {test,expect} from '@playwright/test';

test.skip(!process.env.VITE_FAMILY_API_URL, 'Requires isolated family-connected browser job');
const json=(body:unknown,status=200)=>({status,contentType:'application/json',body:JSON.stringify(body)});
const group={id:9,name:'Household explorers',can_invite:true};
const owner={id:1,name:'Organizer',weekly_xp:10,active_days:1,highest_tier:1,team_xp:10};
const learner={id:2,name:'Learner Two',weekly_xp:19,active_days:1,highest_tier:3,team_xp:19};
const summary=(members:typeof owner[])=>({
  group,members,regions:[{region:'pomorskie',target:300,earned:members.length===2?29:10,unlocked:false}],
  totals:{weekly_xp:members.length===2?29:10,regions_unlocked:0},
  recognition:{improvement:'pending_validated_evidence'}
});

test('organizer removes a member, confirms erasure, and receives updated rankings',async({page})=>{
  let members=[owner,learner];
  let removed=0;
  await page.route('**/api/v2/family/health',route=>route.fulfill(json({
    ok:true,email_verification_available:true,password_recovery_available:true
  })));
  await page.route('**/api/v2/family/login',route=>route.fulfill(json({token:'test-owner-session'})));
  await page.route('**/api/v2/family/me',route=>route.fulfill(json({
    user:{id:1,name:'Organizer'},families:[group]
  })));
  await page.route('**/api/v2/family/groups/9/summary',route=>route.fulfill(json(summary(members))));
  await page.route('**/api/v2/family/groups/9/members/remove',async route=>{
    const data=route.request().postDataJSON() as {member_id:number};
    expect(data.member_id).toBe(2);
    expect(route.request().headers().authorization).toBe('Bearer test-owner-session');
    removed++;
    members=[owner];
    await route.fulfill(json({removed:true,member_id:2,removed_activities:1,revoked_invites:2}));
  });
  await page.goto('/');
  await page.getByRole('button',{name:'Expedition'}).first().click();
  const panel=page.getByRole('region',{name:'Family expedition'});
  await panel.getByRole('button',{name:'Sign in',exact:true}).click();
  await panel.getByLabel('Email').fill('organizer@example.test');
  await panel.getByLabel('Password').fill('private-mock-passphrase');
  await panel.getByRole('button',{name:'Sign in to family'}).click();
  await panel.getByLabel('Choose family group').selectOption('9');
  await expect(panel.getByRole('list',{name:'Effort leaderboard'}).getByRole('listitem')).toHaveCount(2);
  await panel.getByTestId('family-privacy').locator('summary').click();
  await panel.getByLabel('Member to remove').selectOption('2');
  page.once('dialog',dialog=>dialog.accept());
  await panel.getByRole('button',{name:'Remove member and erase shared XP'}).click();
  await expect(panel.getByText('Learner Two removed. 1 shared activities erased; 2 unused invitations revoked.')).toBeVisible();
  await expect(panel.getByRole('list',{name:'Effort leaderboard'}).getByRole('listitem')).toHaveCount(1);
  await expect(panel.getByText('10 weekly family XP')).toBeVisible();
  expect(removed).toBe(1);
  await expect(panel.getByLabel('Member to remove').locator('option')).toHaveCount(1);
});

test('revoked member refresh drops stale group, contribution toggle and shared map',async({page})=>{
  let revoked=false;
  await page.route('**/api/v2/family/me',route=>route.fulfill(json({
    user:{id:2,name:'Learner Two'},families:[group]
  })));
  await page.route('**/api/v2/family/groups/9/summary',route=>{
    if(revoked)return route.fulfill(json({error:'not_found'},404));
    return route.fulfill(json({...summary([owner,learner]),group:{...group,can_invite:false}}));
  });
  await page.goto('/');
  await page.evaluate(()=>{
    sessionStorage.setItem('ptp-v2-family-session','test-learner-session');
    sessionStorage.setItem('ptp-v2-family-group','9');
    sessionStorage.setItem('ptp-v2-family-sharing','yes');
  });
  await page.reload();
  await page.getByRole('button',{name:'Expedition'}).first().click();
  const panel=page.getByRole('region',{name:'Family expedition'});
  await expect(panel.getByText('29 weekly family XP')).toBeVisible();
  revoked=true;
  await panel.getByRole('button',{name:'Refresh rankings'}).click();
  await expect(panel.getByText('Family access has ended. Choose another group.')).toBeVisible();
  await expect(panel.getByLabel('Choose family group')).toHaveValue('0');
  await expect(panel.getByText('29 weekly family XP')).toHaveCount(0);
  await expect(panel.getByRole('checkbox',{name:/Contribute my/})).toHaveCount(0);
  const stored=await page.evaluate(()=>({
    group:sessionStorage.getItem('ptp-v2-family-group'),
    sharing:sessionStorage.getItem('ptp-v2-family-sharing')
  }));
  expect(stored).toEqual({group:null,sharing:null});
});
