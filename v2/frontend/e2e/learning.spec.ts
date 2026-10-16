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
  await page.getByRole('group', { name: 'Choose the meaning' }).getByRole('button').first().click();
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
  await page.getByRole('button', {name:'Practice', exact:true}).first().click();
  await expect(page.getByText('1 due now')).toBeVisible();
  await page.getByRole('button', {name:/Conversation 1.*1 expression.*Review/}).click();
  await expect(page.getByText('Review what matters')).toBeVisible();
  await expect(page.getByText('Dzień dobry', {exact:true})).toBeVisible();
  await page.getByRole('button', {name:/Reveal meaning/}).click();
  await page.getByRole('button', {name:/Got it/}).click();
  await expect(page.getByText('REVIEW COMPLETE', {exact:true})).toBeVisible();
  await page.getByRole('button', {name:/Back to library/}).click();
  await page.getByRole('button', {name:'Practice', exact:true}).first().click();
  await expect(page.getByText('0 due now')).toBeVisible();
  await page.reload();
  await page.getByRole('button', {name:'Practice', exact:true}).first().click();
  await expect(page.getByText('0 due now')).toBeVisible();
});
