import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { DIST, resetOutput, validateReleaseTags } from '../scripts/shared.mjs';
import { buildWeb } from '../scripts/build-web.mjs';

test('only a new release must exceed all historical build numbers; old tags remain reproducible', () => {
  const old = { gameVersion: 'v3.68.0', buildNumber: 1, commit: 'old' };
  const tags = [{ name: 'dragon-tide-v3.68.0-build.1', commit: 'old' }, { name: 'dragon-tide-v3.69.0-build.2', commit: 'new' }];
  assert.doesNotThrow(() => validateReleaseTags(old, tags));
  assert.doesNotThrow(() => validateReleaseTags(old, tags, tags[0].name));
  assert.throws(() => validateReleaseTags({ ...old, commit: 'changed' }, tags), /different source/);
  assert.throws(() => validateReleaseTags({ ...old, gameVersion: 'v3.70.0' }, tags), /must exceed/);
  assert.throws(() => validateReleaseTags(old, tags, tags[1].name), /Tag must be/);
  assert.doesNotThrow(() => validateReleaseTags({ ...old, gameVersion: 'v3.70.0', buildNumber: 3 }, tags));
});

test('clean builds remove obsolete files and the manifest covers shipped bytes', () => {
  const directory = path.join(DIST, 'web');
  fs.mkdirSync(directory, { recursive: true });
  fs.writeFileSync(path.join(directory, 'obsolete.js'), 'old release');
  buildWeb();
  assert.equal(fs.existsSync(path.join(directory, 'obsolete.js')), false);
  const manifest = JSON.parse(fs.readFileSync(path.join(directory, 'release-manifest.json'), 'utf8'));
  assert.ok(Object.keys(manifest.files).length > 10);
  for (const [name, hash] of Object.entries(manifest.files)) {
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(directory, name))).digest('hex'), hash);
  }
  const html = fs.readFileSync(path.join(directory, 'index.html'), 'utf8');
  assert.ok(html.indexOf('release-runtime.js') < html.indexOf('const GAME_VERSION'));
  assert.equal(fs.existsSync(path.join(directory, 'snapshots')), false);
  const firstManifest = fs.readFileSync(path.join(directory, 'release-manifest.json'), 'utf8');
  buildWeb();
  assert.equal(fs.readFileSync(path.join(directory, 'release-manifest.json'), 'utf8'), firstManifest);
});

test('cleaning is confined to generated child directories', () => {
  assert.throws(() => resetOutput(DIST), /child/);
  assert.throws(() => resetOutput(path.join(DIST, '..')), /child/);
});
