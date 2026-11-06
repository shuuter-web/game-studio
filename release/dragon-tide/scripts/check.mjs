import fs from 'node:fs';
import path from 'node:path';
import { ROOT, REPO_ROOT, SOURCE, readRelease, releaseTag, readTags, validateReleaseTags, run } from './shared.mjs';
const release = readRelease();
const source = fs.readFileSync(SOURCE, 'utf8');
for (const [constant, key] of [['PROFILE_VERSION', 'profileVersion'], ['RUN_SAVE_VERSION', 'runVersion']]) {
  const value = Number(source.match(new RegExp(`const ${constant}\\s*=\\s*(\\d+)`))?.[1]);
  if (value !== release.config.saveCompatibility[key]) throw new Error(`${constant} changed: add migrations and update compatibility fixtures before changing the declared contract`);
}
const requestedTag = process.env.RELEASE_TAG || (process.env.GITHUB_REF_TYPE === 'tag' ? process.env.GITHUB_REF_NAME : '');
validateReleaseTags(release, readTags(), requestedTag);
run(process.execPath, [path.join(REPO_ROOT, 'tools/check.mjs'), SOURCE]);
const tests = fs.readdirSync(path.join(ROOT, 'tests')).filter(name => name.endsWith('.test.mjs')).map(name => path.join(ROOT, 'tests', name));
run(process.execPath, ['--test', ...tests]);
console.log(`Release contract OK: ${releaseTag(release)}`);
