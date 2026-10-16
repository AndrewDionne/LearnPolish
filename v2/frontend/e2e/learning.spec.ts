import { readFile } from 'node:fs/promises';
import { expect, test } from '@playwright/test';

test('Home to library to Learn and progress survives reload', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByText('Real progress.')).toBeVisible();
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await expect(page.getByRole('heading', { name: /Lesson library/ })).toBeVisible();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Dzień dobry');
  await expect(page.getByText('Conversation 1', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Conversation 1/ }).click();
  await expect(page.getByText('Dzień dobry', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Reveal meaning/ }).click();
  await expect(page.getByText('Good morning / Good day')).toBeVisible();
  await page.getByRole('button', { name: /Got it/ }).click();
  await expect(page.getByText('Dobry wieczór', { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Library' }).first().click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Conversation');
  await expect(page.getByText('1 practised', { exact: false }).first()).toBeVisible();
  expect(errors).toEqual([]);
});

test('responsive mobile library and lesson controls', async ({ page, isMobile }) => {
  if (!isMobile) test.skip();
  await page.goto('/');
  await page.getByRole('navigation', { name: 'Mobile navigation' }).getByRole('button', { name: 'Library' }).click();
  await expect(page.getByRole('heading', { name: /Lesson library/ })).toBeVisible();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('numbers 1-20');
  await page.getByRole('button', { name: /numbers 1-20/i }).click();
  await expect(page.getByText('Jeden', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Reveal meaning/ }).click();
  await expect(page.getByText('One', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Got it/ }).click();
  await expect(page.getByText('Dwa', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/mobile-learn.png', fullPage: true });
});

test('create, edit, export, import and delete a personal lesson without deploying', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.getByRole('button', { name: /Create lesson/ }).click();
  await page.getByRole('textbox', { name: 'Lesson name' }).fill('At the bakery');
  await page.getByRole('textbox', { name: 'Polish text' }).fill('Poproszę chleb');
  await page.getByRole('textbox', { name: 'English meaning' }).fill('Bread, please');
  await page.getByRole('button', { name: /Create lesson/ }).click();
  await expect(page.getByText('Poproszę chleb', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Edit lesson' }).click();
  await page.getByRole('textbox', { name: 'Lesson name' }).fill('At the Polish bakery');
  await page.getByRole('textbox', { name: 'English meaning' }).fill('A loaf of bread, please');
  await page.getByRole('button', { name: /Save changes/ }).click();
  await expect(page.getByText('At the Polish bakery', { exact: true }).first()).toBeVisible();

  const exportStarted = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export JSON' }).click();
  const exported = await exportStarted;
  expect(exported.suggestedFilename()).toMatch(/personal_.*\.json/);

  await page.reload();
  await page.getByRole('button', { name: 'Library' }).first().click();
  await expect(page.getByText('At the Polish bakery', { exact: true })).toBeVisible();

  const imported = {
    schemaVersion: 1, id: 'old-portable-id', title: 'Imported lesson',
    kind: 'vocabulary', source: 'personal',
    items: [{ id: 'one', polish: 'Dziękuję', english: 'Thank you', audio: 'https://untrusted.example/audio.mp3' }],
  };
  await page.locator('input[aria-label="Import lesson JSON"]').setInputFiles({
    name: 'import.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(imported)),
  });
  await expect(page.getByText('Imported lesson', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Imported lesson/ }).click();
  await expect(page.getByText('Dziękuję', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /No audio/ })).toBeDisabled();

  page.on('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByText('Imported lesson', { exact: true })).toHaveCount(0);
});


test('Read resumes a saved passage and Listen reveals content only after answering', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Basic 01R');
  await page.getByRole('button', { name: /Basic 01R/ }).click();
  await expect(page.getByText('Cześć! Jak się masz?', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Read' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: /Skip to next/ }).click();
  await expect(page.getByText('Dziękuję, mam się dobrze.', { exact: true })).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: 'Library' }).first().click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Basic 01R');
  await page.getByRole('button', { name: /Basic 01R/ }).click();
  await expect(page.getByText('Dziękuję, mam się dobrze.', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Listen', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Listen', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('Cześć! Jak się masz?', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: '0.75×' }).click();
  await expect(page.getByRole('button', { name: '0.75×' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('group', { name: /Choose the meaning|Answer the listening question/ }).getByRole('button').first().click();
  await expect(page.getByText('POLISH TRANSCRIPT', { exact: true })).toBeVisible();
  await expect(page.getByText('Cześć! Jak się masz?', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /Continue/ }).click();
  await expect(page.getByText('What did you hear?')).toBeVisible();
  await expect(page.getByText('Dziękuję, mam się dobrze.', { exact: true })).toHaveCount(0);
  await page.screenshot({ path: 'test-results/listen-practice.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('Listen is unavailable when personal lessons have no trusted audio', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.getByRole('button', { name: /Create lesson/ }).click();
  await page.getByRole('textbox', { name: 'Lesson name' }).fill('No audio yet');
  await page.getByRole('textbox', { name: 'Polish text' }).fill('Jabłko');
  await page.getByRole('textbox', { name: 'English meaning' }).fill('Apple');
  await page.getByRole('button', { name: /Create lesson/ }).click();
  await expect(page.getByRole('button', { name: 'Listen', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'No audio' })).toBeDisabled();
});


test('offline lesson pack is confirmed only after caching and supports an offline reload', async ({ page, context }) => {
  await page.goto('/');
  await page.evaluate(async () => {
    if (!('serviceWorker' in navigator)) throw new Error('Service workers unavailable');
    await navigator.serviceWorker.ready;
  });
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Conversation 1');
  await page.getByRole('button', { name: /Conversation 1/ }).click();
  await page.getByRole('button', { name: /Download for offline/ }).click();
  await expect(page.getByText('Offline ready', { exact: false })).toBeVisible({ timeout: 30000 });
  const storedAudio = await page.evaluate(async () => {
    const cache = await caches.open('ptp-v2-lesson-audio-v1');
    return (await cache.keys()).length;
  });
  expect(storedAudio).toBeGreaterThan(0);
  // The worker may be installed/ready before clients.claim() controls this tab.
  // Wait for control before disconnecting the network.
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  await context.setOffline(true);
  const before = await page.evaluate(async () => {
    const keys = await caches.keys();
    try {
      const response = await fetch('/');
      return { cacheNames: keys, fetchOk: response.ok, status: response.status, controlled: !!navigator.serviceWorker.controller };
    } catch (error) { return { cacheNames: keys, fetchError: String(error), controlled: !!navigator.serviceWorker.controller }; }
  });
  console.log('OFFLINE PRE-RELOAD:', JSON.stringify(before));
  await page.reload();
  const after = await page.evaluate(async () => {
    let cacheInfo = [];
    try { cacheInfo = await caches.keys(); } catch { /* browser error page */ }
    return { href: location.href, title: document.title, body: document.body?.innerText.slice(0, 700), controlled: !!navigator.serviceWorker?.controller, cacheInfo };
  }).catch(error => ({ error: String(error) }));
  console.log('OFFLINE POST-RELOAD:', JSON.stringify(after));
  await expect(page.getByText('Real progress.')).toBeVisible();
  await page.getByRole('button', { name: 'Library' }).first().click();
  await page.getByRole('searchbox', { name: 'Search lessons' }).fill('Conversation 1');
  await page.getByRole('button', { name: /Conversation 1/ }).click();
  await expect(page.getByText('Offline ready', { exact: false })).toBeVisible();
  await expect(page.getByText('Dzień dobry', { exact: true })).toBeVisible();
  await context.setOffline(false);
  await page.getByRole('button', { name: 'Remove offline copy' }).click();
  await expect(page.getByRole('button', { name: /Download for offline/ })).toBeVisible();
});


test('Speak records, checks acoustic quality, replays locally, and clears on next phrase', async ({ page }) => {
  await page.addInitScript(() => {
    const length = 16000;
    const bytes = new ArrayBuffer(44 + length * 2);
    const view = new DataView(bytes);
    for (const [pos, chars] of [[0,'RIFF'], [8,'WAVE'], [12,'fmt '], [36,'data']] as const) {
      for (let i = 0; i < chars.length; i++) view.setUint8(pos + i, chars.charCodeAt(i));
    }
    view.setUint32(4, bytes.byteLength - 8, true);
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true);
    view.setUint32(40, length * 2, true);
    for (let i = 0; i < length; i++) view.setInt16(44 + 2 * i, Math.round(5000 * Math.sin(i * .23)), true);
    (window as any).__microphoneTrackStops = 0;
    const fakeStream = {getTracks: () => [{stop: () => { (window as any).__microphoneTrackStops++; }}]};
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      configurable: true, value: async () => fakeStream,
    });
    class MockRecorder {
      static isTypeSupported(_: string) { return true; }
      mimeType = 'audio/wav';
      state = 'inactive';
      ondataavailable: ((event: {data: Blob}) => void) | null = null;
      onstop: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(_stream: unknown, _options?: unknown) {}
      start() { this.state = 'recording'; }
      stop() {
        this.state = 'inactive';
        queueMicrotask(() => {
          this.ondataavailable?.({data: new Blob([bytes], {type: 'audio/wav'})});
          this.onstop?.();
        });
      }
    }
    Object.defineProperty(window, 'MediaRecorder', {configurable: true, value: MockRecorder});
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Explore lessons'}).click();
  await page.getByRole('searchbox', {name: 'Search lessons'}).fill('Conversation 1');
  await page.getByRole('button', {name: /Conversation 1/}).click();
  await page.getByRole('button', {name: 'Speak', exact: true}).click();
  await expect(page.getByText('Dzień dobry', {exact: true})).toBeVisible();
  await page.getByRole('button', {name: /Start recording/}).click();
  await expect(page.getByRole('button', {name: 'Stop recording'})).toBeVisible();
  await page.getByRole('button', {name: 'Stop recording'}).click();
  await expect(page.getByText(/Recording captured/)).toBeVisible();
  await expect(page.locator('#personal-speech-replay')).toHaveAttribute('src', /blob:/);
  await expect(page.getByText(/Pronunciation is not scored yet/)).toBeVisible();
  await page.getByRole('button', {name: /Next phrase/}).click();
  await expect(page.getByText('Dobry wieczór', {exact: true})).toBeVisible();
  const earned = await page.evaluate(() => JSON.parse(localStorage.getItem('ptp-v2-expedition') || '{}'));
  expect(earned.events.some((entry:{mode:string})=>entry.mode==='speak')).toBe(true);
  await expect(page.locator('#personal-speech-replay')).toHaveCount(0);
  const trackStops = await page.evaluate(() => (window as any).__microphoneTrackStops);
  expect(trackStops).toBeGreaterThan(0);
  await page.screenshot({path: 'test-results/speak-capture.png', fullPage: true});
});

test('Speak handles denied microphone permissions without grading or blocking navigation', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      configurable: true,
      value: async () => { throw new DOMException('Permission denied', 'NotAllowedError'); },
    });
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Explore lessons'}).click();
  await page.getByRole('searchbox', {name: 'Search lessons'}).fill('numbers 1-20');
  await page.getByRole('button', {name: /numbers 1-20/i}).click();
  await page.getByRole('button', {name: 'Speak', exact: true}).click();
  await page.getByRole('button', {name: /Start recording/}).click();
  await expect(page.getByRole('alert')).toContainText('Microphone permission was denied');
  await page.getByRole('button', {name: /Next phrase/}).click();
  await expect(page.getByText('Dwa', {exact: true})).toBeVisible();
});


test('Practice review queue targets only due cards and preserves scheduling after reload', async ({page}) => {
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.setItem('ptp-v2-review-schedule', JSON.stringify({
      'Conversation_1:0': {streak: 0, attempts: 1, lastReviewedAt: '2020-01-01T00:00:00.000Z', dueAt: '2020-01-01T00:00:00.000Z'},
      'Conversation_1:1': {streak: 1, attempts: 1, lastReviewedAt: '2020-01-01T00:00:00.000Z', dueAt: '2099-01-01T00:00:00.000Z'},
    }));
  });
  await page.reload();
  await page.getByRole('button', {name:/Practice/}).first().click();
  await expect(page.getByText('1 due now')).toBeVisible();
  await page.getByRole('button', {name:/Conversation 1.*1 expression.*Review/}).click();
  await expect(page.getByText('Review what matters')).toBeVisible();
  await expect(page.getByText('Dzień dobry', {exact:true})).toBeVisible();
  await page.getByRole('button', {name:/Reveal meaning/}).click();
  await page.getByRole('button', {name:/Got it/}).click();
  await expect(page.getByText('REVIEW COMPLETE', {exact:true})).toBeVisible();
  await page.getByRole('button', {name:'Back to library →', exact:true}).click();
  await page.getByRole('button', {name:/Practice/}).first().click();
  await expect(page.getByText('0 due now')).toBeVisible();
  await page.reload();
  await page.getByRole('button', {name:/Practice/}).first().click();
  await expect(page.getByText('0 due now')).toBeVisible();
});


test('sound lab compares individually sourced MP3 examples, not bundled phrases', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button', { name: 'Explore lessons' }).click();
  await page.locator('.filter-buttons').getByRole('button', { name: 'Polish sounds' }).click();
  await expect(page.getByRole('button', { name: /C · CZ · Ć/ })).toBeVisible();
  await expect(page.getByText('letter recognition', { exact: false })).toHaveCount(0);
  await page.getByRole('button', { name: /C · CZ · Ć/ }).click();
  const lab = page.getByRole('region', { name: 'Compare Polish sounds' });
  await expect(lab).toBeVisible();
  await expect(lab.getByRole('button', { name: 'Play plac' })).toBeVisible();
  await expect(lab.getByRole('button', { name: 'Play Cztery' })).toBeVisible();
  await expect(lab.getByRole('button', { name: 'Play Pięć' })).toBeVisible();
  await lab.getByRole('button', { name: /Cztery/ }).first().click();
  await expect(lab.getByRole('button', { name: /Cztery/ }).first()).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: 'Speak', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Listen', exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/sound-lab.png', fullPage: true });
  expect(errors).toEqual([]);
});


test('full browser-local backup safely restores personal lessons, recall and review dates', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', {name:'Explore lessons'}).click();
  await page.getByRole('button', {name:/Create lesson/}).click();
  await page.getByRole('textbox', {name:'Lesson name'}).fill('Saved Polish lesson');
  await page.getByRole('textbox', {name:'Polish text'}).fill('Świetnie');
  await page.getByRole('textbox', {name:'English meaning'}).fill('Great');
  await page.getByRole('button', {name:/Create lesson/}).click();
  await page.getByRole('button', {name:/Reveal meaning/}).click();
  await page.getByRole('button', {name:/Got it/}).click();
  await page.getByRole('button', {name:/My progress|Profile/}).last().click();
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', {name:'Export full backup'}).click();
  const file = await downloadEvent;
  expect(file.suggestedFilename()).toBe('path-to-polish-v2-backup.json');
  const bytes = await readFile(await file.path());
  const saved = JSON.parse(bytes.toString('utf8'));
  expect(saved.format).toBe('path-to-polish-v2-local-backup');
  expect(saved.personalLessons).toHaveLength(1);
  expect(Object.keys(saved.progress)).toHaveLength(1);
  expect(Object.keys(saved.reviews)).toHaveLength(1);
  expect(bytes.toString('utf8')).not.toContain('audio/webm');

  await page.evaluate(() => {
    for (const key of ['ptp-v2-personal-lessons','ptp-v2-progress','ptp-v2-review-schedule',
       'ptp-v2-reading-position','ptp-v2-last-lesson']) localStorage.removeItem(key);
  });
  await page.reload();
  await page.getByRole('button', {name:/My progress|Profile/}).last().click();
  await expect(page.getByText('0%')).toBeVisible();
  page.once('dialog', dialog => dialog.accept());
  await page.locator('input[aria-label="Restore from backup"]').setInputFiles({
    name:'backup.json', mimeType:'application/json', buffer:bytes,
  });
  await expect(page.getByText(/Backup restored: 1 personal lessons/)).toBeVisible();
  await expect(page.getByText('100%')).toBeVisible();
  await page.reload();
  await page.getByRole('button', {name:'Library'}).first().click();
  await expect(page.getByText('Saved Polish lesson', {exact:true})).toBeVisible();
  await page.getByRole('button', {name:'Practice'}).first().click();
  await expect(page.getByText('0 due now')).toBeVisible();
});


test('XP is awarded for actual Learn/Listen responses, but not a skipped Speak attempt', async ({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Explore lessons'}).click();
 await page.getByRole('searchbox',{name:'Search lessons'}).fill('Conversation 1');
 await page.getByRole('button',{name:/Conversation 1/}).click();
 await page.getByRole('button',{name:/Reveal meaning/}).click();
 await page.getByRole('button',{name:/Got it/}).click();
 await page.getByRole('button',{name:'Listen',exact:true}).click();
 await page.getByRole('group',{name:'Choose the meaning'}).getByRole('button').first().click();
 await page.getByRole('button',{name:'Continue →',exact:true}).click();
 await page.getByRole('button',{name:'Speak',exact:true}).click();
 await page.getByRole('button',{name:/Next phrase/}).click();
 await page.getByRole('button',{name:/My progress|Profile/}).last().click();
 const xp=page.getByRole('region',{name:'Your learning XP'});
 await expect(xp).toContainText('20');
 const state=await page.evaluate(()=>JSON.parse(localStorage.getItem('ptp-v2-expedition')||'{}'));
 expect(state.events.map((e:{mode:string})=>e.mode).sort()).toEqual(['learn','listen']);
 await page.reload();
 await page.getByRole('button',{name:/My progress|Profile/}).last().click();
 await expect(page.getByRole('region',{name:'Your learning XP'})).toContainText('20');
});

test('XP and expedition targets survive full backup and restore; custom weekly goal persists',async ({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Expedition'}).first().click();
 await page.getByLabel('Explore another region').selectOption('podkarpackie');
 await expect(page.getByRole('heading',{name:'Podkarpackie'})).toBeVisible();
 await page.getByRole('button',{name:'Library'}).first().click();
 await page.getByRole('searchbox',{name:'Search lessons'}).fill('Basic 01R');
 await page.getByRole('button',{name:/Basic 01R/}).click();
 await page.getByRole('button',{name:'How are you?',exact:true}).click();
 await page.getByRole('button',{name:'Continue →',exact:true}).click();
 await page.getByRole('button',{name:/My progress|Profile/}).last().click();
 await page.getByLabel('My own goal').check();
 await page.getByRole('spinbutton',{name:'Custom weekly XP goal'}).fill('250');
 await page.getByRole('button',{name:'Save goal'}).click();
 const download=page.waitForEvent('download');
 await page.getByRole('button',{name:'Export full backup'}).click();
 const bytes=await readFile(await (await download).path());
 const data=JSON.parse(bytes.toString());
 expect(data.expedition.events).toHaveLength(1);
 expect(data.expedition.selectedRegion).toBe('podkarpackie');
 expect(data.expedition.selfGoal).toBe(250);
 await page.evaluate(()=>localStorage.removeItem('ptp-v2-expedition'));
 await page.reload();
 await page.getByRole('button',{name:/My progress|Profile/}).last().click();
 page.once('dialog',d=>d.accept());
 await page.locator('input[aria-label="Restore from backup"]').setInputFiles({name:'restore.json',mimeType:'application/json',buffer:bytes});
 await expect(page.getByRole('region',{name:'Your learning XP'})).toContainText('240 XP until your weekly goal');
 await expect(page.getByLabel('My own goal')).toBeChecked();
 await expect(page.getByRole('spinbutton',{name:'Custom weekly XP goal'})).toHaveValue('250');
 await page.getByRole('button',{name:'Expedition'}).first().click();
 await expect(page.getByRole('heading',{name:'Podkarpackie'})).toBeVisible();
 await expect(page.getByRole('progressbar',{name:'Podkarpackie unlock progress'})).toHaveAttribute('aria-valuenow','10');
});

test('completed Read lesson hands off to Listen without leaving the lesson', async ({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Basic 01R');
  await page.getByRole('button',{name:/Basic 01R/}).click();
  for(let i=0;i<5;i++) await page.getByRole('button',{name:/Skip to next/}).click();
  await page.getByRole('button',{name:/Reveal translation without answering/}).click();
  await page.getByRole('button',{name:/Finished reading/}).click();
  await expect(page.getByText('SESSION COMPLETE',{exact:true})).toBeVisible();
  const next=page.getByRole('group',{name:'Continue learning in another mode'});
  await expect(next.getByRole('button',{name:'Listen →'})).toBeVisible();
  await next.getByRole('button',{name:'Listen →'}).click();
  await expect(page.getByRole('button',{name:'Listen',exact:true})).toHaveAttribute('aria-pressed','true');
  await expect(page.getByText('What did you hear?')).toHaveCount(0);
  await expect(page.getByRole('button',{name:/Play audio/})).toBeVisible();
});

test('interactive open map permits distant choice and restores destination on reload',async ({page})=>{
 await page.goto('/');
 await page.getByRole('button',{name:'Expedition'}).first().click();
 const map=page.getByRole('region',{name:'Open Poland expedition map'});
 await expect(map.locator('path[role="button"]')).toHaveCount(16);
 await map.getByRole('button',{name:'Małopolskie'}).click();
 await expect(map.getByRole('heading',{name:'Małopolskie'})).toBeVisible();
 await map.getByLabel('Explore another region').selectOption('pomorskie');
 await page.reload();
 await page.getByRole('button',{name:'Expedition'}).first().click();
 await expect(page.getByRole('heading',{name:'Pomorskie'})).toBeVisible();
 await expect(page.getByText(/Single-learner preview/)).toBeVisible();
 await page.screenshot({path:'test-results/open-poland-expedition.png',fullPage:true});
});

test('late microphone permission after leaving Speak stops tracks and cannot award XP', async ({page}) => {
  await page.addInitScript(() => {
    (window as any).__lateTracksStopped = 0;
    (window as any).__resolveLateMicrophone = null;
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      configurable: true,
      value: () => new Promise(resolve => {
        (window as any).__resolveLateMicrophone = () => resolve({
          getTracks: () => [{stop: () => {(window as any).__lateTracksStopped++;}}],
        });
      }),
    });
  });
  const browserErrors: string[] = [];
  page.on('pageerror', e => browserErrors.push(e.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Conversation 1');
  await page.getByRole('button',{name:/Conversation 1/}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await page.getByRole('button',{name:/Start recording/}).click();
  await expect(page.getByText(/Requesting microphone permission/)).toBeVisible();
  await page.getByRole('button',{name:/Back to library/}).click();
  await page.evaluate(() => (window as any).__resolveLateMicrophone?.());
  await expect.poll(() => page.evaluate(() => (window as any).__lateTracksStopped)).toBe(1);
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem('ptp-v2-expedition') || '{}'));
  expect(saved.events).toHaveLength(0);
  expect(browserErrors).toEqual([]);
});
