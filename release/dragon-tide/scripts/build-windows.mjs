import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { build } from 'electron-builder';
import { ROOT, DIST, resetOutput, requireRelease, readRelease } from './shared.mjs';
import { buildWeb } from './build-web.mjs';
if (process.argv.includes('--release')) requireRelease(readRelease());
const release = buildWeb();
const application = path.join(DIST, 'desktop-app');
resetOutput(application);
fs.cpSync(path.join(DIST, 'web'), path.join(application, 'web'), { recursive: true });
for (const name of ['main.cjs', 'application.cjs']) fs.copyFileSync(path.join(ROOT, 'desktop', name), path.join(application, name));
fs.writeFileSync(path.join(application, 'config.json'), JSON.stringify(release.config, null, 2));
fs.writeFileSync(path.join(application, 'package.json'), JSON.stringify({ name: 'dragon-tide', productName: 'Dragon Tide', version: release.version, private: true, main: 'main.cjs', description: 'Dragon Tide', author: 'shuuter-web' }, null, 2));
resetOutput(path.join(DIST, 'windows'));
await build({
  projectDir: application,
  config: {
    appId: release.config.appId, productName: 'Dragon Tide', electronVersion: '45.2.1',
    buildVersion: release.version, asar: true, npmRebuild: false,
    directories: { output: path.join(DIST, 'windows') },
    files: ['main.cjs', 'application.cjs', 'config.json', 'package.json', 'web/**/*'],
    artifactName: `DragonTide-${release.version}-build.${release.buildNumber}-windows-x64.\${ext}`,
    win: { target: [{ target: 'zip', arch: ['x64'] }], signAndEditExecutable: false }
  }
});
const manifest = JSON.parse(fs.readFileSync(path.join(DIST, 'web/release-manifest.json'), 'utf8'));
const windowsFiles = {};
function hashDirectory(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) hashDirectory(filename);
    else windowsFiles[path.relative(path.join(DIST, 'windows'), filename).split(path.sep).join('/')] = crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');
  }
}
hashDirectory(path.join(DIST, 'windows'));
fs.writeFileSync(path.join(DIST, 'windows/build-manifest.json'), JSON.stringify({ ...manifest, windowsFiles }, null, 2) + '\n');
