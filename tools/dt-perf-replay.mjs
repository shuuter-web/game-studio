// -----------------------------------------------------------------
// Dragon Tide の重い場面を開き直して測る（案帳 DT-638）
//
//   node tools/dt-perf-replay.mjs --species fire --seed 3 --at-ms 1234000 [--frames 120] [--profile] [--shot heavy.png]
//        [--setup "式"] [--file prototypes/dragon-tide/index.html]
//
// dt-run-stats.mjs --perf が出した「重い場面」は、竜種・シード・ランの頭からの時刻で決まる。
// このツールは同じ始め方（オートプレイで竜種を決めて beginRun）でランを始め、その時刻まで描かずに早送りし、
// そこから --frames 歩だけ毎歩描いて、1歩のロジックと描画の本物の時間（平均・最大）を出す。
// --profile を付けると、その間の CPU の使い方（関数ごとの自分の時間の上位）を出す＝どこを直せば軽くなるかの見当を付ける。
// --shot でその場面の絵を撮る。
// ゲームの状態・乱数には触らない（描いても描かなくても同じランになる。dt-headless.mjs --render で確かめてある）。
// 時間は計測する機械で変わるので、直す前と後を同じ機械で比べる（直した写しは --file で渡す）。
// -----------------------------------------------------------------
import path from "node:path";
import { fileURLToPath } from "node:url";
import { openGame, stepMany } from "./dt-harness.mjs";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const arg = (name, fallback) => { const i = args.indexOf(`--${name}`); return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback; };
const file = path.resolve(REPO_ROOT, arg("file", "prototypes/dragon-tide/index.html"));
const species = arg("species", "fire");
const seed = arg("seed", "1");
const atMs = Number(arg("at-ms", "60000"));
const frames = Number(arg("frames", "120"));
const setupExpr = arg("setup", "");
const shot = arg("shot", "");
const profile = args.includes("--profile");
const STEP_MS = 16;
const CHUNK_STEPS = Math.round(1000 / STEP_MS);   // dt-run-stats と同じ区切りで進める（同じ時刻に着くため）
const PROFILE_TOP = 25;

const started = Date.now();
const { browser, page, errors } = await openGame({ file, seed, noRender: true });
try {
  // dt-run-stats.mjs の runOne と同じ始め方
  await page.evaluate((sp) => {
    startAutoplay(sp);
    const all = SPECIES_CHOICES.map((ch) => ch.species);
    const id = all.includes(sp) ? sp : all[Math.floor(autoRandom() * all.length)];
    beginRun(id);
  }, species);
  if (setupExpr) await page.evaluate((expr) => (0, eval)(expr), setupExpr);
  // その時刻まで描かずに早送り（dt-run-stats と同じく1秒ずつ）
  for (;;) {
    const t = await page.evaluate(() => performance.now() - runStartTime);
    if (t >= atMs) break;
    if (await page.evaluate(() => gameState === "all-clear" || gameState === "title")) { console.log("その時刻より前にランが終わった"); break; }
    await stepMany(page, CHUNK_STEPS, { stepMs: STEP_MS });
  }
  // ここから毎歩描いて測る
  await page.evaluate(() => {
    const real = window.__dtRealRender;
    window.__dtRenderMs = 0;
    window.render = function (...a) { const t0 = window.__dtRealNow(); const r = real.apply(this, a); window.__dtRenderMs += window.__dtRealNow() - t0; return r; };
    window.drawMinimap = window.__dtRealMinimap;
  });
  let cdp = null;
  if (profile) {
    cdp = await page.context().newCDPSession(page);
    await cdp.send("Profiler.enable");
    await cdp.send("Profiler.setSamplingInterval", { interval: 200 });
    await cdp.send("Profiler.start");
  }
  const res = await page.evaluate((n) => {
    const per = [];
    for (let k = 0; k < n; k++) {
      window.__dtRenderMs = 0;
      const t0 = window.__dtRealNow();
      window.__dtStep(16);
      const total = window.__dtRealNow() - t0;
      per.push({ logic: total - window.__dtRenderMs, render: window.__dtRenderMs });
    }
    const avg = (k) => per.reduce((a, p) => a + p[k], 0) / per.length;
    const max = (k) => Math.max(...per.map((p) => p[k]));
    const countOn = (arr) => { let c = 0; for (let i = 0; i < arr.length; i++) if (arr[i]) c++; return c; };
    let buildings = 0; for (const s of settlements) if (!s.fallen && !s.isBoss && !s._isWall) buildings++;
    return {
      version: GAME_VERSION, t: Math.round(performance.now() - runStartTime),
      logicAvg: avg("logic"), logicMax: max("logic"), renderAvg: avg("render"), renderMax: max("render"),
      scene: { stage: runStageNumber, era: CONTINENT_DEFS[runStageIndex] ? CONTINENT_DEFS[runStageIndex].name : "", shape: STRINGS.shapeNames[runShape],
        tier: powerTier + 1, flock: countFlockNow(), buildings, settlements: settlements.length, movers: movers.length,
        projectiles: countOn(projActive), particles: countOn(partActive), fires: countOn(fireActive), state: gameState },
    };
  }, frames);
  console.log(`${res.version} ${species} seed=${seed} 時刻 ${Math.floor(res.t / 60000)}:${String(Math.floor(res.t / 1000) % 60).padStart(2, "0")}（${frames}歩）`);
  console.log(`場面: ステージ${res.scene.stage}（${res.scene.era}／${res.scene.shape}）警戒度${res.scene.tier} 群れ${res.scene.flock} 建物${res.scene.buildings}/${res.scene.settlements} 敵${res.scene.movers} 弾${res.scene.projectiles} 火の粉${res.scene.particles} 火${res.scene.fires} ${res.scene.state}`);
  console.log(`1歩のロジック: 平均 ${res.logicAvg.toFixed(2)}ms 最大 ${res.logicMax.toFixed(2)}ms`);
  console.log(`1枚の描画:     平均 ${res.renderAvg.toFixed(2)}ms 最大 ${res.renderMax.toFixed(2)}ms`);
  if (cdp) {
    const { profile: prof } = await cdp.send("Profiler.stop");
    // 関数ごとの自分の時間（標本の数 × 間隔）。名前の無い関数は場所で示す
    const dt = prof.timeDeltas.reduce((a, b) => a + b, 0) / Math.max(1, prof.samples.length) / 1000;
    const byId = new Map(prof.nodes.map((nd) => [nd.id, nd]));
    const parentOf = new Map();
    for (const nd of prof.nodes) for (const c of nd.children || []) parentOf.set(c, nd.id);
    const where = (cf) => `${cf.functionName || "(無名)"} :${cf.lineNumber + 1}`;
    const hits = new Map();
    for (const id of prof.samples) {
      const nd = byId.get(id); const cf = nd.callFrame;
      // 描画の命令（restore・drawImage など）は場所を持たないので、呼んだゲームの関数を添える（どの描き方が重いかを見るため）
      let key = where(cf);
      if (!cf.url && !cf.functionName.startsWith("(")) {
        let p = parentOf.get(id);
        while (p !== undefined && !byId.get(p).callFrame.url) p = parentOf.get(p);
        key = `${cf.functionName}（${p !== undefined ? where(byId.get(p).callFrame) : "?"} から）`;
      }
      if (["(idle)", "(program)", "(garbage collector)"].includes(cf.functionName)) { hits.set(cf.functionName, (hits.get(cf.functionName) || 0) + 1); continue; }
      hits.set(key, (hits.get(key) || 0) + 1);
    }
    const total = prof.samples.length;
    console.log(`\nCPU の使い方（自分の時間の上位・行は index.html の行）`);
    [...hits.entries()].sort((a, b) => b[1] - a[1]).slice(0, PROFILE_TOP).forEach(([k, n]) =>
      console.log(`${(100 * n / total).toFixed(1).padStart(5)}%  ${(n * dt).toFixed(0).padStart(6)}ms  ${k}`));
  }
  if (shot) {
    await page.evaluate(() => window.__dtStep(16));
    await page.screenshot({ path: path.resolve(shot) });
    console.log(`絵: ${shot}`);
  }
  if (errors.length) console.log("エラー:", errors.slice(0, 3).join("\n"));
} finally {
  await browser.close();
}
console.error(`elapsed ${((Date.now() - started) / 1000).toFixed(0)}s`);
