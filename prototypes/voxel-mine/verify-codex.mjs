// Voyage Codex acceptance and regression checks for v0.8.1.
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
const page = await browser.newPage({ viewport: { width: 375, height: 667 }, deviceScaleFactor: 1 });
const failures = [], errors = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
const check = (name, condition, detail = '') => { console.log(`${condition ? 'PASS' : 'FAIL'} ${name} ${detail}`); if (!condition) failures.push(name); };
const url = pathToFileURL(path.join(here, 'index.html')).href + '?seed=81081&fresh=codex';
const artifacts = path.resolve(process.env.VOXEL_ARTIFACT_DIR || path.join(here, '../../artifacts/voxel-mine'));
await mkdir(artifacts, { recursive: true });
async function fresh() {
  await page.goto(url);
  await page.waitForFunction(() => typeof debugOpenCodex === 'function');
  await page.evaluate(() => resetGame());
}
const gameplayState = () => page.evaluate(() => {
  const savedPlayer = JSON.parse(JSON.stringify(player));
  delete savedPlayer.codexSeen; delete savedPlayer.codexRead; delete savedPlayer.codexFirst;
  return JSON.stringify({ player: savedPlayer, expedition, tripSerial, creatures, trees,
    cells: bytesToBase64(cells), damage: bytesToBase64(damage), combo, pendingBreaks });
});
async function layout() {
  return page.evaluate(() => {
    const cards = [...document.querySelectorAll('.codex-card')];
    const columns = new Set(cards.map(card => Math.round(card.getBoundingClientRect().left))).size;
    const controls = [...document.querySelectorAll('#codex button')].filter(button => button.getBoundingClientRect().width > 0);
    return { columns, overflow: document.documentElement.scrollWidth > innerWidth || document.getElementById('codex').scrollWidth > innerWidth,
      undersized: controls.filter(button => { const rect = button.getBoundingClientRect(); return rect.width < 44 || rect.height < 44; }).map(button => button.textContent.trim()) };
  });
}

try {
  await fresh();
  check('Version is v0.8.1', await page.evaluate(() => GAME_VERSION === 'v0.8.1'));
  check('Codex entrance is in the port screen only', await page.evaluate(() => {
    const button = document.getElementById('btn-open-codex');
    return button && button.closest('#base') && !button.closest('#game') && !button.closest('#result');
  }));
  const beforeOpen = await gameplayState();
  await page.locator('#btn-open-codex').focus();
  await page.locator('#btn-open-codex').click();
  check('Port entrance opens and close control receives focus', await page.evaluate(() => !document.getElementById('codex').hidden && document.activeElement.id === 'btn-codex-close'));
  check('Browsing the index does not mutate gameplay state', await gameplayState() === beforeOpen);

  const catalog = await page.evaluate(() => ({ categories: CODEX_CATEGORIES.map(category => ({ ...category, entries: codexEntries(category.id) })), keys: allCodexKeys(), progress: document.getElementById('codex-progress').textContent }));
  const expectedTotal = catalog.categories.reduce((sum, category) => sum + category.entries.length, 0);
  check('Six categories and exact unique total are reported', catalog.categories.length === 6 && catalog.keys.length === expectedTotal && new Set(catalog.keys).size === expectedTotal && catalog.progress.includes(`登録項目 ${expectedTotal}件`), JSON.stringify(catalog.categories.map(category => [category.id, category.entries.length])));
  check('Progress reports every category count', catalog.categories.every(category => catalog.progress.includes(`${category.name} ${category.entries.length}`)), catalog.progress);

  let complete = true, detailMatches = true;
  for (const category of catalog.categories) {
    await page.locator(`[data-codex-tab="${category.id}"]`).click();
    const cards = await page.locator('.codex-card').allTextContents();
    complete &&= cards.length === category.entries.length && cards.every(text => text.trim() && !text.includes('???'));
    for (let index = 0; index < category.entries.length; index++) {
      const entry = category.entries[index];
      await page.locator(`[data-codex-entry="${entry.id}"]`).click();
      const rendered = await page.evaluate(() => ({ name: document.querySelector('.codex-detail h2')?.textContent, flavor: document.querySelector('.codex-detail p')?.textContent,
        facts: [...document.querySelectorAll('.codex-detail dt')].map((term, i) => [term.textContent, document.querySelectorAll('.codex-detail dd')[i].textContent]) }));
      detailMatches &&= rendered.name === entry.name && rendered.flavor === entry.flavor && entry.facts.every((fact, i) => JSON.stringify(rendered.facts[i]) === JSON.stringify(fact));
      await page.locator('#btn-codex-back').click();
      detailMatches &&= await page.evaluate(id => document.activeElement?.dataset.codexEntry === id, entry.id);
    }
  }
  check('All entries show name, description and no masked placeholders before discovery', complete);
  check('Every detail sheet matches its source data and returns focus to its card', detailMatches);

  await page.locator('[data-codex-tab="blocks"]').click();
  await page.screenshot({ path: path.join(artifacts, 'codex-list-v081.png'), fullPage: true });
  await page.locator('.codex-card').first().click();
  await page.screenshot({ path: path.join(artifacts, 'codex-detail-v081.png'), fullPage: true });
  await page.keyboard.press('Escape');
  check('First Escape leaves detail open state at list', await page.evaluate(() => !document.getElementById('codex').hidden && debugCodexState().detailId === null && document.activeElement.id === 'btn-codex-close'));
  await page.keyboard.press('Escape');
  check('Second Escape closes codex and restores entrance focus', await page.evaluate(() => document.getElementById('codex').hidden && document.activeElement.id === 'btn-open-codex'));

  await page.evaluate(() => debugDepart(1));
  check('Codex rejects opening during expedition', await page.evaluate(() => !debugOpenCodex() && document.getElementById('codex').hidden));
  await page.evaluate(() => debugReturn());
  check('Codex rejects opening on result screen', await page.evaluate(() => expedition.phase === 'result' && !debugOpenCodex() && document.getElementById('codex').hidden));
  await page.evaluate(() => debugAcknowledgeResult());

  await page.evaluate(() => debugOpenCodex('blocks'));
  let measured = await layout();
  check('375x667 uses two columns without horizontal overflow', measured.columns === 2 && !measured.overflow, JSON.stringify(measured));
  check('Codex controls meet 44px touch target', measured.undersized.length === 0, JSON.stringify(measured.undersized));
  await page.setViewportSize({ width: 800, height: 800 }); measured = await layout();
  check('Wide layout uses three columns', measured.columns === 3 && !measured.overflow, JSON.stringify(measured));
  await page.setViewportSize({ width: 1000, height: 800 }); measured = await layout();
  check('Very wide layout uses four columns', measured.columns === 4 && !measured.overflow, JSON.stringify(measured));
  await page.evaluate(() => closeCodex());

  // Registration hooks: manual/automatic terrain, both tree block types, capture,
  // first visible enemy, frame/trait grant, and material acquisition.
  await fresh();
  const hookResult = await page.evaluate(() => {
    debugDepart(1); cells.fill(0); damage.fill(0); pendingBreaks.length = 0; creatures.length = 0; trees.length = 0;
    const manual = cellIndex(2, 2, 2), automatic = cellIndex(3, 2, 2), stake = cellIndex(4, 2, 2);
    cells[manual] = M_GRASS; cells[automatic] = M_STONE; solidCount = 2; player.pickaxe = 5; expedition.fuel = 20; rebuildSurface();
    debugMineCell(manual);
    const gear = debugGrantGear('autoDrill'); player.equippedGearIds = [gear.id]; expedition.gearRuntime = { stakes: [{ gearId: gear.id, cellIndex: stake, placedTurn: expedition.turns }], autoResolvedTurn: expedition.turns };
    for (let turn = 0; turn < 5 && cells[automatic]; turn++) { beginAction(); completeAction(); nowSeconds += 100; processPendingBreaks(); }
    removeLargeTreeBlock({ id: 50, removedBlocks: [] }, 0); removeLargeTreeBlock({ id: 51, removedBlocks: [] }, 3);
    const creature = { id: 70, kind: 'bird', cellIndex: 0, captured: false, escaped: false }; creatures.push(creature);
    const realCreatureProjection = creatureProjection; creatureProjection = () => ({ id: 70, x: 1, y: 1, depth: 0 });
    const captured = captureCreature(70); creatureProjection = realCreatureProjection;
    debugGrant('copper', 1);
    expedition.routeLevel = 1; expedition.phase = 'base'; debugDepart(2); renderIslandLayer(); drawEnemyMarker(ctx);
    return { seen: Object.keys(player.codexSeen), frameId: gear.frameId, savedGear: { ...gear }, captured };
  });
  const requiredSeen = ['blocks:grass','blocks:stone','blocks:woodBlock','blocks:leafBlock','creatures:bird','enemies:ancientSentinel','gearFrames:prototype','traits:autoDrill','materials:copper'];
  check('All discovery hooks register their entries', requiredSeen.every(key => hookResult.seen.includes(key)), JSON.stringify(hookResult));
  check('Gear instances carry a valid frameId', hookResult.frameId === 'prototype' && hookResult.savedGear.frameId === 'prototype', JSON.stringify(hookResult.savedGear));

  await page.evaluate(() => { expedition.phase = 'base'; debugSave(); });
  const savedFlags = await page.evaluate(() => ({ seen: { ...player.codexSeen }, first: { ...player.codexFirst }, raw: JSON.parse(localStorage.getItem(saveKey())) }));
  check('Schema 10 stores codex history and gear frameId', savedFlags.raw.version === 10 && savedFlags.raw.player.gears.every(gear => typeof gear.frameId === 'string'));
  await page.reload(); await page.waitForFunction(() => typeof debugCodexState === 'function');
  check('Codex history survives save and reload', await page.evaluate(expected => JSON.stringify(player.codexSeen) === JSON.stringify(expected.seen) && JSON.stringify(player.codexFirst) === JSON.stringify(expected.first), savedFlags));
  await page.evaluate(() => resetGame());
  check('Reset clears discovery history but catalog remains fully visible', await page.evaluate(() => Object.keys(player.codexSeen).length === 0 && allCodexKeys().length === debugCodexState().entries && codexEntries('blocks').every(entry => entry.name && entry.flavor)));

  await page.evaluate(() => { const data = JSON.parse(localStorage.getItem(saveKey())); data.version = 9; data.player.coins = 999; localStorage.setItem(saveKey(), JSON.stringify(data)); });
  await page.reload(); await page.waitForFunction(() => typeof debugState === 'function');
  check('Invalid schema 9 resets to a fresh schema 10 save', await page.evaluate(() => player.coins === 0 && JSON.parse(localStorage.getItem(saveKey())).version === 10 && Object.keys(player.codexSeen).length === 0));
  check('No runtime errors', errors.length === 0, JSON.stringify(errors));
} finally { await browser.close(); }

if (failures.length) { console.error(`\n${failures.length} failed: ${failures.join(', ')}`); process.exitCode = 1; }
else console.log('\nAll voxel-mine v0.8.1 voyage codex checks passed.');
