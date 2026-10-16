import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

async function audit(page: Page, label: string) {
  const results = await new AxeBuilder({page})
    .withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa'])
    .analyze();
  const serious = results.violations
    .filter(v => v.impact === 'serious' || v.impact === 'critical')
    .map(v => v.id + ' (' + v.impact + '): ' + v.nodes.slice(0, 6).map(n => n.target.join(' ')).join(', '));
  expect(serious, 'WCAG issues on ' + label).toEqual([]);
  const metrics = await page.evaluate(() => {
    const width = window.innerWidth;
    const overflow = Math.round(document.documentElement.scrollWidth - width);
    const clippedControls = [...document.querySelectorAll<HTMLElement>('button,a,input,textarea,select')]
      .filter(el => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 &&
          rect.height > 0 && (rect.right > width + 2 || rect.left < -2);
      }).map(el => el.tagName.toLowerCase() + ':' + (el.getAttribute('aria-label') || el.textContent?.trim().slice(0, 40)));
    return {overflow, clippedControls};
  });
  expect(metrics.overflow, 'Document width overflow on ' + label).toBeLessThanOrEqual(2);
  expect(metrics.clippedControls, 'Off-viewport interactive controls on ' + label).toEqual([]);
  await page.screenshot({path:'test-results/audit-' + label + '.png', fullPage:true});
}

test('Home, Library and Profile pass synthetic WCAG and responsive geometry audit', async ({page}) => {
  test.setTimeout(90_000);
  const pageErrors: string[] = [];
  page.on('pageerror', e => pageErrors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('link', {name:'Skip to main content'})).toBeAttached();
  await audit(page,'home');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await audit(page,'library');
  await page.getByRole('button',{name:/My progress|Profile/}).last().click();
  await audit(page,'profile');
  expect(pageErrors).toEqual([]);
});

test('Learn, Listen and Sound Lab satisfy the baseline semantic audit', async ({page}) => {
  test.setTimeout(90_000);
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Conversation 1');
  await page.getByRole('button',{name:/Conversation 1/}).click();
  await audit(page,'learn');
  await page.getByRole('button',{name:'Listen',exact:true}).click();
  await audit(page,'listen');
  await page.getByRole('button',{name:/Back to library/}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('C · CZ');
  await page.getByRole('button',{name:/C · CZ · Ć/}).click();
  await audit(page,'sounds');
});

test('Speak and authoring meet keyboard and layout audit', async ({page}) => {
  test.setTimeout(90_000);
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('button',{name:/Create lesson/}).click();
  await audit(page,'editor');
  await page.getByRole('button',{name:/Cancel and return/}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('numbers 1-20');
  await page.getByRole('button',{name:/numbers 1-20/i}).click();
  await page.getByRole('button',{name:'Speak',exact:true}).click();
  await audit(page,'speak');
});

test('Compact 320px keyboard nav, language, and minimum interactive surface checks', async ({page}) => {
  test.setTimeout(90_000);
  await page.setViewportSize({width:320,height:720});
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link',{name:'Skip to main content'})).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
  await audit(page,'compact-home');
  await page.getByRole('navigation',{name:'Mobile navigation'}).getByRole('button',{name:'Library'}).click();
  await audit(page,'compact-library');
  await page.getByRole('button',{name:/Create lesson/}).click();
  await audit(page,'compact-editor');
  await page.getByRole('button',{name:/Cancel and return/}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('C · CZ');
  await page.getByRole('button',{name:/C · CZ · Ć/}).click();
  await audit(page,'compact-sound-lab');
  const controls = page.locator('.contrast-play');
  for(const button of await controls.all()) {
    const bbox = await button.boundingBox();
    expect(bbox?.width, 'sound playback touch target width').toBeGreaterThanOrEqual(44);
    expect(bbox?.height, 'sound playback touch target height').toBeGreaterThanOrEqual(44);
  }
});
