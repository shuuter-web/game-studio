import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
let playwright;
for (const candidate of [process.env.PLAYWRIGHT_MODULE_PATH, 'playwright'].filter(Boolean)) {
  try { playwright = require(candidate); break; } catch { /* try next */ }
}
if (!playwright) throw Error('Install playwright or set PLAYWRIGHT_MODULE_PATH.');
const browser = await playwright.chromium.launch(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {});
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const failures = [], errors = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
const check = (name, condition, detail = '') => { console.log(`${condition ? 'PASS' : 'FAIL'} ${name} ${detail}`); if (!condition) failures.push(name); };
const url = pathToFileURL(path.join(here, 'index.html')).href + '?seed=82082&fresh=flavor';
const artifacts = path.resolve(process.env.VOXEL_ARTIFACT_DIR || path.join(here, '../../artifacts/voxel-mine'));
await mkdir(artifacts, { recursive: true });
async function fresh() {
  await page.goto(url);
  await page.waitForFunction(() => typeof debugTryFlavor === 'function');
  await page.evaluate(() => resetGame());
}

try {
  await fresh();
  check('Version and fuel progression are v0.8.5 and 20/30/45/65', await page.evaluate(() => GAME_VERSION === 'v0.8.5' && JSON.stringify(FUEL_LEVELS.map(level => level.capacity)) === '[20,30,45,65]' && fuelCapacity() === 20));
  check('Port and result contain no flavor-note sections', await page.evaluate(() => !document.getElementById('discovery-notes') && !document.getElementById('result-notes')));

  const portTreasure = await page.evaluate(() => {
    player.treasures = [{ id:'test', name:'試験品', rarity:'希少', value:12, flavor:'結果に出してはいけない文章' }];
    renderBase();
    return document.getElementById('port-treasures').textContent;
  });
  check('Port treasure cards stay factual', portTreasure.includes('試験品') && portTreasure.includes('査定') && !portTreasure.includes('結果に出してはいけない文章'), portTreasure);

  await page.evaluate(() => debugDepart(1));
  const deterministic = await page.evaluate(() => {
    const findCount = () => {
      expedition.turns = 20; expedition.lastFlavorTurn = -1000000; player.recentFlavorIds = [];
      for (let count = 1; count < 500; count++) {
        player.materialGainCounts.copper = count;
        if (debugTryFlavor('copper')) return count;
      }
      return -1;
    };
    const count = findCount();
    hideFlavorToast(); expedition.lastFlavorTurn = -1000000; player.recentFlavorIds = []; player.materialGainCounts.copper = count;
    const first = debugTryFlavor('copper');
    hideFlavorToast(); expedition.lastFlavorTurn = -1000000; player.recentFlavorIds = []; player.materialGainCounts.copper = count;
    const second = debugTryFlavor('copper');
    return { count, first, second };
  });
  check('Flavor draw is deterministic and can occur during exploration', deterministic.count > 0 && deterministic.first && deterministic.second, JSON.stringify(deterministic));

  const pacing = await page.evaluate(() => {
    hideFlavorToast(); expedition.turns = 30; expedition.lastFlavorTurn = -1000000; player.recentFlavorIds = [];
    const force = id => { for (let count = 1; count < 1000; count++) { player.materialGainCounts[id] = count; if (debugTryFlavor(id)) return true; } return false; };
    const first = force('copper');
    const sameTurn = force('iron');
    expedition.turns += 8; const atEight = force('iron');
    expedition.turns += 1; const afterEight = force('iron');
    const recentRepeat = force('copper');
    return { first, sameTurn, atEight, afterEight, recentRepeat, recent:[...player.recentFlavorIds] };
  });
  check('One toast per turn and eight following actions are quiet', pacing.first && !pacing.sameTurn && !pacing.atEight && pacing.afterEight, JSON.stringify(pacing));
  check('Recently shown item types do not repeat', !pacing.recentRepeat && pacing.recent.includes('copper') && pacing.recent.includes('iron'), JSON.stringify(pacing));

  const rngIndependent = await page.evaluate(() => {
    reseedLogic(123456); const expected = random();
    reseedLogic(123456); expedition.turns = 100; expedition.lastFlavorTurn = -1000000; player.recentFlavorIds = []; player.materialGainCounts.scrap = 1; debugTryFlavor('scrap');
    return random() === expected;
  });
  check('Flavor checks do not consume gameplay RNG', rngIndependent);

  const toastLayout = await page.evaluate(() => {
    debugShowFlavor('copper');
    const element = document.getElementById('flavor-toast'), rect = element.getBoundingClientRect(), style = getComputedStyle(element);
    const hud = document.getElementById('hud').getBoundingClientRect();
    return { visible:!element.hidden, pointerEvents:style.pointerEvents, width:rect.width, left:rect.left, right:rect.right, top:rect.top, overlapsHud:rect.left<hud.right&&rect.right>hud.left&&rect.top<hud.bottom&&rect.bottom>hud.top };
  });
  check('Toast is compact, noninteractive, and clear of the main HUD', toastLayout.visible && toastLayout.pointerEvents === 'none' && toastLayout.width <= 324 && toastLayout.left >= 0 && toastLayout.right <= 390 && !toastLayout.overlapsHud, JSON.stringify(toastLayout));
  await page.screenshot({ path:path.join(artifacts, 'flavor-toast-v082.png'), fullPage:true });

  const saved = await page.evaluate(() => { player.materialGainCounts.copper = 7; player.recentFlavorIds = ['copper']; expedition.lastFlavorTurn = expedition.turns; debugSave(); return JSON.parse(localStorage.getItem(saveKey())); });
  check('Schema 11 saves flavor pacing state', saved.version === 11 && saved.player.materialGainCounts.copper === 7 && saved.player.recentFlavorIds[0] === 'copper' && Number.isInteger(saved.expedition.lastFlavorTurn));
  await page.reload(); await page.waitForFunction(() => typeof debugFlavorState === 'function');
  check('Flavor pacing state survives reload', await page.evaluate(() => player.materialGainCounts.copper === 7 && player.recentFlavorIds[0] === 'copper' && expedition.lastFlavorTurn === expedition.turns));

  await page.evaluate(() => { hideFlavorToast(); debugReturn(); });
  check('Result screen is a plain factual summary and hides flavor toast', await page.evaluate(() => expedition.phase === 'result' && document.getElementById('flavor-toast').hidden && !document.getElementById('result-details').textContent.includes('拾い話')));
  await page.screenshot({ path:path.join(artifacts, 'result-clean-v082.png'), fullPage:true });
  check('No runtime errors', errors.length === 0, JSON.stringify(errors));
} finally { await browser.close(); }

if (failures.length) { console.error(`\n${failures.length} failed: ${failures.join(', ')}`); process.exitCode = 1; }
else console.log('\nAll voxel-mine v0.8.5 fuel and flavor checks passed.');
