// -----------------------------------------------------------------
// Dragon Tide のヘッドレス再生（同じシード・同じ時計で決定的に回す）
//
//   node tools/dt-headless.mjs [--seed 12345] [--ticks 20000] [--species fire] [--every 500] [--advance-every 0] [--file prototypes/dragon-tide/index.html]
//
// オートプレイでランを回し、一定間隔ごとにゲーム状態の指紋（ハッシュ）を出す。
// リファクタリングの前後で同じ引数の出力が一致すれば「挙動を変えていない」と言える。
// 時計（performance.now / Date.now）とループ（setInterval）を差し替えて 1 歩ずつ進めるので、
// 実機の速さや背景タブの間引きに左右されない。
// -----------------------------------------------------------------
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
function argValue(name, fallback) {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback;
}
const seed = argValue("seed", "12345");
const totalTicks = Number(argValue("ticks", "20000"));
const species = argValue("species", "fire");
const reportEvery = Number(argValue("every", "500"));
const file = path.resolve(REPO_ROOT, argValue("file", "prototypes/dragon-tide/index.html"));
// 指定すると、この歩数ごとにデバッグの「次の警戒度へ」を押す（1つの地域に留まらず、ステージクリア・店・地域選びまで通す）
const advanceEvery = Number(argValue("advance-every", "0"));
// 固定歩幅。ゲーム側の BASE_CFG.fixedStepMs と同じ 16ms で刻む
const STEP_MS = 16;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e && e.stack || e)));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });

await page.addInitScript(() => {
  // 時計を手で進める。起動時刻は固定（Date.now をシードに使う箇所があっても ?seed= で上書きされる）
  let fakeNow = 1000;
  const epoch = Date.UTC(2026, 0, 1);
  performance.now = () => fakeNow;
  Date.now = () => epoch + fakeNow;
  // タイマーも全部この時計に載せる。本物の setTimeout / requestAnimationFrame が残っていると、
  // 実行の速さ次第で発火する歩がずれ（ステージクリア後の演出など）、同じシードでも結果が揺れる
  let timerSeq = 1;
  const timers = new Map();   // id -> { at, fn, args, every }
  const addTimer = (fn, ms, args, every) => {
    const id = timerSeq++;
    timers.set(id, { at: fakeNow + Math.max(0, Number(ms) || 0), fn, args, every, seq: id });
    return id;
  };
  window.__dtTicks = [];
  window.setTimeout = (fn, ms, ...args) => addTimer(fn, ms, args, 0);
  window.clearTimeout = (id) => { timers.delete(id); };
  window.setInterval = (fn, ms, ...args) => {
    // ゲームループ（16ms 以上の間隔）は捕まえて、歩ごとに自分で呼ぶ
    if (ms >= 16 && window.__dtTicks.length === 0) { window.__dtTicks.push(fn); return 0; }
    return addTimer(fn, ms, args, Math.max(1, Number(ms) || 1));
  };
  window.clearInterval = (id) => { timers.delete(id); };
  let rafQueue = [];
  window.requestAnimationFrame = (fn) => { const id = timerSeq++; rafQueue.push({ id, fn }); return id; };
  window.cancelAnimationFrame = (id) => { rafQueue = rafQueue.filter(r => r.id !== id); };
  const runDue = () => {
    for (;;) {
      let next = null;
      for (const [id, t] of timers) if (t.at <= fakeNow && (!next || t.at < next[1].at || (t.at === next[1].at && t.seq < next[1].seq))) next = [id, t];
      if (!next) break;
      const [id, t] = next;
      if (t.every) { t.at += t.every; t.seq = timerSeq++; } else timers.delete(id);
      if (typeof t.fn === "function") t.fn(...t.args);
    }
  };
  window.__dtStep = (ms) => {
    fakeNow += ms;
    runDue();
    for (const fn of window.__dtTicks) fn();
    const frame = rafQueue; rafQueue = [];
    for (const r of frame) r.fn(fakeNow);
  };
  try { localStorage.clear(); } catch (e) { /* 無くてよい */ }
});

const url = pathToFileURL(file).href + `?seed=${encodeURIComponent(seed)}`;
await page.goto(url);
// 起動（画像の読み込み待ち）は本物の時間で進むので、ゲームループが登録されるまで外から待つ
for (let waited = 0; !(await page.evaluate(() => window.__dtTicks.length > 0)); waited += 100) {
  if (waited > 60000) throw new Error("ゲームループが始まらなかった");
  await new Promise((resolve) => setTimeout(resolve, 100));
}

await page.evaluate((sp) => { startAutoplay(sp); }, species);

const fingerprint = () => page.evaluate(() => {
  // 文字列に畳んで FNV-1a。小数は丸めてから（浮動小数の表示の揺れを避けるため 3 桁）
  let h = 0x811C9DC5;
  const feed = (v) => { const s = String(v); for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193); } };
  const r = (x) => Math.round(x * 1000);
  feed(gameState); feed(currentStage); feed(runStageIndex); feed(playerLevel); feed(flockSpecies);
  for (let i = 0; i < N; i++) { feed(r(px[i])); feed(r(py[i])); feed(boidDead[i]); feed(r(boidHp[i])); }
  let alive = 0;
  for (const s of settlements) { if (!s.fallen) alive++; feed(s.fallen ? 1 : 0); feed(r(s.hp || 0)); }
  feed(movers.length);
  for (const m of movers) { feed(r(m.x || 0)); feed(r(m.y || 0)); feed(r(m.hp || 0)); }
  return { hash: (h >>> 0).toString(16).padStart(8, "0"), state: gameState, stage: runStageIndex, level: playerLevel, dragons: N, aliveBuildings: alive, movers: movers.length };
});

const started = Date.now();
for (let t = 1; t <= totalTicks; t++) {
  await page.evaluate((ms) => window.__dtStep(ms), STEP_MS);
  if (advanceEvery > 0 && t % advanceEvery === 0) await page.evaluate(() => debugAdvanceStage());
  if (t % reportEvery === 0) {
    const fp = await fingerprint();
    console.log(`tick ${String(t).padStart(6)}  ${fp.hash}  ${fp.state} stage=${fp.stage} lv=${fp.level} dragons=${fp.dragons} buildings=${fp.aliveBuildings} movers=${fp.movers}`);
  }
  if (errors.length) break;
}
console.error(`elapsed ${((Date.now() - started) / 1000).toFixed(1)}s`);
if (errors.length) { console.log("ERRORS:\n" + errors.join("\n")); process.exitCode = 1; }
await browser.close();
