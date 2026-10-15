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
