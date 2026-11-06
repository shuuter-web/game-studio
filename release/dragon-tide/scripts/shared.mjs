import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync, spawnSync } from 'node:child_process';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const REPO_ROOT = path.resolve(ROOT, '../..');
export const SOURCE = path.join(REPO_ROOT, 'prototypes/dragon-tide/index.html');
export const DIST = path.join(ROOT, 'dist');
export function run(command, args, options = {}) {
  // Node scripts are invoked directly; never construct a shell command from release metadata.
  const result = spawnSync(command, args, { cwd: ROOT, stdio: 'inherit', ...options });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} exited with ${result.status}`);
}
export function readRelease() {
  const config = JSON.parse(fs.readFileSync(path.join(ROOT, 'config.json'), 'utf8'));
  const source = fs.readFileSync(SOURCE, 'utf8');
  const matches = [...source.matchAll(/const GAME_VERSION\s*=\s*"(v(\d+\.\d+\.\d+))";/g)];
  if (matches.length !== 1) throw new Error('Exactly one semantic GAME_VERSION is required');
  const [, gameVersion, version] = matches[0];
  if (!Number.isSafeInteger(config.buildNumber) || config.buildNumber < 1 || config.buildNumber > 2100000000) {
    throw new Error('buildNumber must be a positive Android-compatible integer');
  }
  if (!/^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*){2,}$/.test(config.appId)) throw new Error('Invalid appId');
  if (!/^[A-Za-z0-9_-]+$/.test(config.desktop.userDataDirectory)) throw new Error('Invalid userDataDirectory');
  if (!/^persist:[a-z0-9-]+$/.test(config.desktop.partition)) throw new Error('A stable persistent partition is required');
  const commit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  return { config, gameVersion, version, buildNumber: config.buildNumber, commit };
}
export function requireIdentity(config) {
  if (config.identityConfirmed !== true) throw new Error('Confirm the permanent appId and set identityConfirmed before store distribution');
}
export function validateReleaseTags(release, tags, requestedTag = '') {
  const expected = releaseTag(release);
  if (requestedTag && requestedTag !== expected) throw new Error(`Tag must be ${expected}, got ${requestedTag}`);
  for (const tag of tags) {
    const number = Number(/-build\.(\d+)$/.exec(tag.name)?.[1]);
    if (tag.name !== expected && number === release.buildNumber) throw new Error(`buildNumber is already used by ${tag.name}`);
  }
  const existing = tags.find(tag => tag.name === expected);
  if (existing) {
    if (existing.commit !== release.commit) throw new Error(`${expected} already identifies different source; increment buildNumber`);
    return; // Rebuilding an immutable historical release remains supported after newer releases exist.
  }
  if (requestedTag) throw new Error(`Release tag ${requestedTag} must exist and point to HEAD`);
  for (const tag of tags) {
    const match = /^dragon-tide-v\d+\.\d+\.\d+-build\.(\d+)$/.exec(tag.name);
    if (match && Number(match[1]) >= release.buildNumber) throw new Error(`buildNumber must exceed existing ${tag.name}; use npm run release:next`);
  }
}
export function readTags() {
  const names = execFileSync('git', ['tag', '--list', 'dragon-tide-v*-build.*'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim().split(/\r?\n/).filter(Boolean);
  return names.map(name => ({ name, commit: execFileSync('git', ['rev-list', '-n', '1', name], { cwd: REPO_ROOT, encoding: 'utf8' }).trim() }));
}
export function requireRelease(release) {
  requireIdentity(release.config);
  validateReleaseTags(release, readTags(), releaseTag(release));
  const changes = execFileSync('git', ['status', '--porcelain'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
  if (changes) throw new Error('Store builds require a clean checkout of the release tag');
}
export function resetOutput(directory) {
  const resolved = path.resolve(directory);
  const relative = path.relative(DIST, resolved);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) throw new Error('Output must be a child of release/dragon-tide/dist');
  fs.rmSync(resolved, { recursive: true, force: true });
  fs.mkdirSync(resolved, { recursive: true });
}
export function releaseTag(release) {
  return `dragon-tide-${release.gameVersion}-build.${release.buildNumber}`;
}
