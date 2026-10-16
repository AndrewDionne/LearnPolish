import assert from 'node:assert/strict';
import { test } from 'node:test';
import { shellResources } from './build-offline.mjs';

test('precache excludes lesson MP3s but includes main bundle and manifest', () => {
  const resources = shellResources();
  assert.ok(resources.includes('./'));
  assert.ok(resources.includes('generated/lessons.json'));
  assert.ok(resources.some(item => item.endsWith('.js')));
  assert.ok(!resources.some(item => item.endsWith('.mp3')));
  assert.ok(resources.includes('avatars/hero-neutral.svg'));
  assert.ok(resources.includes('avatars/chonky-win.svg'));
});
