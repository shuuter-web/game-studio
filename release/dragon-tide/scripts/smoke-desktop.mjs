import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { ROOT, DIST, run, resetOutput } from './shared.mjs';
import { buildWeb } from './build-web.mjs';
const require = createRequire(import.meta.url);
const electron = require('electron');
buildWeb();
const profile = path.join(DIST, 'smoke-profile');
resetOutput(profile);
const environment = { ...process.env, DT_SMOKE_ROOT: ROOT, DT_SMOKE_PROFILE: profile };
delete environment.ELECTRON_RUN_AS_NODE;
for (const phase of ['write', 'read']) {
  const packaged = path.join(DIST, 'windows/win-unpacked/resources/app.asar');
  if (process.argv.includes('--packaged') && phase === 'read') {
    if (!fs.existsSync(packaged)) throw new Error('Build Windows before the packaged restart check');
    environment.DT_SMOKE_APPLICATION = packaged;
  }
  run(electron, [path.join(ROOT, 'tests/desktop-harness.cjs'), phase], { env: environment, timeout: 60000, windowsHide: true });
}
console.log('Desktop boot and storage across process restarts: OK');
