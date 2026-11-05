import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { ROOT, REPO_ROOT, SOURCE, DIST, readRelease, resetOutput, run } from './shared.mjs';

export function buildWeb() {
  const release = readRelease();
  run(process.execPath, [path.join(REPO_ROOT, 'tools/check.mjs'), SOURCE]);
  const output = path.join(DIST, 'web');
  resetOutput(output);
  const html = fs.readFileSync(SOURCE, 'utf8');
  if (!html.includes('window.DRAGON_TIDE_RELEASE')) throw new Error('Game must implement the release debug gate');
  if (!html.includes('<head>')) throw new Error('Expected one HTML head for runtime injection');
  fs.writeFileSync(path.join(output, 'index.html'), html.replace('<head>', '<head>\n<script src="./release-runtime.js"></script>'));
  fs.cpSync(path.join(path.dirname(SOURCE), 'assets'), path.join(output, 'assets'), { recursive: true, dereference: false });
  const runtime = { version: release.version, buildNumber: release.buildNumber, commit: release.commit };
  fs.writeFileSync(path.join(output, 'release-runtime.js'), `Object.defineProperty(window, 'DRAGON_TIDE_RELEASE', { value: Object.freeze(${JSON.stringify(runtime)}), writable: false });\n`);
  const files = {};
  function inventory(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const filename = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) throw new Error('Distribution assets must not be symbolic links');
      if (entry.isDirectory()) inventory(filename);
      else files[path.relative(output, filename).split(path.sep).join('/')] = crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');
    }
  }
  inventory(output);
  const dirty = execFileSync('git', ['status', '--porcelain', '--untracked-files=normal', '--', 'prototypes/dragon-tide', 'release/dragon-tide', 'tools/check.mjs'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim().length > 0;
  const manifest = { ...runtime, sourceDirty: dirty, appId: release.config.appId, identityConfirmed: release.config.identityConfirmed, saveCompatibility: release.config.saveCompatibility, files };
  fs.writeFileSync(path.join(output, 'release-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  console.log(`Built ${release.gameVersion} build ${release.buildNumber}: ${Object.keys(files).length} hashed files${dirty ? ' (local changes)' : ''}`);
  return release;
}
if (process.argv[1] && path.resolve(process.argv[1]) === path.join(ROOT, 'scripts/build-web.mjs')) buildWeb();
