import {test,expect} from '@playwright/test';

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
    await expect(panel.getByRole('button',{name:'Create group'})).toBeVisible();
    await panel.getByLabel('New family group').fill('Weekend explorers');
    await panel.getByRole('button',{name:'Create group'}).click();
    await expect(panel.getByRole('heading',{name:'Weekend explorers'})).toBeVisible();
    await panel.getByRole('button',{name:'Create one-use family invite'}).click();
    const invitation=await panel.locator('.family-invite code').textContent();
    expect(invitation?.length).toBeGreaterThan(25);
    await panel.getByRole('checkbox',{name:/Contribute my/}).check();
    await parent.getByLabel('Explore another region').selectOption('pomorskie');
    await parent.getByRole('button',{name:'Library'}).first().click();
    await parent.getByRole('searchbox',{name:'Search lessons'}).fill('Conversation 1');
    await parent.getByRole('button',{name:/Conversation 1/}).click();
    await parent.getByRole('button',{name:/Reveal meaning/}).click();
    await parent.getByRole('button',{name:/Got it/}).click();
    await parent.getByRole('button',{name:'Expedition'}).first().click();
    await expect(panel.getByText('Practice contributed to your family.')).toBeVisible();
    await panel.getByRole('button',{name:'Refresh rankings'}).click();
    await expect(panel.getByText('10 weekly family XP')).toBeVisible();
    await expect(panel.getByText('pomorskie')).toBeVisible();

    const learner=await second.newPage();
    await learner.goto('/');
    await learner.getByRole('button',{name:'Expedition'}).first().click();
    const lp=learner.getByRole('region',{name:'Family expedition'});
    await lp.getByLabel('Display name').fill('Explorer B');
    await lp.getByLabel('Email').fill('explorerb+'+projectTag+'@example.test');
    await lp.getByLabel('Password').fill('Secure-family-passphrase-2026');
    await lp.getByRole('button',{name:'Create account'}).click();
    await lp.getByLabel('Private invitation code').fill(invitation!);
    await lp.getByRole('button',{name:'Join family'}).click();
    await expect(lp.getByRole('heading',{name:'Weekend explorers'})).toBeVisible();
    await lp.getByRole('checkbox',{name:/Contribute my/}).check();
    await learner.getByLabel('Explore another region').selectOption('małopolskie');
    await learner.getByRole('button',{name:'Library'}).first().click();
    await learner.getByRole('searchbox',{name:'Search lessons'}).fill('Conversation 1');
    await learner.getByRole('button',{name:/Conversation 1/}).click();
    await learner.getByRole('button',{name:/Reveal meaning/}).click();
    await learner.getByRole('button',{name:/Got it/}).click();
    await learner.getByRole('button',{name:'Expedition'}).first().click();
    await expect(lp.getByText('Practice contributed to your family.')).toBeVisible();
    await lp.getByRole('button',{name:'Refresh rankings'}).click();
    await expect(lp.getByText('20 weekly family XP')).toBeVisible();
    await expect(lp.getByText('pomorskie')).toBeVisible();
    await expect(lp.getByText('małopolskie')).toBeVisible();
    await expect(learner.getByRole('button',{name:'Family Map'})).toHaveAttribute('aria-pressed','true');
    await expect(learner.getByRole('progressbar',{name:'Małopolskie unlock progress'})).toHaveAttribute('aria-valuenow','10');
    await expect(lp.getByRole('listitem')).toHaveCount(2);
    await learner.screenshot({path:'test-results/family-connected-leaderboard.png',fullPage:true});
    // One-use invitation was consumed. It cannot grant access to a third account.
    const learnerToken=await learner.evaluate(()=>sessionStorage.getItem('ptp-v2-family-session'));
    const replay=await learner.request.post('http://127.0.0.1:8016/api/v2/family/invites/redeem',
      {headers:{Authorization:'Bearer '+learnerToken},data:{code:invitation}});
    expect(replay.status()).toBe(400);
  }finally{
    await first.close();await second.close();
  }
});
