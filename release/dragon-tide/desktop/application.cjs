const { BrowserWindow, protocol, net, session } = require('electron');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

// This origin and partition are part of the save contract. They must survive app updates.
protocol.registerSchemesAsPrivileged([{ scheme: 'dragontide', privileges: { standard: true, secure: true, supportFetchAPI: true } }]);
function installProtocol(partition, webRoot) {
  const persistentSession = session.fromPartition(partition);
  persistentSession.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  persistentSession.setPermissionCheckHandler(() => false);
  persistentSession.protocol.handle('dragontide', request => {
    const url = new URL(request.url);
    if (url.hostname !== 'game') return new Response('Not found', { status: 404 });
    let pathname;
    try { pathname = decodeURIComponent(url.pathname); } catch { return new Response('Bad path', { status: 400 }); }
    const filename = path.resolve(webRoot, '.' + (pathname === '/' ? '/index.html' : pathname));
    const relative = path.relative(webRoot, filename);
    if (relative.startsWith('..') || path.isAbsolute(relative)) return new Response('Forbidden', { status: 403 });
    return net.fetch(pathToFileURL(filename).toString());
  });
}
function createWindow(config, webRoot, options = {}) {
  const window = new BrowserWindow({
    width: 1280, height: 800, minWidth: 390, minHeight: 600,
    title: 'Dragon Tide', autoHideMenuBar: true, show: options.show !== false,
    webPreferences: { partition: config.desktop.partition, nodeIntegration: false, contextIsolation: true, sandbox: true, devTools: false, backgroundThrottling: true }
  });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event, target) => {
    if (target !== 'dragontide://game/index.html') event.preventDefault();
  });
  window.loadURL('dragontide://game/index.html');
  return window;
}
module.exports = { installProtocol, createWindow };
