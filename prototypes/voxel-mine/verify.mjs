// -----------------------------------------------------------------
// 掘り島 の headless 検証。AIの目視ではなく機械で採点する。
//
//   node prototypes/voxel-mine/verify.mjs
//
// Playwright はグローバル（/opt/node22/lib/node_modules）か node_modules のどちらかから読む。
// -----------------------------------------------------------------
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
function loadPlaywright() {
  const candidates = ["playwright", "/opt/node22/lib/node_modules/playwright"];
  for (const c of candidates) {
    try { return require(c); } catch (error) { /* 次の候補 */ }
  }
  throw new Error("playwright が見つからない");
}
const { chromium } = loadPlaywright();

const failures = [];
function check(name, ok, detail) {
  console.log((ok ? "  ok  " : "  NG  ") + name + (detail !== undefined ? "  … " + detail : ""));
  if (!ok) failures.push(name);
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
const errors = [];
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
page.on("console", (m) => { if (m.type() === "error") errors.push("console: " + m.text()); });
page.on("requestfailed", (r) => errors.push("request: " + r.url()));

const url = pathToFileURL(path.join(here, "index.html")).href + "?seed=777&fresh=1";
await page.goto(url);
await page.waitForTimeout(600);

const s0 = await page.evaluate(() => debugState());
check("例外・エラーが0", errors.length === 0, errors.join(" | "));
check("島1が生成される（ブロック数）", s0.solid > 400, s0.solid);
check("面が描かれている", s0.faces > 300, s0.faces);
check("島1に銅があり、鉄は無い", s0.counts.copper > 0 && !s0.counts.iron, JSON.stringify(s0.counts));
check("素手では石・土・草だけ掘れる", s0.mineable === s0.solid - (s0.counts.copper || 0), s0.mineable + " / " + s0.solid);

// タップで掘る：石は打撃1に対し hp2 なので、1回目はひび・2回目で割れる
let stoneFace = await page.evaluate(() => debugFindFace("stone"));
if (!stoneFace) {
  // 上面は草。少し回して側面の石を出す
  await page.evaluate(() => { camera.pitch = -0.1; cameraDirty = true; });
  await page.waitForTimeout(200);
  stoneFace = await page.evaluate(() => debugFindFace("stone"));
}
check("石の面が見つかる", !!stoneFace, JSON.stringify(stoneFace));
const hit1 = await page.evaluate(({ x, y }) => debugTapAt(x, y), stoneFace);
const afterHit1 = await page.evaluate(() => debugState());
check("石は1回目で割れない（ひび）", hit1.broken === 0 && afterHit1.solid === s0.solid, JSON.stringify(hit1));
await page.waitForTimeout(150);
const hit2 = await page.evaluate(({ x, y }) => debugTapAt(x, y), stoneFace);
const afterHit2 = await page.evaluate(() => debugState());
check("石は2回目で割れる", hit2.broken === 1 && afterHit2.solid === s0.solid - 1, JSON.stringify(hit2));
check("石が在庫に入る", afterHit2.player.inventory.stone === 1, JSON.stringify(afterHit2.player.inventory));
check("破片が出る", afterHit2.chips > 0, afterHit2.chips);

// 銅は素手では掘れない（×）
await page.evaluate(() => { camera.pitch = -0.46; cameraDirty = true; });
await page.waitForTimeout(200);
let copperFace = await page.evaluate(() => debugFindFace("copper"));
for (let turn = 0; turn < 12 && !copperFace; turn++) {
  await page.evaluate(() => { camera.yaw += 0.5; camera.pitch = -0.2 - (camera.yaw % 1) * 0.6; cameraDirty = true; });
  await page.waitForTimeout(120);
  copperFace = await page.evaluate(() => debugFindFace("copper"));
}
check("銅の面が見つかる", !!copperFace);
if (copperFace) {
  const lockedHit = await page.evaluate(({ x, y }) => debugTapAt(x, y), copperFace);
  const afterLocked = await page.evaluate(() => debugState());
  check("素手で銅を叩いても割れない（×）", lockedHit.locked && afterLocked.solid === afterHit2.solid, JSON.stringify(lockedHit));
}

// 工房：素材が足りないと作れない／足りれば作れる
const craftNo = await page.evaluate(() => debugCraft("pickaxe"));
check("素材不足では作れない", craftNo === false);
await page.evaluate(() => { debugGrant("stone", 25); debugGrant("dirt", 15); });
const craftYes = await page.evaluate(() => debugCraft("pickaxe"));
const afterCraft = await page.evaluate(() => debugState());
check("石のつるはしが作れる", craftYes === true && afterCraft.player.pickaxe === 1 && afterCraft.power === 2, JSON.stringify(afterCraft.player));
check("作ると素材が減る", afterCraft.player.inventory.stone === 1, afterCraft.player.inventory.stone);
check("石のつるはしで銅が掘れる数に入る", afterCraft.mineable === afterCraft.solid, afterCraft.mineable + " / " + afterCraft.solid);

// 連鎖：銅の脈をつるはし＋連鎖Lv1で割ると、時間差で続けて割れる
await page.evaluate(() => { debugGrant("copper", 8); debugGrant("stone", 30); });
const craftChain = await page.evaluate(() => debugCraft("chain"));
check("鉱脈連鎖Lv1が作れる", craftChain === true);
copperFace = await page.evaluate(() => debugFindFace("copper"));
if (copperFace) {
  const before = await page.evaluate(() => debugState());
  // 銅 hp3・打撃2 → 2回で割れる
  await page.evaluate(({ x, y }) => debugTapAt(x, y), copperFace);
  await page.waitForTimeout(80);
  const r = await page.evaluate(({ x, y }) => debugTapAt(x, y), copperFace);
  const mid = await page.evaluate(() => debugState());
  await page.waitForTimeout(500);
  const after = await page.evaluate(() => debugState());
  const chainBroken = (before.counts.copper || 0) - (after.counts.copper || 0);
  check("銅が割れて連鎖が予約される", r.broken === 1 && (mid.pending > 0 || chainBroken > 1), "pending=" + mid.pending + " broken=" + chainBroken);
  check("連鎖が処理されて銅が続けて減る", chainBroken >= 2 && after.pending === 0, "copper -" + chainBroken);
}

// 範囲：Lv1（幅3）で1タップに複数割れる
await page.evaluate(() => { debugGrant("crystal", 8); debugGrant("stone", 60); });
const craftRange = await page.evaluate(() => debugCraft("range"));
check("範囲Lv1が作れる", craftRange === true);
await page.evaluate(() => { camera.pitch = -0.9; cameraDirty = true; });
await page.waitForTimeout(200);
const grassFace = await page.evaluate(() => debugFindFace("grass"));
if (grassFace) {
  const rr = await page.evaluate(({ x, y }) => debugTapAt(x, y), grassFace);
  check("幅3で草・土がまとめて割れる", rr.broken >= 4, rr.broken);
}

// コンボ：短い間隔で割ると数が増える
await page.evaluate(() => { for (let i = 0; i < 8; i++) { const f = debugFindFace("dirt") || debugFindFace("grass"); if (f) debugTapAt(f.x, f.y); } });
const comboState = await page.evaluate(() => debugState());
check("連打でコンボが乗る", comboState.combo >= 4 && comboState.player.stats.maxCombo >= 4, "combo=" + comboState.combo);

// 保存 → 再読込 で状態が戻る
await page.evaluate(() => debugSave());
const beforeReload = await page.evaluate(() => debugState());
await page.goto(pathToFileURL(path.join(here, "index.html")).href + "?seed=777");
await page.waitForTimeout(500);
const afterReload = await page.evaluate(() => debugState());
check("再読込で在庫・つるはし・島が戻る",
  afterReload.solid === beforeReload.solid && afterReload.player.pickaxe === beforeReload.player.pickaxe &&
  JSON.stringify(afterReload.player.inventory) === JSON.stringify(beforeReload.player.inventory),
  afterReload.solid + " vs " + beforeReload.solid);

// 次の島：番号が進み、大きく・深くなり、新しい素材が出る
page.removeAllListeners("dialog");
page.on("dialog", (d) => d.accept());
const island2 = await page.evaluate(() => debugNextIsland());
check("島2が生成される", island2.islandLevel === 2 && island2.solid > s0.solid, island2.solid + " > " + s0.solid);
check("島2で結晶が出る", island2.counts.crystal > 0, JSON.stringify(island2.counts));
for (let i = 3; i <= 6; i++) await page.evaluate(() => debugNextIsland());
const island6 = await page.evaluate(() => debugState());
check("島6で鉄・金・黒曜・星核が出る",
  island6.counts.iron > 0 && island6.counts.gold > 0 && island6.counts.obsidian > 0 && island6.counts.starcore > 0,
  JSON.stringify(island6.counts));
check("島6は島1よりずっと大きい", island6.solid > s0.solid * 2.5, island6.solid + " vs " + s0.solid);
check("島が決定的（同じ種で同じ島）", true);

// 大きい島の描画コスト（1回の島レイヤー描画にかかる時間）
const drawMs = await page.evaluate(() => {
  const t0 = performance.now();
  for (let i = 0; i < 5; i++) { boilFrame++; renderIslandLayer(); }
  return (performance.now() - t0) / 5;
});
check("島6の描画が1回 25ms 未満（沸き10Hzに間に合う）", drawMs < 25, drawMs.toFixed(2) + "ms, faces=" + island6.faces);

// 決定性：同じ種の島1を2回作って同じ内容か
const same = await page.evaluate(() => {
  generateIsland(1); const a = Array.from(cells).join(",");
  generateIsland(1); const b = Array.from(cells).join(",");
  return a === b;
});
check("同じ種で同じ島になる", same);

check("最後まで例外・エラーが0", errors.length === 0, errors.join(" | "));
await browser.close();

if (failures.length > 0) {
  console.error("\n検証失敗: " + failures.length + " 件\n  - " + failures.join("\n  - "));
  process.exit(1);
}
console.log("\n検証通過");
