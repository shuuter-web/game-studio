// -----------------------------------------------------------------
// Dragon Tide: 首都を落とすまでの時間を、決まった群れで測る（案帳 DT-594）
//
//   node tools/dt-capital-bench.mjs [--era 0] [--shape 0] [--species fire] [--flock 150] [--overflow 150]
//                                   [--seconds 20] [--seed 4242] [--pattern loop|dart] [--file …]
//
// 首都だけを残し（城壁・ほかの建物は陥落扱い）、首都は撃ってこずHP無限にして、
// 群れ（動く竜 --flock 体＋上限超えの竜 --overflow 体）で首都のまわりに輪を引き続け、入った傷を測る。
// 出すもの：1秒の傷・首都の最大HP・その傷で落とすまでの秒数（最大HP÷1秒の傷）。
// 動く敵・敵の弾は毎歩消し、群れは無敵にする（守りの強さではなく、群れの攻撃に対する首都の硬さを見るため）。
// 経験値・レベルアップは止める。強化カードの分は --setup "式" で入れる（例: --setup "stageCards.cat_shot=3"）
// -----------------------------------------------------------------
import path from "node:path";
import { fileURLToPath } from "node:url";
import { openGame } from "./dt-harness.mjs";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const argValue = (name, fallback) => { const i = args.indexOf(`--${name}`); return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback; };
const file = path.resolve(REPO_ROOT, argValue("file", "prototypes/dragon-tide/index.html"));
const ERA = Number(argValue("era", "0")), SHAPE = Number(argValue("shape", "0"));
const SPECIES = argValue("species", "fire");
const FLOCK = Number(argValue("flock", "150")), OVERFLOW = Number(argValue("overflow", "150"));
const MEASURE_S = Number(argValue("seconds", "20"));
const SEED = argValue("seed", "4242");
const PATTERN = argValue("pattern", "loop");
const SETUP = argValue("setup", "");
const STEP_MS = 16;              // ゲームの固定歩幅と同じ
const WARMUP_S = 5;              // 群れが首都に着いて輪に乗るまで（測らない）
const LOOP_MARGIN_PX = 70;       // 輪の半径＝首都の半径＋この余白
const LOOP_REDRAW_S = 5;
const DART_EVERY_S = 3;
const STROKE_STEP_PX = 24;

const { browser, page, errors } = await openGame({ file, seed: SEED });
try {
  const setup = await page.evaluate(({ ERA, SHAPE, SPECIES, FLOCK, OVERFLOW, SETUP }) => {
    debugUnlockAllContinents();
    window.addXp = () => {};
    window.queueLevelUp = () => {};
    window.render = () => {};
    window.drawMinimap = () => {};
    beginRun(SPECIES);
    debugStartStage(ERA, SHAPE);
    dismissStageIntro();
    const bossIdx = settlements.findIndex(b => b && b.isBoss);
    const boss = settlements[bossIdx];
    const HUGE = 1e12;
    settlements.forEach((b, i) => { if (b && i !== bossIdx) b.fallen = true; });
    const maxHp = boss.maxHp;
    boss.hp = HUGE; boss._noAttack = true; boss.attackRadius = 0; boss.projectileInterval = 1e9;
    debugClearEnemies();
    for (let i = 0; i < N; i++) if (!boidDead[i] && countAliveBoids() > FLOCK) boidDead[i] = 1;
    if (countAliveBoids() < FLOCK) debugAddDragons(FLOCK - countAliveBoids());
    setFlockOverflow(OVERFLOW);
    debugInvincible = true;
    if (SETUP) (0, eval)(SETUP);
    const r = (boss.radius || 40);
    const tx = boss.wx - r - 220, ty = boss.wy;
    let k = 0;
    for (let i = 0; i < N; i++) { if (boidDead[i]) continue; px[i] = tx + (k % 10) * 14; py[i] = ty - 70 + Math.floor(k / 10) * 14; k++; }
    leader.x = tx; leader.y = ty; leader.vx = 0; leader.vy = 0;
    cam.x = boss.wx; cam.y = boss.wy;
    pathClear();
    window.__cap = { bossIdx, maxHp, HUGE, cx: boss.wx, cy: boss.wy, r, strokeT: 0, dealt: 0 };
    return { maxHp, alive: countAliveBoids(), overflow: flockOverflow, era: currentStage, stage: runStageIndex };
  }, { ERA, SHAPE, SPECIES, FLOCK, OVERFLOW, SETUP });

  const run = (seconds, measuring) => page.evaluate(({ seconds, measuring, PATTERN, STEP_MS, LOOP_MARGIN_PX, LOOP_REDRAW_S, DART_EVERY_S, STROKE_STEP_PX }) => {
    const C = window.__cap;
    const stroke = (pts) => {
      cam.x = C.cx; cam.y = C.cy;
      const now = performance.now();
      inputEnd();
      const s0 = worldToScreen(pts[0].x, pts[0].y);
      beginDraw(s0.x, s0.y, now);
      for (let k = 1; k < pts.length; k++) { const s = worldToScreen(pts[k].x, pts[k].y); inputMove(s.x, s.y, now); }
      inputEnd();
    };
    const drawNext = () => {
      const c = calcFriendlyCentroid();
      const pts = [];
      if (PATTERN === "dart") {
        const dx = C.cx - c.x, dy = C.cy - c.y, d = Math.hypot(dx, dy) || 1, n = Math.max(2, Math.ceil(d / STROKE_STEP_PX));
        for (let k = 0; k <= n; k++) pts.push({ x: c.x + dx * k / n, y: c.y + dy * k / n });
        C.strokeT = DART_EVERY_S;
      } else {
        const r = C.r + LOOP_MARGIN_PX, a0 = Math.atan2(c.y - C.cy, c.x - C.cx);
        const n = Math.max(12, Math.ceil(Math.PI * 2 * r / STROKE_STEP_PX));
        for (let k = 0; k <= n; k++) { const a = a0 + Math.PI * 2 * k / n; pts.push({ x: C.cx + Math.cos(a) * r, y: C.cy + Math.sin(a) * r }); }
        C.strokeT = LOOP_REDRAW_S;
      }
      stroke(pts);
    };
    const steps = Math.round(seconds * 1000 / STEP_MS);
    for (let s = 0; s < steps; s++) {
      C.strokeT -= STEP_MS / 1000;
      if (C.strokeT <= 0) drawNext();
      window.__dtStep(STEP_MS);
      debugClearEnemies();
      projActive.fill(0);
      const b = settlements[C.bossIdx];
      const d = C.HUGE - b.hp;
      b.hp = C.HUGE; b.fallen = false;
      if (measuring && d > 0) C.dealt += d;
    }
    return { dealt: C.dealt, state: gameState };
  }, { seconds, measuring, PATTERN, STEP_MS, LOOP_MARGIN_PX, LOOP_REDRAW_S, DART_EVERY_S, STROKE_STEP_PX });

  await run(WARMUP_S, false);
  let res = null;
  for (let left = MEASURE_S; left > 0; left -= 10) res = await run(Math.min(10, left), true);
  if (errors.length) throw new Error(errors.join("\n"));
  const perSecond = res.dealt / MEASURE_S;
  console.log(JSON.stringify({ ...setup, species: SPECIES, pattern: PATTERN, perSecond: Math.round(perSecond),
    secondsToKill: perSecond > 0 ? +(setup.maxHp / perSecond).toFixed(1) : null }));
} finally {
  await browser.close();
}
