import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const ios = path.resolve(scriptDir, '..');
const asset = path.join(ios, 'Resources/AppIcon.xcassets/AppIcon.appiconset');
const png = path.join(asset, 'AppIcon.png');

test('real iOS app icon is an opaque unrounded 1024px RGB PNG', () => {
  const bytes = fs.readFileSync(png);
  assert.deepEqual(bytes.subarray(0, 8), Buffer.from('89504e470d0a1a0a', 'hex'));
  assert.equal(bytes.subarray(12, 16).toString('ascii'), 'IHDR');
  assert.equal(bytes.readUInt32BE(8), 13);
  assert.equal(bytes.readUInt32BE(16), 1024);
  assert.equal(bytes.readUInt32BE(20), 1024);
  assert.equal(bytes[24], 8, '8-bit channels');
  assert.equal(bytes[25], 2, 'truecolor RGB: no alpha/palette');
  assert.equal(bytes[28], 0, 'no interlacing');
  assert.equal(bytes.subarray(-8, -4).toString('ascii'), 'IEND');
});

test('asset catalog and Xcode project declare AppIcon', () => {
  const contents = JSON.parse(fs.readFileSync(path.join(asset, 'Contents.json'), 'utf8'));
  assert.deepEqual(contents.images, [
    { filename: 'AppIcon.png', idiom: 'universal', platform: 'ios', size: '1024x1024' }
  ]);
  const project = fs.readFileSync(path.join(ios, 'project.yml'), 'utf8');
  assert.match(project, /- path: Resources\/AppIcon\.xcassets/);
  assert.match(project, /ASSETCATALOG_COMPILER_APPICON_NAME:\s*AppIcon/);
});

test('brand vector is a full unrounded white square with navy P and mint dot', () => {
  const svg = fs.readFileSync(path.join(ios, 'Brand/AppIcon.svg'), 'utf8');
  assert.match(svg, /<rect width="1024" height="1024" fill="#FFFFFF"\/>/);
  assert.match(svg, /fill="#102333"/);
  assert.match(svg, /fill="#56CFAE"/);
  assert.doesNotMatch(svg, /\brx=|clipPath|mask=/);
});
