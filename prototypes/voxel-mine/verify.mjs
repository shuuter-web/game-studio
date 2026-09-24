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
    cells.fill(0); damage.fill(0); pendingBreaks.length = 0; creatures.length = 0; trees.length = 0;
    for (let x = 2; x < options.count + 2; x++) cells[cellIndex(x, 2, 2)] = MATERIAL_BY_ID[options.material];
    solidCount = options.count;
    Object.assign(player, { pickaxe: options.pickaxe, chain: options.chain, range: options.range, power: 0, inventory: {} });
    expedition.fuel = options.fuel;
    rebuildSurface();
  }, { material, count, fuel, pickaxe, chain, range });
}
const hit = () => page.evaluate(() => mineAt(2, 2, 2, 195, 422));
const settle = () => page.evaluate(() => { nowSeconds += 10000; processPendingBreaks(); });
async function ensureVisibleCreature() {
  return page.evaluate(() => {
    let visible = debugFindCreature();
    if (visible) return visible;
    const creature = creatures.find(entry => !entry.captured && !entry.escaped);
    if (!creature) return null;
    for (const candidate of groundCandidates()) {
      creature.cellIndex = candidate;
      renderIslandLayer();
      visible = creatureProjection(creature);
      if (visible) return visible;
    }
    return null;
  });
}
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
  check('Prominent fuel gauge shows current and maximum fuel', await page.locator('#fuel-status').isVisible() && await page.locator('#fuel-meter').getAttribute('aria-valuenow') === '60' && await page.locator('#fuel-meter').getAttribute('aria-valuemax') === '60' && (await page.locator('#fuel-value').textContent()) === '60 / 60');
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
  check('Crafting and repeat departure blocked during expedition', await page.evaluate(() => { debugGrant('scrap', 1000); player.coins = 10000; return !debugCraft('fuel') && !debugCraft('route') && !debugCraft('pickaxe') && !debugDepart(1); }));
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-expedition.png'), fullPage: true });
  await checkLayout('Mobile expedition');
  const inventoryBeforeReturn = (await state()).player.inventory;
  await page.locator('#btn-next').click();
  check('Manual return preserves inventory', (await state()).expedition.phase === 'result' && JSON.stringify((await state()).player.inventory) === JSON.stringify(inventoryBeforeReturn));
  await page.evaluate(() => { debugAcknowledgeResult(); debugDepart(1); });
  const revisitCells = await page.evaluate(() => Array.from(cells));
  check('Revisiting the same route generates a different island shape and refills for free', await page.evaluate(expected => JSON.stringify(Array.from(cells, value => Number(Boolean(value)))) !== JSON.stringify(expected.map(value => Number(Boolean(value)))) && expedition.fuel === debugState().capacity, originalCells));
  await page.evaluate(() => debugSave()); await page.reload();
  check('Reloading the current expedition preserves its generated island', await page.evaluate(expected => JSON.stringify(Array.from(cells)) === JSON.stringify(expected), revisitCells));
  await page.evaluate(() => { debugReturn(); debugAcknowledgeResult(); });
  const capacityBefore = (await state()).capacity;
  check('Fuel upgrade is craftable at base', await page.evaluate(() => debugCraft('fuel')));
  check('Fuel upgrade increases capacity', (await state()).capacity > capacityBefore);
  await page.evaluate(() => debugDepart(1));
  check('Departure uses upgraded capacity', (await state()).expedition.fuel === (await state()).capacity);

  await fresh();
  await page.evaluate(() => debugDepart(1));
  await ensureVisibleCreature();
  const preCapture = await state();
  check('Four creatures are preplaced before mining', preCapture.creatures.length === 4 && preCapture.creatures.every(creature => !creature.captured && !creature.escaped));
  const animation = await page.evaluate(() => {
    const previousFrame = boilFrame, before = JSON.stringify({ creatures, expedition, inventory: player.inventory });
    boilFrame = 0;
    const first = buildPropFaces().filter(face => face.entity.type === 'creature');
    boilFrame = 4;
    const second = buildPropFaces().filter(face => face.entity.type === 'creature');
    boilFrame = previousFrame;
    return { firstFaces: first.length, changed: JSON.stringify(first.map(face => face.vertices)) !== JSON.stringify(second.map(face => face.vertices)), stable: JSON.stringify({ creatures, expedition, inventory: player.inventory }) === before };
  });
  check('Rounded creature meshes have two distinct visual poses without changing game state', animation.firstFaces > 60 && animation.changed && animation.stable, JSON.stringify(animation));
  const silhouette = await page.evaluate(() => {
    const previousYaw = camera.yaw;
    const styles = () => buildPropFaces().filter(face => face.entity.type === 'creature').map(face => [face.key, face.edgeStyles]);
    const first = styles();
    camera.yaw += .9; updateCamBasis(); updateViewDir();
    const rotated = styles();
    camera.yaw = previousYaw; updateCamBasis(); updateViewDir();
    return { thick: first.flatMap(face => face[1]).filter(style => style === 2).length, thin: first.flatMap(face => face[1]).filter(style => style === 1).length, changed: JSON.stringify(first) !== JSON.stringify(rotated), sharedWidth: drawIsland.toString().includes('sceneBoldInkWidth()') && drawPropFace.toString().includes('sceneBoldInkWidth()') };
  });
  check('Creature outer lines match block width, internal lines stay thin, and change with camera', silhouette.thick > 0 && silhouette.thin > 0 && silhouette.changed && silhouette.sharedWidth, JSON.stringify(silhouette));
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-creatures.png'), fullPage: true });
  const visibleCreature = await page.evaluate(() => debugFindCreature());
  await page.mouse.click(visibleCreature.x, visibleCreature.y);
  const captured = await state();
  check('Canvas capture spends exactly one fuel and yields treasure', captured.expedition.fuel === 59 && captured.expedition.captures === 1 && captured.creatures.find(creature => creature.id === visibleCreature.id).captured && Object.keys(captured.player.inventory).length > 0);
  const capturedInventory = JSON.stringify(captured.player.inventory);
  await page.evaluate(id => { debugCapture(id); debugCapture(-1); debugSave(); }, visibleCreature.id);
  check('Duplicate and invalid capture are free', (await state()).expedition.fuel === 59 && JSON.stringify((await state()).player.inventory) === capturedInventory);
  await page.reload();
  check('Captured creature stays captured after reload', (await state()).creatures.find(creature => creature.id === visibleCreature.id).captured && JSON.stringify((await state()).player.inventory) === capturedInventory);
  check('Cannot sell while exploring', await page.evaluate(() => { const before = JSON.stringify(player); debugSellAll(); return JSON.stringify(player) === before; }));
  await page.evaluate(() => debugReturn());
  const resultState = await state();
  check('Capture return opens populated result', resultState.expedition.phase === 'result' && resultState.expedition.captures === 1 && resultState.expedition.turns === 1);
  await page.locator('#btn-result-debug').click();
  check('Result debug menu opens', await page.locator('#debug-panel').isVisible());
  await page.locator('#btn-debug-close').click();
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-result.png'), fullPage: true });
  await checkLayout('Mobile result');
  await page.evaluate(() => debugSave()); await page.reload();
  check('Result reload preserves haul without awarding twice', (await state()).expedition.phase === 'result' && JSON.stringify((await state()).player.inventory) === capturedInventory);
  check('Result blocks capture, departure, crafting and selling', await page.evaluate(() => {
    const before = JSON.stringify(debugState().player), fuel = expedition.fuel;
    debugCapture(creatures.find(creature => !creature.captured)?.id); debugDepart(1); debugCraft('fuel'); debugSellAll();
    return before === JSON.stringify(debugState().player) && fuel === expedition.fuel && expedition.phase === 'result';
  }));
  await page.locator('#btn-result-base').click();
  await page.evaluate(() => debugAcknowledgeResult());
  check('Acknowledging result repeatedly never re-awards inventory', (await state()).expedition.phase === 'base' && JSON.stringify((await state()).player.inventory) === capturedInventory);
  await page.evaluate(() => { debugGrant('scrap', 9); debugGrant('copper', 7); });
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-base-sell.png'), fullPage: true });
  const coinsBefore = (await state()).player.coins;
  const expectedSale = await page.evaluate(() => Object.entries(player.inventory).reduce((sum, [id, amount]) => sum + (ITEMS[id]?.saleValue || 0) * amount, 0));
  await page.locator('#btn-sell-all').click();
  const sold = await state();
  check('Sell-all converts exact treasure value without selling materials', expectedSale > 0 && sold.player.coins === coinsBefore + expectedSale && sold.player.inventory.scrap === 9 && sold.player.inventory.copper === 7);
  await page.evaluate(() => debugSellAll());
  check('Treasure cannot be sold twice', (await state()).player.coins === sold.player.coins);

  await fresh(); await page.evaluate(() => debugDepart(1));
  await ensureVisibleCreature();
  await page.evaluate(() => { expedition.fuel = 1; debugCapture(debugFindCreature().id); });
  current = await state();
  check('Last-fuel capture awards treasure and opens return notice before result', current.expedition.phase === 'exploring' && current.expedition.returnRequested && current.expedition.captures === 1 && Object.keys(current.player.inventory).length > 0 && await page.locator('#fuel-notice').isVisible() && (await page.locator('#fuel-notice-message').textContent()) === '燃料がなくなった。帰還しよう。' && await page.locator('#fuel-status').evaluate(element => element.classList.contains('empty')) && await page.locator('#fuel-meter').getAttribute('aria-valuenow') === '0');
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-fuel-empty.png'), fullPage: true });
  const fuelNoticeInventory = JSON.stringify(current.player.inventory);
  await page.evaluate(() => debugSave()); await page.reload();
  check('Fuel notice survives reload and blocks further actions', await page.locator('#fuel-notice').isVisible() && await page.evaluate(expected => { const before = JSON.stringify(player.inventory); debugTapCenter(); debugReturn(); return before === JSON.stringify(player.inventory) && JSON.stringify(player.inventory) === expected && expedition.phase === 'exploring'; }, fuelNoticeInventory));
  await page.locator('#btn-fuel-return').click();
  check('Fuel notice confirmation opens result exactly once', (await state()).expedition.phase === 'result' && !(await page.locator('#fuel-notice').isVisible()));

  await fresh(); await page.evaluate(() => debugDepart(1));
  await ensureVisibleCreature();
  const pendingCapture = await page.evaluate(() => {
    const visible = debugFindCreature(), index = cells.findIndex(material => material === M_COPPER);
    pendingBreaks.push({ idx: index, material: M_COPPER, due: nowSeconds + 1, step: 1 });
    const fuel = expedition.fuel, inventory = JSON.stringify(player.inventory);
    debugCapture(visible.id);
    return expedition.fuel === fuel && JSON.stringify(player.inventory) === inventory && !creatures.find(creature => creature.id === visible.id).captured;
  });
  check('Capture cannot overlap pending chain', pendingCapture);

  await fresh(); await page.evaluate(() => debugDepart(1));
  await ensureVisibleCreature();
  const occlusion = await page.evaluate(() => {
    const visible = debugFindCreature(), creature = creatures.find(entry => entry.id === visible.id);
    indexToXYZ(creature.cellIndex, _xyz); const [x, y, z] = _xyz;
    const roof = cellIndex(x, y + 1, z), previous = cells[roof];
    cells[roof] = M_STONE; if (!previous) solidCount++;
    rebuildSurface(); renderIslandLayer();
    const hidden = creatureProjection(creature) === null, fuel = expedition.fuel;
    debugCapture(creature.id);
    return { hidden, free: expedition.fuel === fuel, captured: creature.captured };
  });
  check('Rock occlusion prevents capture through terrain', occlusion.hidden && occlusion.free && !occlusion.captured, JSON.stringify(occlusion));
  const supportOutcomes = [];
  for (let repeat = 0; repeat < 2; repeat++) {
    await fresh(); await page.evaluate(() => debugDepart(1));
    await ensureVisibleCreature();
    supportOutcomes.push(await page.evaluate(() => {
      const visible = debugFindCreature(), creature = creatures.find(entry => entry.id === visible.id), oldIndex = creature.cellIndex;
      indexToXYZ(oldIndex, _xyz); const coordinates = [..._xyz];
      player.pickaxe = 5; player.power = 20; player.range = 0; player.chain = 0;
      mineAt(...coordinates, visible.x, visible.y);
      return { id: creature.id, oldIndex, cellIndex: creature.cellIndex, escaped: creature.escaped, supported: !!cells[creature.cellIndex], captured: creature.captured };
    }));
  }
  check('Mining creature support relocates or escapes safely', supportOutcomes.every(outcome => (outcome.escaped || (outcome.supported && outcome.cellIndex !== outcome.oldIndex)) && !outcome.captured), JSON.stringify(supportOutcomes));
  const relocationBatches = await page.evaluate(() => {
    const outcomes = [];
    for (const stepped of [false, true]) {
      cells.fill(0); damage.fill(0); pendingBreaks.length = 0;
      const upper = cellIndex(3, 6, 3), lower = cellIndex(3, 2, 3);
      for (const idx of [upper, lower, cellIndex(4, 6, 3), cellIndex(4, 2, 3)]) cells[idx] = M_COPPER;
      solidCount = 4;
      creatures.splice(0, creatures.length, { id: 0, kind: 'bird', cellIndex: upper, captured: false, escaped: false });
      Object.assign(expedition, { phase: 'exploring', fuel: 10, returnRequested: false, haul: {} });
      const start = nowSeconds;
      pendingBreaks.push({ idx: upper, material: M_COPPER, due: start + 1, step: 1 }, { idx: lower, material: M_COPPER, due: start + 2, step: 2 });
      if (stepped) { nowSeconds = start + 1; processPendingBreaks(); }
      nowSeconds = start + 2; processPendingBreaks();
      outcomes.push(creatures[0].cellIndex);
    }
    return outcomes;
  });
  check('Creature relocation is independent of chain frame batching', relocationBatches[0] === relocationBatches[1], JSON.stringify(relocationBatches));

  await fresh(); await page.evaluate(() => debugDepart(1));
  const lootBefore = await page.evaluate(() => { const entries=Array.from({length:100},(_,index)=>resolveBlockLoot(M_STONE,index)); return {serial:tripSerial,entries,treasureCount:player.treasures.length}; });
  const lootKinds = new Set(lootBefore.entries.map(entry => entry?.id || 'none'));
  check('Terrain loot includes nothing, scrap and treasure', lootKinds.has('none') && lootKinds.has('scrap') && lootBefore.treasureCount > 0);
  await page.evaluate(() => debugSave()); await page.reload();
  const lootAfter = await page.evaluate(() => ({ serial: tripSerial, entries: Array.from({length: 100}, (_, index) => resolveBlockLoot(M_STONE, index)) }));
  check('Same-trip reload preserves exact loot and trip serial', lootAfter.serial === lootBefore.serial && JSON.stringify(lootAfter.entries) === JSON.stringify(lootBefore.entries));
  const lateLoot = await page.evaluate(() => { nowSeconds += 10000; combo = 100; return Array.from({length: 100}, (_, index) => resolveBlockLoot(M_STONE, index)); });
  check('Terrain discoveries do not depend on combo or observation time', JSON.stringify(lateLoot) === JSON.stringify(lootBefore.entries));
  await page.evaluate(() => { debugReturn(); debugAcknowledgeResult(); });
  check('Returning does not increment trip serial', (await state()).tripSerial === lootBefore.serial);
  await page.evaluate(() => debugDepart(1));
  check('Only departure advances serial and next-trip discoveries', (await state()).tripSerial === lootBefore.serial + 1 && JSON.stringify(await page.evaluate(() => Array.from({length: 100}, (_, index) => resolveBlockLoot(M_STONE, index)))) !== JSON.stringify(lootBefore.entries));

  await fixture({ material: 'stone', count: 1, pickaxe: 0, chain: 0 });
  let result = await hit();
  check('Partial hit spends one fuel without breaking stone', result.broken === 0 && (await state()).expedition.fuel === 9 && (await state()).solid === 1);
  await page.evaluate(() => debugSave());
  await page.reload();
  check('Reload preserves partial damage, fuel and turn', await page.evaluate(() => damage[cellIndex(2, 2, 2)] === 1 && expedition.fuel === 9 && expedition.turns === 1));
  result = await hit();
  check('Second hit breaks saved damaged stone', result.broken === 1 && !(await state()).player.inventory.stone && (await state()).expedition.fuel === 8);
  check('Removing last block opens result automatically', (await state()).expedition.phase === 'result' && (await state()).expedition.blocksDestroyed === 1);
  for (const material of ['grass', 'dirt', 'stone']) {
    await fixture({ material, count: 6, pickaxe: 2, chain: 0 });
    const terrain = await page.evaluate(() => {
      const expected = {};
      for (let x = 2; x < 8; x++) { const index = cellIndex(x, 2, 2), reward = resolveBlockLoot(cells[index], index); if (reward) expected[reward.id] = (expected[reward.id] || 0) + reward.amount; }
      for (let x = 2; x < 8; x++) mineAt(x, 2, 2, 195, 422);
      return { expected, actual: player.inventory };
    });
    check(`${material} mining grants only deterministic discoveries`, !terrain.actual.dirt && !terrain.actual.stone && !terrain.actual.grass && JSON.stringify(terrain.actual) === JSON.stringify(terrain.expected), JSON.stringify(terrain));
  }
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
  check('Final fuel action waits after every chain reward', current.expedition.phase === 'exploring' && current.expedition.returnRequested && current.pending === 0 && current.player.inventory.copper === chainReward && await page.locator('#fuel-notice').isVisible());
  await page.evaluate(() => debugAcknowledgeFuelNotice());
  check('Final chain moves to result after fuel notice confirmation', (await state()).expedition.phase === 'result');
  await fixture();
  await page.evaluate(() => { mineAt(2, 2, 2, 195, 422); debugReturn(); });
  await settle();
  current = await state();
  check('Manual return during chain retains every reward', current.expedition.phase === 'result' && current.pending === 0 && current.player.inventory.copper === chainReward);
  await fixture();
  await page.evaluate(() => { nowSeconds += 10000; mineAt(2, 2, 2, 195, 422); nowSeconds += 10; processPendingBreaks(); });
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
  await page.evaluate(() => { for (const id of INVENTORY_ORDER) debugGrant(id, 100000); player.coins = 100000; });
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
    const obsolete = JSON.parse(localStorage.getItem(saveKey()));
    obsolete.version = 7;
    obsolete.player.coins = 999;
    window.removeEventListener('beforeunload', saveGame);
    localStorage.setItem(saveKey(), JSON.stringify(obsolete));
  });
  await page.reload(); current = await state();
  check('Schema 7 save is initialized as a new schema 8 game', current.expedition.phase === 'base' && current.player.coins === 0 && current.unlocks.length === 1); await page.evaluate(() => debugSave()); check('Fresh replacement save uses schema 8', JSON.parse(await page.evaluate(() => localStorage.getItem(saveKey()))).version === 8);
  await page.setViewportSize({ width: 390, height: 844 });
  await fresh(); await page.evaluate(() => debugDepart(1));
  await page.waitForFunction(() => debugFindTree('sapling') !== null);
  const treesBefore = await state();
  const visibleTree = await page.evaluate(() => debugFindTree('sapling'));
  const timberYield = await page.evaluate(() => TREE_CONFIG.saplingTimberYield);
  check('Young and large trees grow separately on the starting island', treesBefore.trees.filter(tree => tree.kind === 'sapling').length === 6 && treesBefore.trees.filter(tree => tree.kind === 'large').length === 2);
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-trees.png'), fullPage: true });
  await page.mouse.click(visibleTree.x, visibleTree.y);
  const treeChopped = await state();
  check('Canvas chop spends one fuel and adds timber to expedition haul', treeChopped.expedition.fuel === treesBefore.expedition.fuel - 1 && treeChopped.player.inventory.timber === timberYield && treeChopped.expedition.haul.timber === timberYield && treeChopped.trees.find(tree => tree.id === visibleTree.id).chopped);
  const choppedInventory = JSON.stringify(treeChopped.player.inventory);
  await page.evaluate(id => { debugChop(id); debugSave(); }, visibleTree.id);
  check('Repeated chop cannot award timber twice', JSON.stringify((await state()).player.inventory) === choppedInventory);
  await page.reload();
  check('Chopped tree and timber survive reload', (await state()).trees.find(tree => tree.id === visibleTree.id).chopped && JSON.stringify((await state()).player.inventory) === choppedInventory);
  await page.evaluate(() => { debugReturn(); debugAcknowledgeResult(); });
  const timberSale = await page.evaluate(() => ITEMS.timber.saleValue);
  const beforeTimberSale = (await state()).player.coins;
  await page.evaluate(() => debugSellAll());
  check('Port sale converts timber to coins', timberSale > 0 && (await state()).player.coins === beforeTimberSale + timberSale * timberYield && !(await state()).player.inventory.timber);

  await fresh(); await page.evaluate(() => { debugDepart(1); player.range = RANGE_LEVELS.length - 1; });
  await page.waitForFunction(() => debugFindLargeTreeBlock('leaf') !== null && debugFindLargeTreeBlock('wood') !== null);
  const leafBlock = await page.evaluate(() => debugFindLargeTreeBlock('leaf'));
  const beforeLeafChop = await state();
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-large-tree.png'), fullPage: true });
  await page.mouse.click(leafBlock.x, leafBlock.y);
  const afterLeafChop = await state();
  check('Large-tree leaf removes one block for one fuel and no timber even with range upgrade', afterLeafChop.expedition.fuel === beforeLeafChop.expedition.fuel - 1 && !afterLeafChop.player.inventory.timber && afterLeafChop.trees.find(tree => tree.id === leafBlock.treeId).removedBlocks.length === 1 && !afterLeafChop.trees.find(tree => tree.id === leafBlock.treeId).chopped);
  await page.waitForFunction(() => debugFindLargeTreeBlock('wood') !== null);
  const woodBlock = await page.evaluate(() => debugFindLargeTreeBlock('wood'));
  const largeBlockTimberYield = await page.evaluate(() => TREE_CONFIG.largeBlockTimberYield);
  await page.mouse.click(woodBlock.x, woodBlock.y);
  const afterWoodChop = await state();
  check('Large-tree wood removes one block and yields two timber', afterWoodChop.expedition.fuel === beforeLeafChop.expedition.fuel - 2 && afterWoodChop.player.inventory.timber === largeBlockTimberYield && afterWoodChop.trees.find(tree => tree.id === woodBlock.treeId).removedBlocks.includes(woodBlock.blockId));
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-large-tree-partial.png'), fullPage: true });
  const partialLargeState = JSON.stringify(afterWoodChop.trees.find(tree => tree.id === woodBlock.treeId));
  await page.evaluate(() => debugSave()); await page.reload();
  check('Partially chopped large tree stays partial after reload', JSON.stringify((await state()).trees.find(tree => tree.id === woodBlock.treeId)) === partialLargeState && (await state()).player.inventory.timber === largeBlockTimberYield);
  const completeLargeTree = await page.evaluate(treeId => {
    const tree = trees.find(entry => entry.id === treeId); expedition.fuel = 100; player.range = RANGE_LEVELS.length - 1;
    let guard = 30;
    while (!tree.chopped && guard-- > 0) { renderIslandLayer(); const target = findVisibleLargeTreeBlock(tree.id); if (!target || !chopTreeBlock(tree.id, target.blockId, target)) break; }
    return { tree: JSON.parse(JSON.stringify(tree)), fuel: expedition.fuel, timber: have('timber'), treesChopped: expedition.treesChopped, blockCount: treeBoxes('large').length };
  }, woodBlock.treeId);
  check('Removing all large-tree blocks completes it once with six total timber', completeLargeTree.tree.chopped && completeLargeTree.tree.removedBlocks.length === completeLargeTree.blockCount && completeLargeTree.timber === largeBlockTimberYield * 3 && completeLargeTree.treesChopped === 1);

  await fresh(); await page.evaluate(() => debugDepart(1));
  await page.waitForFunction(() => debugFindTree() !== null);
  const treeLayoutA = JSON.stringify((await state()).trees.map(tree => [tree.kind, tree.cellIndex]));
  await fresh(); await page.evaluate(() => debugDepart(1));
  await page.waitForFunction(() => debugFindTree() !== null);
  const treeLayoutB = JSON.stringify((await state()).trees.map(tree => [tree.kind, tree.cellIndex]));
  check('Tree placement repeats for the same seed and trip', treeLayoutA === treeLayoutB);
  await page.evaluate(() => { expedition.fuel = 1; debugChop(debugFindTree().id); });
  check('Last-fuel chop records timber before return notice', (await state()).expedition.phase === 'exploring' && (await state()).expedition.haul.timber === timberYield && await page.locator('#fuel-notice').isVisible());
  await page.evaluate(() => debugAcknowledgeFuelNotice());
  check('Last-fuel chop reaches result after notice confirmation', (await state()).expedition.phase === 'result');

  for (const seed of [0, 1, 777, 12345]) {
    await page.goto(pathToFileURL(path.join(here, 'index.html')).href + `?seed=${seed}&fresh=1`);
    const generation = await page.evaluate(() => {
      const definingMaterials = ['copper', 'crystal', 'iron', 'gold', 'obsidian', 'starcore'];
      return definingMaterials.map((material, index) => { generateIsland(index + 1); placeCreatures(); placeTrees(); return { island: index + 1, material, count: debugState().counts[material] || 0, youngTrees: trees.filter(tree => tree.kind === 'sapling').length, largeTrees: trees.filter(tree => tree.kind === 'large').length }; });
    });
    check(`Seed ${seed}: every destination contains its defining resource`, generation.every(item => item.count > 0), JSON.stringify(generation));
    check(`Seed ${seed}: every destination grows young and large trees`, generation.every(item => item.youngTrees >= 3 && item.largeTrees >= 1), JSON.stringify(generation.map(item => ({ island: item.island, youngTrees: item.youngTrees, largeTrees: item.largeTrees }))));
  }
  await fresh();
  await page.locator('#port-debug').click();
  check('Port debug menu names current save slot', await page.locator('#debug-panel').isVisible() && (await page.locator('#debug-slot').textContent()).includes('777') && (await page.locator('#debug-slot').textContent()).includes('独立テスト枠'));
  await page.screenshot({ path: path.join(artifactDirectory, 'mobile-debug-menu.png'), fullPage: true });
  await page.locator('#btn-debug-close').click();
  const normalSaveSentinel = 'other slot must survive debug reset';
  await page.evaluate(value => {
    localStorage.setItem(SAVE_KEY_PREFIX + worldSeed, value);
    debugGrant('scrap', 9); player.coins = 41; debugDepart(1); debugSave();
  }, normalSaveSentinel);
  await page.locator('#btn-debug').click();
  check('Expedition debug menu opens without spending fuel', await page.locator('#debug-panel').isVisible() && (await state()).expedition.fuel === 60);
  await page.locator('#btn-debug-reset').click();
  current = await state();
  check('Debug reset clears current save and returns to initial port', current.expedition.phase === 'base' && current.player.coins === 0 && Object.keys(current.player.inventory).length === 0 && current.expedition.routeLevel === 0 && current.tripSerial === 0);
  check('Debug reset leaves another save slot intact', await page.evaluate(value => localStorage.getItem(SAVE_KEY_PREFIX + worldSeed) === value, normalSaveSentinel));
  await page.reload();
  check('Debug reset persists after reload', (await state()).expedition.phase === 'base' && (await state()).player.coins === 0 && (await state()).tripSerial === 0);
  await page.evaluate(() => localStorage.removeItem(SAVE_KEY_PREFIX + worldSeed));
  check('No runtime or resource errors', errors.length === 0, errors.join(' | '));
} catch (error) {
  failures.push(error.stack || error.message);
} finally {
  await browser.close();
}
console.log(`Screenshots: ${artifactDirectory}`);
if (failures.length) { console.error(failures.join('\n')); process.exitCode = 1; }
else console.log('All expedition regressions passed.');
