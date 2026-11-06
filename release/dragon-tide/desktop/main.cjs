const { app } = require('electron');
const path = require('node:path');
const config = require('./config.json');
const { installProtocol, createWindow } = require('./application.cjs');
app.setPath('userData', path.join(app.getPath('appData'), config.desktop.userDataDirectory));
if (!app.requestSingleInstanceLock()) app.quit();
else {
  let mainWindow;
  app.on('second-instance', () => {
    if (mainWindow) { if (mainWindow.isMinimized()) mainWindow.restore(); mainWindow.focus(); }
  });
  app.whenReady().then(() => {
    const webRoot = path.join(__dirname, 'web');
    installProtocol(config.desktop.partition, webRoot);
    mainWindow = createWindow(config, webRoot);
  }).catch(error => { console.error(error); app.exit(1); });
  app.on('window-all-closed', () => app.quit());
}
