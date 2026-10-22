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
  // Record the actual screenshot and geometry even when a WCAG check fails.
  // This creates durable CI evidence for diagnosis rather than a blank artifact.
  const wcagErrors = serious;
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
  console.log('AUDIT ' + label + ': ' + JSON.stringify({wcag:wcagErrors,metrics}));
  await page.screenshot({path:'test-results/audit-' + label + '.png', fullPage:true});
  expect(wcagErrors, 'WCAG issues on ' + label).toEqual([]);
  expect(metrics.overflow, 'Document width overflow on ' + label).toBeLessThanOrEqual(2);
  expect(metrics.clippedControls, 'Off-viewport interactive controls on ' + label).toEqual([]);
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
  await page.getByRole('button',{name:/Learning groups & scoreboards/}).click();
  await expect(page.getByRole('heading',{name:'Learning groups'})).toBeVisible();
  await expect(page.getByRole('heading',{name:/Your Poland expedition/})).toHaveCount(0);
  await audit(page,'groups');
  expect(pageErrors).toEqual([]);
});

test('Learn, Listen and Sound Lab satisfy the baseline semantic audit', async ({page}) => {
  test.setTimeout(90_000);
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).click();
  await audit(page,'learn');
  await page.getByRole('button',{name:'Listen',exact:true}).click();
  await audit(page,'listen');
  await page.getByRole('button',{name:/Back to library/}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('C, CZ');
  await page.getByRole('button',{name:/C, CZ and Ć/}).click();
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
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('C, CZ');
  await page.getByRole('button',{name:/C, CZ and Ć/}).click();
  await audit(page,'compact-sound-lab');
  const controls = page.locator('.contrast-play');
  for(const button of await controls.all()) {
    const bbox = await button.boundingBox();
    expect(bbox?.width, 'sound playback touch target width').toBeGreaterThanOrEqual(44);
    expect(bbox?.height, 'sound playback touch target height').toBeGreaterThanOrEqual(44);
  }
});


test('Read, due review and Poland Expedition pass synthetic accessibility, focus and geometry',async({page,isMobile})=>{
  test.setTimeout(90_000);
  const pageErrors:string[]=[];
  page.on('pageerror',error=>pageErrors.push(error.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Explore lessons'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Everyday Conversations: Greetings');
  await page.getByRole('button',{name:/Everyday Conversations: Greetings/}).click();
  await expect(page.getByRole('button',{name:'Read',exact:true})).toHaveAttribute('aria-pressed','true');
  await audit(page,'reading-passage');
  await page.getByRole('button',{name:'Skip to next →'}).click();
  await audit(page,'reading-next-passage');
  await page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'})
    .getByRole('button',{name:'Practice',exact:true}).click();
  await page.evaluate(()=>{
    localStorage.setItem('ptp-v2-review-schedule',JSON.stringify({
      'Conversation_1:0':{streak:0,attempts:1,lastReviewedAt:'2020-01-01T00:00:00.000Z',
        dueAt:'2020-01-01T00:00:00.000Z'},
    }));
  });
  await page.reload();
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  await nav.getByRole('button',{name:'Practice',exact:true}).click();
  await expect(page.getByText('1 due now')).toBeVisible();
  await audit(page,'practice-due');
  await page.getByRole('button',{name:/Greetings and Introductions.*1 expression.*Review/}).click();
  await expect(page.getByText('Review what matters')).toBeVisible();
  await audit(page,'practice-single-review');
  await page.getByRole('button',{name:/Reveal meaning/}).click();
  await page.getByRole('button',{name:/Got it/}).click();
  await audit(page,'practice-review-complete');
  await nav.getByRole('button',{name:'Expedition',exact:true}).click();
  await expect(page.getByRole('region',{name:'Open Poland expedition map'}).locator('path[role="button"]')).toHaveCount(16);
  await audit(page,'expedition-open-map');
  expect(pageErrors).toEqual([]);
});

test('320px Read, Expedition and Learning Groups retain accessible controls',async({page})=>{
  test.setTimeout(90_000);
  await page.setViewportSize({width:320,height:720});
  const errors:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:'Mobile navigation'});
  await nav.getByRole('button',{name:'Library'}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Everyday Conversations: Greetings');
  await page.getByRole('button',{name:/Everyday Conversations: Greetings/}).click();
  await audit(page,'compact-read');
  await page.getByRole('button',{name:'Listen',exact:true}).click();
  await audit(page,'compact-reading-listen');
  await nav.getByRole('button',{name:'Expedition'}).click();
  await audit(page,'compact-expedition');
  await page.getByRole('button',{name:/Learning groups & scoreboards/}).click();
  await expect(page.getByRole('heading',{name:'Learning groups'})).toBeVisible();
  await audit(page,'compact-groups');
  await page.getByRole('button',{name:/Back to Poland map/}).click();
  await expect(page.getByRole('heading',{name:/Your Poland expedition/})).toBeVisible();
  expect(errors).toEqual([]);
});


test('empty Library, no-due Practice and navigation focus remain accessible',async({page,isMobile})=>{
  test.setTimeout(90_000);
  const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  const main=page.locator('#main-content');

  await nav.getByRole('button',{name:'Library',exact:true}).focus();
  await page.keyboard.press('Enter');
  await expect(main).toBeFocused();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('no-matching-polish-set-xyz');
  await expect(page.getByRole('heading',{name:'No matching lessons'})).toBeVisible();
  await audit(page,'library-no-results');
  await page.getByRole('button',{name:'Show all stages'}).click();
  await expect(page.getByRole('heading',{name:'No matching lessons'})).toHaveCount(0);

  await nav.getByRole('button',{name:'Practice',exact:true}).focus();
  await page.keyboard.press('Enter');
  await expect(main).toBeFocused();
  await expect(page.getByText('No expressions are due right now.',{exact:false})).toBeVisible();
  await audit(page,'practice-no-due');

  await nav.getByRole('button',{name:'Expedition',exact:true}).focus();
  await page.keyboard.press('Enter');
  await expect(main).toBeFocused();
  await page.getByRole('button',{name:/Learning groups & scoreboards/}).click();
  await expect(main).toBeFocused();
  await expect(page.getByRole('heading',{name:'Learning groups'})).toBeVisible();
  await page.getByRole('button',{name:/Back to Poland map/}).click();
  await expect(main).toBeFocused();
  await expect(page.getByRole('heading',{name:/Your Poland expedition/})).toBeVisible();
  expect(errors).toEqual([]);
});

test('keyboard mode selection does not steal focus or produce a new XP award',async({page,isMobile})=>{
  test.setTimeout(90_000);
  await page.goto('/');
  const nav=page.getByRole('navigation',{name:isMobile?'Mobile navigation':'Main navigation'});
  const main=page.locator('#main-content');
  await nav.getByRole('button',{name:'Library',exact:true}).click();
  await page.getByRole('searchbox',{name:'Search lessons'}).fill('Greetings and Introductions');
  await page.getByRole('button',{name:/Greetings and Introductions/}).focus();
  await page.keyboard.press('Enter');
  await expect(main).toBeFocused();
  const original=await page.evaluate(()=>localStorage.getItem('ptp-v2-expedition'));
  const listen=page.getByRole('button',{name:'Listen',exact:true});
  await listen.focus();await page.keyboard.press('Enter');
  await expect(listen).toBeFocused();
  await expect(listen).toHaveAttribute('aria-pressed','true');
  const speak=page.getByRole('button',{name:'Speak',exact:true});
  await speak.focus();await page.keyboard.press('Enter');
  await expect(speak).toBeFocused();
  await expect(speak).toHaveAttribute('aria-pressed','true');
  expect(await page.evaluate(()=>localStorage.getItem('ptp-v2-expedition'))).toBe(original);
  await nav.getByRole('button',{name:'Profile',exact:true}).focus();
  await page.keyboard.press('Enter');
  await expect(main).toBeFocused();
  await expect(page.getByRole('heading',{name:/Your profile/})).toBeVisible();
});

test.describe('network error-state audit (service worker deliberately excluded)',()=>{
  test.use({serviceWorkers:'block'});
  test('catalog HTTP failure provides keyboard-accessible retry and responsive error geometry',async({page})=>{
    test.setTimeout(90_000);
    await page.route('**/generated/lessons.json',route=>route.fulfill({
      status:503,contentType:'application/json',body:'{"error":"catalog_unavailable"}'
    }));
    await page.goto('/');
    const alert=page.getByRole('alert');
    await expect(alert).toContainText('Lessons could not load');
    await expect(alert.getByRole('button',{name:'Retry loading lessons'})).toBeVisible();
    await audit(page,'catalog-service-error');
    await alert.getByRole('button',{name:'Retry loading lessons'}).focus();
    await page.keyboard.press('Enter');
    await expect(alert).toContainText('Lessons could not load');
    await expect(alert.getByRole('button',{name:'Retry loading lessons'})).toBeVisible();
  });
});
