// Run: node prototypes/voxel-mine/verify.mjs
// Optional: PLAYWRIGHT_MODULE_PATH, PLAYWRIGHT_EXECUTABLE_PATH, VOXEL_ARTIFACT_DIR.
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
function loadPlaywright() {
  for (const candidate of [process.env.PLAYWRIGHT_MODULE_PATH, 'playwright', '/opt/node22/lib/node_modules/playwright'].filter(Boolean)) {
    try { return require(candidate); } catch { /* Try next installed runtime. */ }
  }
  throw new Error('Install playwright or set PLAYWRIGHT_MODULE_PATH.');
}
const { chromium } = loadPlaywright();
const browser = await chromium.launch({ ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const failures = [], errors = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
page.on('requestfailed', request => errors.push(request.url()));
page.on('dialog', dialog => dialog.accept());
function check(name, condition, detail = '') {
  console.log(`${condition ? 'PASS' : 'FAIL'} ${name} ${detail}`);
  if (!condition) failures.push(name);
}
const state = () => page.evaluate(() => debugState());
const url = pathToFileURL(path.join(here, 'index.html')).href + '?seed=777&fresh=1';
const artifactDirectory = path.resolve(process.env.VOXEL_ARTIFACT_DIR || path.join(here, '../../artifacts/voxel-mine'));
await mkdir(artifactDirectory, { recursive: true });
async function fresh() {
  await page.goto(url);
  await page.evaluate(() => { resetGame(); debugSave(); });
  await page.reload();
  await page.waitForFunction(() => typeof debugDepart === 'function');
}
// Small deterministic fixtures isolate edge cases from camera occlusion and world generation.
async function fixture({ material = 'copper', count = 6, fuel = 10, pickaxe = 2, chain = 1, range = 0 } = {}) {
  await fresh();
  await page.evaluate(options => {
    debugDepart(1);
    cells.fill(0); damage.fill(0); pendingBreaks.length = 0;
    for (let x = 2; x < options.count + 2; x++) cells[cellIndex(x, 2, 2)] = MATERIAL_BY_ID[options.material];
    solidCount = options.count;
    Object.assign(player, { pickaxe: options.pickaxe, chain: options.chain, range: options.range, power: 0, inventory: {} });
    expedition.fuel = options.fuel;
    rebuildSurface();
  }, { material, count, fuel, pickaxe, chain, range });
}
const hit = () => page.evaluate(() => mineAt(2, 2, 2, 195, 422));
const settle = () => page.evaluate(() => { nowSeconds += 10000; processPendingBreaks(); });
async function checkLayout(label) {
  const layout = await page.evaluate(() => {
    const visibleButtons = [...document.querySelectorAll('button')].filter(button => {
      const rect = button.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < innerHeight;
    });
    return { overflow: document.documentElement.scrollWidth > innerWidth,
      clipped: visibleButtons.filter(button => { const rect = button.getBoundingClientRect(); return rect.left < 0 || rect.right > innerWidth; }).map(button => button.textContent) };
  });
  check(`${label}: no horizontal overflow or clipped controls`, !layout.overflow && layout.clipped.length === 0, JSON.stringify(layout));
}
try {
  await fresh();
  const normalSentinel = 'verification normal-slot sentinel';
  await page.evaluate(value => localStorage.setItem(SAVE_KEY_PREFIX + worldSeed, value), normalSentinel);
  await page.reload();
  await page.evaluate(() => debugSave());
  check('Fresh sandbox does not overwrite normal save slot', await page.evaluate(value => localStorage.getItem(SAVE_KEY_PREFIX + worldSeed) === value, normalSentinel));
  await page.evaluate(() => localStorage.removeItem(SAVE_KEY_PREFIX + worldSeed));
  let current = await state();
  check('New game starts at base with only island 1 unlocked', current.expedition.phase === 'base' && JSON.stringify(current.unlocks) === '[1]');
  check('Initial fuel capacity is 60', current.capacity === 60);
  check('Locked and invalid destinations cannot be entered', await page.evaluate(() => [2, 0, 7, -1, 1.5].every(id => !debugDepart(id))));
  check('Insufficient materials cannot craft', await page.evaluate(() => !debugCraft('pickaxe') && !debugCraft('fuel') && !debugCraft('route')));
  const baseBefore = await state();
  await page.evaluate(() => debugTapAt(195, 422));
  check('Base tapping does not consume fuel', (await state()).expedition.fuel === baseBefore.expedition.fuel);
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-base.png'), fullPage: true });
  await checkLayout('Mobile base');

  // Exercise an actual departure button and a canvas pointer event.
  await page.locator('[data-depart="1"]').click();
  await page.waitForFunction(() => debugState().faces > 300);
  current = await state();
  const originalCells = await page.evaluate(() => Array.from(cells));
  check('Departure creates island 1 and refills fuel', current.expedition.phase === 'exploring' && current.expedition.fuel === 60 && current.solid > 400);
  check('Island 1 renders copper but no iron', current.faces > 300 && current.counts.copper > 0 && !current.counts.iron);
  const grass = await page.evaluate(() => debugFindFace('grass'));
  check('Visible grass can be targeted', !!grass);
  if (grass) {
    await page.mouse.click(grass.x, grass.y);
    const after = await state();
    check('Real canvas tap mines and consumes one turn', after.solid < current.solid && after.expedition.fuel === 59 && after.expedition.turns === 1);
  }
  const beforeUi = await state();
  await page.locator('#btn-sound').click();
  await page.mouse.move(170, 420); await page.mouse.down(); await page.mouse.move(230, 440, { steps: 5 }); await page.mouse.up();
  await page.evaluate(() => debugTapAt(-100, -100));
  const afterUi = await state();
  check('Sound, rotation and misses are free', afterUi.expedition.fuel === beforeUi.expedition.fuel);
  check('Crafting and repeat departure blocked during expedition', await page.evaluate(() => { debugGrant('stone', 1000); debugGrant('dirt', 1000); return !debugCraft('fuel') && !debugCraft('route') && !debugCraft('pickaxe') && !debugDepart(1); }));
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-expedition.png'), fullPage: true });
  await checkLayout('Mobile expedition');
  const inventoryBeforeReturn = (await state()).player.inventory;
  await page.locator('#btn-next').click();
  check('Manual return preserves inventory', (await state()).expedition.phase === 'base' && JSON.stringify((await state()).player.inventory) === JSON.stringify(inventoryBeforeReturn));
  await page.evaluate(() => debugDepart(1));
  check('Same-seed revisit regenerates exact island and refills for free', await page.evaluate(expected => JSON.stringify(Array.from(cells)) === JSON.stringify(expected) && expedition.fuel === debugState().capacity, originalCells));
  await page.evaluate(() => debugReturn());
  const capacityBefore = (await state()).capacity;
  check('Fuel upgrade is craftable at base', await page.evaluate(() => debugCraft('fuel')));
  check('Fuel upgrade increases capacity', (await state()).capacity > capacityBefore);
  await page.evaluate(() => debugDepart(1));
  check('Departure uses upgraded capacity', (await state()).expedition.fuel === (await state()).capacity);

  await fixture({ material: 'stone', count: 1, pickaxe: 0, chain: 0 });
  let result = await hit();
  check('Partial hit spends one fuel without breaking stone', result.broken === 0 && (await state()).expedition.fuel === 9 && (await state()).solid === 1);
  await page.evaluate(() => debugSave());
  await page.reload();
  check('Reload preserves partial damage, fuel and turn', await page.evaluate(() => damage[cellIndex(2, 2, 2)] === 1 && expedition.fuel === 9 && expedition.turns === 1));
  result = await hit();
  check('Second hit breaks saved damaged stone', result.broken === 1 && (await state()).player.inventory.stone === 1 && (await state()).expedition.fuel === 8);
  await fixture({ pickaxe: 0, chain: 0 });
  result = await hit();
  check('Hardlocked copper is free', result.locked && (await state()).expedition.fuel === 10 && (await state()).solid === 6);

  await fixture({ material: 'dirt', count: 3, chain: 0, range: 1 });
  result = await hit();
  check('Range mining breaks multiple cells for one fuel', result.broken > 1 && (await state()).expedition.fuel === 9);

  await fixture();
  result = await hit();
  current = await state();
  check('Copper fixture queues exactly three chain cells', result.broken === 1 && current.pending === 3);
  const guard = await page.evaluate(() => {
    const before = debugState(); mineAt(7, 2, 2, 195, 422); const after = debugState();
    return before.expedition.fuel === after.expedition.fuel && before.solid === after.solid;
  });
  check('Repeated action cannot overlap pending chain', guard);
  await settle();
  current = await state();
  check('Chain respects budget and costs no extra fuel', current.solid === 2 && current.pending === 0 && current.expedition.fuel === 9);
  const chainReward = current.player.inventory.copper;
  const chainCombo = current.combo;

  // Delay within the legal save window so navigation cannot finish the chain first.
  await fixture();
  await page.evaluate(() => { mineAt(2, 2, 2, 195, 422); for (const item of pendingBreaks) item.due += 1; debugSave(); });
  const pendingBefore = await state();
  await page.reload();
  const pendingAfter = await state();
  check('Reload preserves queued chain and spent fuel', pendingAfter.pending === pendingBefore.pending && pendingAfter.expedition.fuel === 9 && pendingAfter.solid === pendingBefore.solid);
  await settle();
  check('Reloaded chain grants exactly the uninterrupted reward', (await state()).player.inventory.copper === chainReward && (await state()).pending === 0);
  await page.evaluate(() => debugSave()); await page.reload();
  check('Reload does not duplicate chain rewards', (await state()).player.inventory.copper === chainReward);

  await fixture({ fuel: 1 });
  await page.evaluate(() => { mineAt(2, 2, 2, 195, 422); for (const item of pendingBreaks) item.due += 1; debugSave(); });
  await page.reload();
  check('Zero-fuel reload preserves final chain before automatic return', (await state()).expedition.fuel === 0 && (await state()).pending === 3);
  await settle();
  current = await state();
  check('Final fuel action returns with every chain reward', current.expedition.phase === 'base' && current.pending === 0 && current.player.inventory.copper === chainReward);
  await fixture();
  await page.evaluate(() => { mineAt(2, 2, 2, 195, 422); debugReturn(); });
  await settle();
  current = await state();
  check('Manual return during chain retains every reward', current.expedition.phase === 'base' && current.pending === 0 && current.player.inventory.copper === chainReward);
  await fixture();
  await page.evaluate(() => { nowSeconds += 10000; mineAt(2, 2, 2, 195, 422); });
  await settle();
  check('Thinking time does not change action combo or reward', (await state()).combo === chainCombo && (await state()).player.inventory.copper === chainReward);

  // Multiple ore chains must pay the same bonus regardless of frame batching.
  const mixedRewards = await page.evaluate(() => {
    const outcomes = [];
    for (const stepped of [false, true]) {
      pendingBreaks.length = 0; cells.fill(0); damage.fill(0);
      Object.assign(expedition, { phase: 'exploring', fuel: 10, returnRequested: false, haul: {} });
      player.inventory = {}; combo = 7; comboMultiplier = 1; solidCount = 4;
      const start = nowSeconds;
      const entries = [
        { x: 2, material: M_COPPER, delay: 1 }, { x: 3, material: M_COPPER, delay: 2 },
        { x: 4, material: M_CRYSTAL, delay: 1 }, { x: 5, material: M_CRYSTAL, delay: 2 },
      ];
      for (const entry of entries) {
        const idx = cellIndex(entry.x, 2, 2); cells[idx] = entry.material;
        pendingBreaks.push({ idx, material: entry.material, due: start + entry.delay, step: 1 });
      }
      if (stepped) { nowSeconds = start + 1; processPendingBreaks(); }
      nowSeconds = start + 2; processPendingBreaks();
      outcomes.push({ copper: have('copper'), crystal: have('crystal') });
    }
    return outcomes;
  });
  check('Mixed-chain rewards are independent of frame batching', JSON.stringify(mixedRewards[0]) === JSON.stringify(mixedRewards[1]), JSON.stringify(mixedRewards));

  await fresh();
  await page.evaluate(() => { for (const id of INVENTORY_ORDER) debugGrant(id, 100000); });
  for (let id = 2; id <= 6; id++) {
    const before = await state();
    const crafted = await page.evaluate(() => debugCraft('route'));
    current = await state();
    check(`Route upgrade unlocks only island ${id}`, crafted && current.unlocks.length === id && current.unlocks.at(-1) === id && before.unlocks.length === id - 1);
  }
  check('Route at maximum cannot be crafted', await page.evaluate(() => !debugCraft('route')));
  await page.evaluate(() => debugDepart(6));
  current = await state();
  check('Island 6 retains all late-game resources', ['iron', 'gold', 'obsidian', 'starcore'].every(id => current.counts[id] > 0));
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({ path: path.join(artifactDirectory, 'desktop-island6.png'), fullPage: true });
  await checkLayout('Desktop expedition');
  await page.evaluate(() => {
    player.pickaxe = 3; player.range = 1; player.chain = 2; player.power = 2;
    debugSave();
    const legacy = JSON.parse(localStorage.getItem(saveKey()));
    legacy.version = 1;
    for (const key of Object.keys(legacy)) if (!['version', 'gameVersion', 'worldSeed', 'player', 'island', 'camera'].includes(key)) delete legacy[key];
    for (const key of Object.keys(legacy.player)) if (!['pickaxe', 'range', 'chain', 'power', 'inventory', 'seen', 'stats'].includes(key)) delete legacy.player[key];
    window.removeEventListener('beforeunload', saveGame);
    localStorage.setItem(saveKey(), JSON.stringify(legacy));
  });
  const legacyInventory = (await state()).player.inventory;
  await page.reload(); current = await state();
  check('Legacy v1 migration preserves equipment and inventory', current.player.pickaxe === 3 && current.player.range === 1 && current.player.chain === 2 && current.player.power === 2 && JSON.stringify(current.player.inventory) === JSON.stringify(legacyInventory));
  check('Legacy reached island remains unlocked at base', current.unlocks.includes(6) && current.expedition.phase === 'base');
  await page.evaluate(() => { window.removeEventListener('beforeunload', saveGame); localStorage.setItem(saveKey(), JSON.stringify({ version: 2, island: { cells: 'invalid!' }, player: {} })); });
  await page.reload();
  check('Malformed save falls back to playable base', (await state()).expedition.phase === 'base' && (await state()).unlocks.includes(1));
  for (const seed of [0, 1, 777, 12345]) {
    await page.goto(pathToFileURL(path.join(here, 'index.html')).href + `?seed=${seed}&fresh=1`);
    const generation = await page.evaluate(() => {
      const definingMaterials = ['copper', 'crystal', 'iron', 'gold', 'obsidian', 'starcore'];
      return definingMaterials.map((material, index) => { generateIsland(index + 1); return { island: index + 1, material, count: debugState().counts[material] || 0 }; });
    });
    check(`Seed ${seed}: every destination contains its defining resource`, generation.every(item => item.count > 0), JSON.stringify(generation));
  }
  check('No runtime or resource errors', errors.length === 0, errors.join(' | '));
} catch (error) {
  failures.push(error.stack || error.message);
} finally {
  await browser.close();
}
console.log(`Screenshots: ${artifactDirectory}`);
if (failures.length) { console.error(failures.join('\n')); process.exitCode = 1; }
else console.log('All expedition regressions passed.');
