import {test,expect} from '@playwright/test';
import {existsSync,readFileSync} from 'node:fs';

async function verificationCode(email:string):Promise<string>{
  const outbox=process.env.PTP_CI_VERIFICATION_OUTBOX;
  if(!outbox)throw new Error('Private CI verification outbox not configured');
  let code='';
  await expect.poll(()=>{
    if(!existsSync(outbox))return '';
    const lines=readFileSync(outbox,'utf8').trim().split('\n');
    for(const line of lines.reverse()){
      try{const entry=JSON.parse(line) as {email:string;code:string};
        if(entry.email===email){code=entry.code;return code;}}
      catch{/* concurrent partial write; retry */}
    }
    return '';
  },{timeout:10000}).not.toBe('');
  return code;
}

// The isolated connected job sets this value and starts a local family API.
test.skip(!process.env.VITE_FAMILY_API_URL, 'Requires the backend-enabled family integration job');

test('two real private sessions join a family, choose different regions and share weekly XP', async ({browser},testInfo)=>{
  const projectTag=testInfo.project.name.replace(/[^a-z0-9]/gi,'').toLowerCase()+'r'+testInfo.retry;
  const first=await browser.newContext();
  const second=await browser.newContext();
  try{
    const parent=await first.newPage();
    await parent.goto('/');
    await parent.getByRole('button',{name:'Expedition'}).first().click();
    const panel=parent.getByRole('region',{name:'Family expedition'});
    await expect(panel.getByRole('button',{name:'Create account'})).toBeVisible();
    await panel.getByLabel('Display name').fill('Explorer A');
    await panel.getByLabel('Email').fill('explorera+'+projectTag+'@example.test');
    await panel.getByLabel('Password').fill('Secure-family-passphrase-2026');
    await panel.getByRole('button',{name:'Create account'}).click();
    await expect(panel.getByRole('heading',{name:'Verify your email'})).toBeVisible();
    await panel.getByLabel('Verification code').fill(
      await verificationCode('explorera+'+projectTag+'@example.test'));
    await panel.getByRole('button',{name:'Verify email'}).click();
    await expect(panel.getByRole('button',{name:'Create group'})).toBeVisible();
    await panel.getByLabel('New family group').fill('Weekend explorers');
    await panel.getByRole('button',{name:'Create group'}).click();
    await expect(panel.getByRole('heading',{name:'Weekend explorers'})).toBeVisible();
    await panel.getByRole('button',{name:'Create one-use family invite'}).click();
    const invitation=await panel.locator('.family-invite code').textContent();
    expect(invitation?.length).toBeGreaterThan(25);
    await panel.getByRole('checkbox',{name:/Contribute my/}).check();
    // Delayed writes expose the former race: screen snapshot may load before credit commits.
    await parent.route('**/api/v2/family/groups/*/activity',async route=>{
      await new Promise(resolve=>setTimeout(resolve,450));
      await route.continue();
    });
    await parent.getByLabel('Explore another region').selectOption('pomorskie');
    await parent.getByRole('button',{name:'Library'}).first().click();
    await parent.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
    await parent.getByRole('button',{name:/Greetings and Introductions/}).click();
    await parent.getByRole('button',{name:/Reveal meaning/}).click();
    await parent.getByRole('button',{name:/Got it/}).click();
    await parent.getByRole('button',{name:'Expedition'}).first().click();
    await expect(panel.getByText('Practice contributed to your family.')).toBeVisible();
    await expect(panel.getByText('10 weekly family XP')).toBeVisible({timeout:10000});
    // Server acknowledges work before React refreshes the family summary.
    await expect(parent.getByRole('progressbar',{name:'Pomorskie unlock progress'})).toHaveAttribute('aria-valuenow','10');
    await expect(panel.getByText('pomorskie')).toBeVisible();

    const learner=await second.newPage();
    await learner.goto('/');
    await learner.getByRole('button',{name:'Expedition'}).first().click();
    const lp=learner.getByRole('region',{name:'Family expedition'});
    await lp.getByLabel('Display name').fill('Explorer B');
    await lp.getByLabel('Email').fill('explorerb+'+projectTag+'@example.test');
    await lp.getByLabel('Password').fill('Secure-family-passphrase-2026');
    await lp.getByRole('button',{name:'Create account'}).click();
    await expect(lp.getByRole('heading',{name:'Verify your email'})).toBeVisible();
    await lp.getByLabel('Verification code').fill(
      await verificationCode('explorerb+'+projectTag+'@example.test'));
    await lp.getByRole('button',{name:'Verify email'}).click();
    await lp.getByLabel('Private invitation code').fill(invitation!);
    await lp.getByRole('button',{name:'Join family'}).click();
    await expect(lp.getByRole('heading',{name:'Weekend explorers'})).toBeVisible();
    await lp.getByRole('checkbox',{name:/Contribute my/}).check();
    await learner.getByLabel('Explore another region').selectOption('małopolskie');
    await learner.getByRole('button',{name:'Library'}).first().click();
    await learner.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
    await learner.getByRole('button',{name:/Greetings and Introductions/}).click();
    await learner.getByRole('button',{name:/Reveal meaning/}).click();
    await learner.getByRole('button',{name:/Got it/}).click();
    await learner.getByRole('button',{name:'Expedition'}).first().click();
    await expect(lp.getByText('Practice contributed to your family.')).toBeVisible();
    await expect(lp.getByText('20 weekly family XP')).toBeVisible({timeout:10000});
    await expect(lp.getByText('pomorskie')).toBeVisible();
    await expect(lp.getByText('małopolskie')).toBeVisible();
    await expect(learner.getByRole('button',{name:'Family Map'})).toHaveAttribute('aria-pressed','true');
    await expect(learner.getByRole('progressbar',{name:'Małopolskie unlock progress'})).toHaveAttribute('aria-valuenow','10');
    await expect(lp.getByRole('listitem')).toHaveCount(2);
    const board=lp.getByRole('group',{name:'Weekly recognition category'});
    await expect(lp.getByRole('list',{name:'Effort leaderboard'})).toBeVisible();
    await expect(lp.getByRole('button',{name:'Create group'})).not.toBeVisible();
    await board.getByRole('button',{name:'Consistency'}).click();
    await expect(lp.getByRole('list',{name:'Consistency leaderboard'})).toContainText('1 day');
    await board.getByRole('button',{name:'Trailblazer'}).click();
    await expect(lp.getByRole('list',{name:'Trailblazer leaderboard'})).toContainText('Tier 1');
    await board.getByRole('button',{name:'Team contribution'}).click();
    await expect(lp.getByRole('list',{name:'Team contribution leaderboard'})).toContainText('10 map XP');
    await board.getByRole('button',{name:'Most improved'}).click();
    await expect(lp.getByRole('status').filter({hasText:'no validated improvement measurements'})).toBeVisible();
    await board.getByRole('button',{name:'Effort'}).click();
    // Exercise the real backend from profile edit to reflected private group ranking.
    await learner.getByRole('button',{name:'Profile'}).first().click();
    const myProfile=learner.getByRole('region',{name:'Learner account'});
    await expect(myProfile.getByLabel('Display name')).toHaveValue('Explorer B');
    await myProfile.getByLabel('Display name').fill('Explorer B updated');
    await myProfile.getByRole('button',{name:'Save display name'}).click();
    await expect(myProfile.getByText('Display name updated for your learning groups.')).toBeVisible();
    await myProfile.getByRole('button',{name:/Learning groups & scoreboards/}).click();
    await expect(learner.getByRole('heading',{name:'Learning groups'})).toBeVisible();
    await expect(learner.getByRole('heading',{name:/Your Poland expedition/})).toHaveCount(0);
    await expect(lp.getByRole('list',{name:'Effort leaderboard'}))
      .toContainText('Explorer B updated (you)');
    // Returned group selection and explicit contribution permission are retained.
    await expect(lp.getByRole('checkbox',{name:/Contribute my/})).toBeChecked();
    await learner.screenshot({path:'test-results/family-connected-leaderboard.png',fullPage:true});
    // One-use invitation was consumed. It cannot grant access to a third account.
    const learnerToken=await learner.evaluate(()=>sessionStorage.getItem('ptp-v2-family-session'));
    const replay=await learner.request.post('http://127.0.0.1:8016/api/v2/family/invites/redeem',
      {headers:{Authorization:'Bearer '+learnerToken},data:{code:invitation}});
    expect(replay.status()).toBe(400);
    // Member withdrawal controls work in a connected family UI.
    const learnerPrivacy=lp.getByTestId('family-privacy');
    await learnerPrivacy.locator('summary').click();
    learner.once('dialog',dialog=>dialog.accept());
    await learnerPrivacy.getByRole('button',{name:'Leave this family'}).click();
    await expect(lp.getByRole('heading',{name:'Weekend explorers'})).toHaveCount(0);
    await panel.getByRole('button',{name:'Refresh rankings'}).click();
    await expect(panel.getByText('10 weekly family XP')).toBeVisible();
    const parentPrivacy=panel.getByTestId('family-privacy');
    await parentPrivacy.locator('summary').click();
    await expect(parentPrivacy.getByRole('button',{name:'Revoke unused invitations'})).toBeVisible();
  }finally{
    await first.close();await second.close();
  }
});


test('family sign-in offers an email-code recovery journey only when delivery is available', async ({page})=>{
  let issued=false;
  let reset=false;
  await page.route('**/api/v2/family/health',route=>route.fulfill({
    status:200,contentType:'application/json',body:JSON.stringify({
      ok:true,version:1,catalog_items:2,password_recovery_available:true
    })
  }));
  await page.route('**/api/v2/family/recovery/request',async route=>{
    const body=route.request().postDataJSON() as {email:string};
    expect(body.email).toBe('parent@example.test');
    issued=true;
    await route.fulfill({status:202,contentType:'application/json',body:'{"accepted":true}'});
  });
  await page.route('**/api/v2/family/recovery/complete',async route=>{
    const body=route.request().postDataJSON() as {code:string;new_password:string};
    expect(body.code).toBe('A'.repeat(43));
    expect(body.new_password).toBe('renewed-secure-passphrase-2026');
    expect(route.request().url()).not.toContain(body.code);
    reset=true;
    await route.fulfill({status:200,contentType:'application/json',
      body:'{"reset":true,"sign_in_again":true}'});
  });
  await page.goto('/');
  await page.getByRole('button',{name:'Expedition'}).first().click();
  const panel=page.getByRole('region',{name:'Family expedition'});
  await panel.getByRole('button',{name:'Forgot password?'}).click();
  await panel.getByLabel('Email').fill('parent@example.test');
  await panel.getByRole('button',{name:'Email recovery code'}).click();
  await expect(panel.getByText(/If an account exists/)).toBeVisible();
  expect(issued).toBe(true);
  await panel.getByLabel('Recovery code').fill('A'.repeat(43));
  await panel.getByLabel('New password').fill('renewed-secure-passphrase-2026');
  await panel.getByRole('button',{name:'Set new password'}).click();
  expect(reset).toBe(true);
  await expect(panel.getByRole('button',{name:'Sign in'})).toBeVisible();
  await expect(panel.getByText('Password reset. Sign in with your new password.')).toBeVisible();
  await page.screenshot({path:'test-results/family-recovery.png',fullPage:true});
});

test('unconfigured verification delivery blocks new family signup',async ({page})=>{
  await page.route('**/api/v2/family/health',route=>route.fulfill({
    status:200,contentType:'application/json',
    body:JSON.stringify({ok:true,password_recovery_available:false,email_verification_available:false})
  }));
  await page.goto('/');
  await page.getByRole('button',{name:'Expedition'}).first().click();
  const panel=page.getByRole('region',{name:'Family expedition'});
  await expect(panel.getByRole('button',{name:'Create account'})).toBeDisabled();
  await expect(panel.getByText(/accounts are unavailable until secure verification/)).toBeVisible();
});
