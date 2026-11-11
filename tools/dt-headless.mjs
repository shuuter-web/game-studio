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
import { fileURLToPath } from "node:url";
import { openGame } from "./dt-harness.mjs";

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
// 指定すると CPU プロファイルを取り、自分の時間（self time）が長い関数を上から出す（毎フレームの重い処理を探すため）
const profileTop = Number(argValue("profile", "0"));
// 指定すると、報告のたびにこの式をページで評価して一緒に出す（調査用。例 --probe "movers.length"）
const probeExpr = argValue("probe", "");
// 指定すると、ランが始まった直後にその時代・地域へ差し替える（例 --stage 3,8 ＝時代4の大都会。地域の番号は STAGE_SHAPES の順）
const stageArg = argValue("stage", "");
// 固定歩幅。ゲーム側の BASE_CFG.fixedStepMs と同じ 16ms で刻む
const STEP_MS = 16;

const { browser, page, errors } = await openGame({ file, seed });

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

if (stageArg) {
  const [era, shape] = stageArg.split(",").map(Number);
  for (let guard = 0; !(await page.evaluate(() => gameState === "playing")); guard++) {
    if (guard > 5000) throw new Error("ランが始まらなかった");
    await page.evaluate((ms) => window.__dtStep(ms), STEP_MS);
  }
  await page.evaluate(([e, sh]) => debugStartStage(e, sh), [era, shape]);
}

let cdp = null;
if (profileTop > 0) {
  cdp = await page.context().newCDPSession(page);
  await cdp.send("Profiler.enable");
  await cdp.send("Profiler.setSamplingInterval", { interval: 200 });
  await cdp.send("Profiler.start");
}
const started = Date.now();
for (let t = 1; t <= totalTicks; t++) {
  await page.evaluate((ms) => window.__dtStep(ms), STEP_MS);
  if (advanceEvery > 0 && t % advanceEvery === 0) await page.evaluate(() => debugAdvanceStage());
  if (t % reportEvery === 0) {
    const fp = await fingerprint();
    const probed = probeExpr ? `  probe=${JSON.stringify(await page.evaluate((expr) => (0, eval)(expr), probeExpr))}` : "";
    console.log(`tick ${String(t).padStart(6)}  ${fp.hash}  ${fp.state} stage=${fp.stage} lv=${fp.level} dragons=${fp.dragons} buildings=${fp.aliveBuildings} movers=${fp.movers}${probed}`);
  }
  if (errors.length) break;
}
if (cdp) {
  const { profile } = await cdp.send("Profiler.stop");
  // ノードごとの標本数を、関数（名前＋行）ごとの自分の時間に畳む
  const byId = new Map(profile.nodes.map((n) => [n.id, n]));
  const hits = new Map();
  for (const id of profile.samples) hits.set(id, (hits.get(id) || 0) + 1);
  const selfByFn = new Map();
  let total = 0;
  for (const [id, count] of hits) {
    const frame = byId.get(id).callFrame;
    const key = `${frame.functionName || "(anonymous)"}:${frame.lineNumber + 1}`;
    selfByFn.set(key, (selfByFn.get(key) || 0) + count);
    total += count;
  }
  const rows = [...selfByFn].sort((a, b) => b[1] - a[1]).slice(0, profileTop);
  console.log(`--- profile (self time, ${total} samples) ---`);
  for (const [key, count] of rows) console.log(`${(count / total * 100).toFixed(2).padStart(6)}%  ${key}`);
}
console.error(`elapsed ${((Date.now() - started) / 1000).toFixed(1)}s`);
if (errors.length) { console.log("ERRORS:\n" + errors.join("\n")); process.exitCode = 1; }
await browser.close();
