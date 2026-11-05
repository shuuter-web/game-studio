const { app } = require('electron');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = process.env.DT_SMOKE_ROOT;
const applicationRoot = process.env.DT_SMOKE_APPLICATION;
const { installProtocol, createWindow } = require(applicationRoot ? path.join(applicationRoot, 'application.cjs') : path.join(root, 'desktop/application.cjs'));
const config = require(applicationRoot ? path.join(applicationRoot, 'config.json') : path.join(root, 'config.json'));
app.setPath('userData', process.env.DT_SMOKE_PROFILE);
const timeout = setTimeout(() => { console.error('Desktop smoke timeout'); app.exit(1); }, 45000);
app.whenReady().then(async () => {
  const webRoot = applicationRoot ? path.join(applicationRoot, 'web') : path.join(root, 'dist/web');
  installProtocol(config.desktop.partition, webRoot);
  const window = createWindow(config, webRoot, { show: false });
  await new Promise((resolve, reject) => {
    window.webContents.once('did-finish-load', resolve);
    window.webContents.once('did-fail-load', (_event, code, description) => reject(new Error(`${code}: ${description}`)));
  });
  const state = await window.webContents.executeJavaScript(`({version: window.DRAGON_TIDE_RELEASE.version, origin: location.origin, node: typeof require, debug: IS_RELEASE_BUILD})`);
  assert.equal(state.origin, 'dragontide://game');
  assert.equal(state.node, 'undefined');
  assert.equal(state.debug, true);
  if (process.argv[2] === 'write') {
    await window.webContents.executeJavaScript(`localStorage.setItem('dragonTide_release_smoke', 'survives-update')`);
    window.webContents.session.flushStorageData();
  } else {
    assert.equal(await window.webContents.executeJavaScript(`localStorage.getItem('dragonTide_release_smoke')`), 'survives-update');
  }
  clearTimeout(timeout);
  app.quit();
}).catch(error => { console.error(error); app.exit(1); });
