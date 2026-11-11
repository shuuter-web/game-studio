// -----------------------------------------------------------------
// Dragon Tide の攻撃の強さを、決まった条件で測る（案帳 DT-550）
//
//   node tools/dt-bench.mjs --species fire [--special aim] [--pattern loop|sweep|dart] [--seed 4242] [--flock 20] [--seconds 60]
//   node tools/dt-bench.mjs --all-species   # 全竜種 × 2つの動き × 2シードを表にする
//   node tools/dt-bench.mjs --all-specials  # 火竜の群れに主な特殊個体を1体ずつ入れて表にする
//
// オートプレイで測ると、群れの増え方・狙う建物・倒しきった後の余り・敵の反撃が竜種ごとに違い、
// 「強いのに弱く出る」ことがあった（彗星竜など）。そこで条件をそろえる：
//   - 地図に街を1つだけ残す（ほかの建物は無いものとして扱う）。街の建物は撃ってこず、倒れても建て直す
//   - 動く敵・敵の弾は毎歩消す。経験値・レベルアップは止める（強化カードで強さが変わらないように）
//   - 群れの数を固定し、街の手前に置いてから決まった線を決まった間隔で引く
//       loop  … 街のまわりを囲む輪を描き、回り続ける（輪は一定時間ごとに描き直す）
//       sweep … 群れから街の中心を突き抜ける直線を一定間隔で引く（薙ぐ。往復になる）
//       dart  … 群れから街の中心まで引いて真ん中で離す（離した所を狙う特殊個体の使い方）
//   - 決まった時間（既定 60 秒）に建物へ入った傷を測る。建物は本来のHPで、削りきった一撃の余りは捨てて数え、
//     倒れた建物は 10 秒後にその場で建て直す（街が尽きない）。--raw で余りも数える
// 特殊個体は、その能力の当たり（ゲームが specialHitActive / bySpecial を立てている間の傷）だけを分けて数える。
// 群れの差で測ると、1匹足しただけで群れの動きが変わり、傷を出さない特殊個体でも ±30 揺れたため。
// 特殊個体の竜は自分の竜種の攻撃も特殊個体の当たりとして出す（強化カードの倍率が乗る）ので、その分（ふつうの竜1匹ぶん）も込み。
// 撃ってくる建物・敵の弾が要る特殊個体（虹弓・暴食）はこの場では働かないので測れない。
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
const hasFlag = (name) => args.includes(`--${name}`);
const file = path.resolve(REPO_ROOT, argValue("file", "prototypes/dragon-tide/index.html"));
const FLOCK = Number(argValue("flock", "20"));
const MEASURE_S = Number(argValue("seconds", "60"));
// 群れが街に着いて線に乗るまでの間（測らない）
const WARMUP_S = Number(argValue("warmup", "4"));
const PARALLEL = Number(argValue("parallel", "3"));
// --raw で、HP無限の建物に入った傷そのままを比べる（既定は本来のHPで余りを捨てた分）
const RAW = hasFlag("raw");
// 固定歩幅。ゲーム側の BASE_CFG.fixedStepMs と同じ 16ms で刻む
const STEP_MS = 16;
// 輪の半径＝街の広がり＋この余白。輪は描き直さないと群れが線を食べ終えて止まるので一定間隔で引き直す
const LOOP_MARGIN_PX = 60;
const LOOP_REDRAW_S = 6;
// 薙ぐ線は街の向こうへこれだけ突き抜ける（群れの今いる所から街の中心を通す＝往復になる）
const SWEEP_OVERSHOOT_PX = 260;
const SWEEP_EVERY_S = 3;
// 街の真ん中で離す線の間隔。狙い火が満タンになる 4 秒に合わせる
const DART_EVERY_S = 4;
// 倒れた建物を建て直すまでの秒数
const REBUILD_S = Number(argValue("rebuild", "10"));
const STROKE_STEP_PX = 24;
// 測る街：建物の数がこの幅の街のうち、地図の中心に近いもの（ふつうの大きさの街。同じシードなら同じ街）
const TOWN_MIN_BUILDINGS = 50;
const TOWN_MAX_BUILDINGS = 90;

/** 1回測る。返り値は { total, perSecond, perDragon, alive, town } */
async function measureOnce({ seed, species, special, pattern, dir = 0 }) {
  const { browser, page, errors } = await openGame({ file, seed });
  try {
    const setup = await page.evaluate(({ species, special, dir, FLOCK, TOWN_MIN_BUILDINGS, TOWN_MAX_BUILDINGS }) => {
      debugUnlockAllContinents();
      // 強化カードで強さが変わらないように、経験値とレベルアップを止める
      window.addXp = () => {};
      window.queueLevelUp = () => {};
      // 測るのは攻撃の当たりだけ。描画は結果に関係しないので止めて速くする
      window.render = () => {};
      window.drawMinimap = () => {};
      beginRun(species);
      debugStartStage(0, 0);
      dismissStageIntro();
      // 街を1つ選ぶ（ふつうの大きさの街のうち地図の中心に近いもの）
      const towns = new Map();
      settlements.forEach((b, i) => {
        if (!b || b.fallen || b._townIndex === undefined || b.isBoss || b._isWall) return;
        const t = towns.get(b._townIndex) || { idx: [], sx: 0, sy: 0 };
        t.idx.push(i); t.sx += b.wx; t.sy += b.wy; towns.set(b._townIndex, t);
      });
      let best = null;
      for (const [key, t] of towns) {
        if (t.idx.length < TOWN_MIN_BUILDINGS || t.idx.length > TOWN_MAX_BUILDINGS) continue;
        const cx = t.sx / t.idx.length, cy = t.sy / t.idx.length;
        const d = Math.hypot(cx - WORLD_W / 2, cy - WORLD_H / 2);
        if (!best || d < best.d) best = { key, cx, cy, d, idx: t.idx };
      }
      const keep = new Set(best.idx);
      let spread = 0;
      for (const i of keep) { const b = settlements[i]; spread = Math.max(spread, Math.hypot(b.wx - best.cx, b.wy - best.cy) + (b.radius || 0)); }
      // ほかの建物は陥落扱い（陥落の処理は通さない＝卵も経験値も出ない）。残す建物はHP無限で撃たない
      const HUGE = 1e12;
      settlements.forEach((b, i) => {
        if (!b) return;
        if (!keep.has(i)) { b.fallen = true; return; }
        b._benchHp = b.maxHp; b.hp = HUGE; b._noAttack = true; b.attackRadius = 0; b.projectileInterval = 1e9;
      });
      window.__bench = { keep: [...keep], cx: best.cx, cy: best.cy, spread, HUGE, spAcc: new Map() };
      // 特殊個体の能力の当たりを分けて数える。ゲームは特殊個体の当たりの間 specialHitActive を立てる（強化カードの倍率のため）。
      // hitBuilding の bySpecial（特殊個体の体当たりなど）もここで拾う
      const origDamage = damageBuilding, origHit = hitBuilding;
      let bySpecialNow = false;
      window.hitBuilding = function (sIdx, hit, fromX, fromY, bySpecial = false) {
        const prev = bySpecialNow; bySpecialNow = bySpecialNow || bySpecial;
        try { return origHit(sIdx, hit, fromX, fromY, bySpecial); } finally { bySpecialNow = prev; }
      };
      window.damageBuilding = function (sIdx, damage) {
        const b = settlements[sIdx], before = b ? b.hp : 0;
        origDamage(sIdx, damage);
        if (b && (specialHitActive || bySpecialNow)) window.__bench.spAcc.set(sIdx, (window.__bench.spAcc.get(sIdx) || 0) + (before - b.hp));
      };
      debugClearEnemies();
      // 群れの数をそろえる（多ければ消し、少なければ足す）
      for (let i = 0; i < N; i++) if (!boidDead[i] && countAliveBoids() > FLOCK) boidDead[i] = 1;
      if (countAliveBoids() < FLOCK) debugAddDragons(FLOCK - countAliveBoids());
      debugInvincible = true;
      if (special) {
        const kind = Object.keys(SPECIAL_DEFS).find(k => SPECIAL_DEFS[k].key === special);
        if (kind === undefined) throw new Error(`特殊個体 ${special} が無い`);
        addRunSpecial(Number(kind));
      }
      // 群れを街の手前へ運ぶ（dir＝0:西 1:北 2:東 3:南。どの竜種も同じ所から始める）
      const ang = Math.PI + dir * Math.PI / 2;
      const tx = best.cx + Math.cos(ang) * (spread + 200), ty = best.cy + Math.sin(ang) * (spread + 200);
      let k = 0;
      for (let i = 0; i < N; i++) {
        if (boidDead[i]) continue;
        px[i] = tx + (k % 5) * 18; py[i] = ty - 40 + Math.floor(k / 5) * 18; k++;
      }
      leader.x = tx; leader.y = ty; leader.vx = 0; leader.vy = 0;
      cam.x = best.cx; cam.y = best.cy;
      pathClear();
      return { town: best.key, buildings: keep.size, spread: Math.round(spread), alive: countAliveBoids() };
    }, { species, special, dir, FLOCK, TOWN_MIN_BUILDINGS, TOWN_MAX_BUILDINGS });

    const run = (seconds, measuring) => page.evaluate(({ seconds, measuring, pattern, STEP_MS, LOOP_MARGIN_PX, LOOP_REDRAW_S, SWEEP_OVERSHOOT_PX, SWEEP_EVERY_S, DART_EVERY_S, STROKE_STEP_PX, REBUILD_S }) => {
      const B = window.__bench;
      if (B.strokeT === undefined) { B.strokeT = 0; B.total = 0; B.capped = 0; B.special = 0; B.kills = 0; B.aliveSum = 0; B.steps = 0; }
      const stroke = (pts) => {
        for (const p of pts) { p.x = Math.max(0, Math.min(WORLD_W, p.x)); p.y = Math.max(0, Math.min(WORLD_H, p.y)); }
        cam.x = B.cx; cam.y = B.cy;   // 画面座標で線を引くので、カメラを街に固定してから
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
        if (pattern === "loop") {
          const r = B.spread + LOOP_MARGIN_PX;
          const a0 = Math.atan2(c.y - B.cy, c.x - B.cx);
          const n = Math.max(12, Math.ceil(Math.PI * 2 * r / STROKE_STEP_PX));
          for (let k = 0; k <= n; k++) { const a = a0 + Math.PI * 2 * k / n; pts.push({ x: B.cx + Math.cos(a) * r, y: B.cy + Math.sin(a) * r }); }
          B.strokeT = LOOP_REDRAW_S;
        } else if (pattern === "dart") {
          // 群れの今いる所から街の中心まで引いて、真ん中で離す（離した所を狙う特殊個体の使い方）
          const dx = B.cx - c.x, dy = B.cy - c.y, d = Math.hypot(dx, dy) || 1;
          const n = Math.max(2, Math.ceil(d / STROKE_STEP_PX));
          for (let k = 0; k <= n; k++) pts.push({ x: c.x + dx * k / n, y: c.y + dy * k / n });
          B.strokeT = DART_EVERY_S;
        } else {
          // 群れの今いる所から、街の中心を通って反対側へ突き抜ける
          const dx = B.cx - c.x, dy = B.cy - c.y, d = Math.hypot(dx, dy) || 1;
          const len = d + B.spread + SWEEP_OVERSHOOT_PX, n = Math.max(2, Math.ceil(len / STROKE_STEP_PX));
          for (let k = 0; k <= n; k++) pts.push({ x: c.x + dx / d * len * k / n, y: c.y + dy / d * len * k / n });
          B.strokeT = SWEEP_EVERY_S;
        }
        stroke(pts);
      };
      const steps = Math.round(seconds * 1000 / STEP_MS);
      for (let s = 0; s < steps; s++) {
        B.strokeT -= STEP_MS / 1000;
        if (B.strokeT <= 0) drawNext();
        window.__dtStep(STEP_MS);
        debugClearEnemies();
        projActive.fill(0);
        // raw … 入った傷そのまま。capped … 建物が本来のHPだったら減った分（壊した一撃の余りは捨てる）。
        // 本来のHPを削りきった建物は本当に倒れ（群れは次の建物へ移る）、REBUILD_S 秒後にその場で建て直す。
        // 倒れない建物だと、体当たりの竜が建物に張り付いて毎フレーム当て続け、実際のプレイより桁違いに強く出るため
        let dealt = 0, capped = 0, kills = 0, special = 0;
        for (const i of B.keep) {
          const b = settlements[i];
          const sp = B.spAcc.get(i) || 0;
          if (b._benchDown > 0) {
            b._benchDown -= STEP_MS / 1000;
            if (b._benchDown <= 0) { b.fallen = false; b.hp = B.HUGE; b._benchHp = b.maxHp; }
            continue;
          }
          const d = B.HUGE - b.hp;
          b.hp = B.HUGE; if (b.fallen) b.fallen = false;
          if (!(d > 0)) continue;
          dealt += d;
          const c = Math.min(d, b._benchHp);
          capped += c;
          special += sp > 0 ? c * Math.min(1, sp / d) : 0;   // 余りを捨てた分は、特殊個体とほかとで割合どおりに分ける
          if (d >= b._benchHp) { kills++; b.fallen = true; b._benchDown = REBUILD_S; }
          else b._benchHp -= d;
        }
        B.spAcc.clear();
        if (measuring) { B.total += dealt; B.capped += capped; B.special += special; B.kills += kills; B.aliveSum += countAliveBoids(); B.steps++; }
      }
      return { total: B.total, capped: B.capped, special: B.special, kills: B.kills, alive: B.steps ? B.aliveSum / B.steps : 0, state: gameState };
    }, { seconds, measuring, pattern, STEP_MS, LOOP_MARGIN_PX, LOOP_REDRAW_S, SWEEP_OVERSHOOT_PX, SWEEP_EVERY_S, DART_EVERY_S, STROKE_STEP_PX, REBUILD_S });

    await run(WARMUP_S, false);
    // 長い evaluate は止まって見えるので 10 秒ずつ回す
    let res = null;
    for (let left = MEASURE_S; left > 0; left -= 10) res = await run(Math.min(10, left), true);
    if (errors.length) throw new Error(errors.join("\n"));
    if (res.state !== "playing") throw new Error(`測っている間に ${res.state} になった`);
        const metric = RAW ? res.total : res.capped;
    return { ...setup, raw: res.total, capped: res.capped, specialPerSecond: res.special / MEASURE_S, kills: res.kills, alive: res.alive, perSecond: metric / MEASURE_S, perDragon: metric / MEASURE_S / res.alive };
  } finally {
    await browser.close();
  }
}

/** 並べて回す（ブラウザ1つが CPU 1つをほぼ使い切るので、コア数ぶんまで） */
async function runAll(jobs) {
  const results = new Array(jobs.length);
  let next = 0;
  const worker = async () => {
    for (;;) {
      const j = next++;
      if (j >= jobs.length) return;
      try { results[j] = await measureOnce(jobs[j]); }
      catch (e) { results[j] = { error: String(e && e.message || e).split("\n")[0] }; }
      process.stderr.write(`  ${j + 1}/${jobs.length} ${jobs[j].species}${jobs[j].special ? "+" + jobs[j].special : ""} ${jobs[j].pattern} seed=${jobs[j].seed} dir=${jobs[j].dir} → ${results[j].error || results[j].perSecond.toFixed(1)}\n`);
    }
  };
  await Promise.all(Array.from({ length: PARALLEL }, worker));
  return results;
}

// 街はシードで決まる。シードを変えると街の形・地形・建物のHPの組み合わせが変わって数字が大きく揺れる（同じ火竜で 1.6〜7）ので、
// 既定は1つの街（シード 4242）に固定し、群れが入ってくる向き（西・北・東・南）を変えて4回測る
const seeds = argValue("seeds", "4242").split(",");
const dirs = argValue("dirs", "0,1,2,3").split(",").map(Number);
const patterns = argValue("patterns", "loop,sweep,dart").split(",");
const fmt = (x) => (x === undefined || Number.isNaN(x) ? "—" : x.toFixed(1));

if (hasFlag("all-species")) {
  const { browser, page } = await openGame({ file, seed: "1" });
  const ids = (argValue("species", "") || "").split(",").filter(Boolean);
  const all = ids.length ? ids : await page.evaluate(() => Object.keys(SPECIES_DEFS));
  const names = await page.evaluate((ids) => Object.fromEntries(ids.map(id => [id, SPECIES_DEFS[id].ja])), all);
  await browser.close();
  const jobs = [];
  for (const species of all) for (const pattern of patterns) for (const seed of seeds) for (const dir of dirs) jobs.push({ species, pattern, seed, dir });
  const res = await runAll(jobs);
  if (argValue("json", "")) (await import("node:fs")).writeFileSync(argValue("json", ""), JSON.stringify(jobs.map((j, k) => ({ ...j, ...res[k] }))));
  console.log(`竜種（ふつうの竜1匹・1秒の傷。群れ ${FLOCK}・${MEASURE_S}秒・シード ${seeds.join("/")}・入る向き${dirs.length}通りの平均）`);
  console.log(["竜種", ...patterns, "平均"].join("\t"));
  const rows = [];
  for (const species of all) {
    const per = patterns.map(p => {
      const v = jobs.map((j, k) => j.species === species && j.pattern === p && !res[k].error ? res[k].perDragon : null).filter(v => v !== null);
      return v.length ? v.reduce((a, b) => a + b, 0) / v.length : NaN;
    });
    const ok = per.filter(v => !Number.isNaN(v));
    rows.push({ species, per, mean: ok.length ? ok.reduce((a, b) => a + b, 0) / ok.length : NaN });
  }
  rows.sort((a, b) => a.mean - b.mean);
  for (const r of rows) console.log([`${names[r.species]}(${r.species})`, ...r.per.map(fmt), fmt(r.mean)].join("\t"));
  const errs = jobs.map((j, k) => res[k].error ? `${j.species} ${j.pattern} ${j.seed}: ${res[k].error}` : null).filter(Boolean);
  if (errs.length) console.log("測れなかった:\n" + errs.join("\n"));
} else if (hasFlag("all-specials")) {
  const base = argValue("species", "fire");
  const list = argValue("specials", "beacon,rainbow,laser,chain,mecha,aim,recall,heavy,wedge").split(",");
  const jobs = [];
  for (const special of list) for (const pattern of patterns) for (const seed of seeds) for (const dir of dirs) jobs.push({ species: base, special, pattern, seed, dir });
  const res = await runAll(jobs);
  if (argValue("json", "")) (await import("node:fs")).writeFileSync(argValue("json", ""), JSON.stringify(jobs.map((j, k) => ({ ...j, ...res[k] }))));
  console.log(`特殊個体（${base}の群れ ${FLOCK} に1体入れたときの、その1体が出した傷・1秒（自分の竜種の攻撃も込み）。${MEASURE_S}秒・シード ${seeds.join("/")}・入る向き${dirs.length}通りの平均）`);
  console.log(["特殊個体", ...patterns, "平均"].join("\t"));
  const rows = [];
  for (const special of list) {
    const per = patterns.map(p => {
      const v = jobs.map((j, k) => j.special === special && j.pattern === p && !res[k].error ? res[k].specialPerSecond : null).filter(v => v !== null);
      return v.length ? v.reduce((x, y) => x + y, 0) / v.length : NaN;
    });
    const ok = per.filter(v => !Number.isNaN(v));
    rows.push({ special, per, mean: ok.length ? ok.reduce((a, b) => a + b, 0) / ok.length : NaN });
  }
  rows.sort((a, b) => a.mean - b.mean);
  for (const r of rows) console.log([r.special, ...r.per.map(fmt), fmt(r.mean)].join("\t"));
  const errs = jobs.map((j, k) => res[k].error ? `${j.special} ${j.pattern} ${j.seed}: ${res[k].error}` : null).filter(Boolean);
  if (errs.length) console.log("測れなかった:\n" + errs.join("\n"));
} else {
  const r = await measureOnce({ dir: Number(argValue("dir", "0")), seed: argValue("seed", "4242"), species: argValue("species", "fire"), special: argValue("special", ""), pattern: argValue("pattern", "loop") });
  console.log(JSON.stringify(r));
}
