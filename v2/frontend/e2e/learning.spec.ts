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
