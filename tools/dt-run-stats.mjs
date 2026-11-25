// -----------------------------------------------------------------
// Dragon Tide のランの記録（案帳 DT-615）
//
//   node tools/dt-run-stats.mjs [--species fire,wyvern | all | random] [--seeds 1,2,3 | --runs 10 --seed-base 100]
//        [--parallel 4] [--out runs.json] [--stage-limit-min 30] [--stall-min 5] [--run-limit-min 240]
//        [--sample-sec 30] [--setup "式"] [--file prototypes/dragon-tide/index.html] [--resume]
//   --out の JSON は1ラン終わるたびに書き足す。--resume で、そこにある竜種・シードのランは回さずに使う（途中で止まった計測の続き）
//
// オートプレイでランを最初から最後まで回し、1ランごとの記録を JSON に書き出して、竜種ごとの表を出す。
// dt-headless.mjs（前後で挙動が同じかを見る指紋）と違い、こちらは「どれくらいかかったか・どこで詰まったか」を見る道具。
//
// - デバッグの「▶ 警戒度を上げる（決戦ならクリア）」（N キー・dt-headless の --advance-every）は押さない（素のラン。警戒度は強化カードの枚数で自然に上がる）。そのかわり次の場合はランを打ち切り、打ち切ったこと自体を記録に残す：
//   1ステージが --stage-limit-min 分を超えた（timeout）／ --stall-min 分のあいだ建物が1つも減らない（stalled）／
//   ラン全体が --run-limit-min 分を超えた（run-timeout）
// - 画面は描かない（dt-harness の noRender）。描いても同じランになるのは dt-headless.mjs --render と比べて確かめてある
// - 時間はすべてゲームの中の時計（1歩16ms）。強化カードで止まっている間も数える（実プレイで画面の前にいる時間に近い）
// - 竜種は鍵が掛かっていても選べる（調整のため。実プレイでは解放が要る）
// - 世界図で次に攻める国はオートプレイが選ぶ（シードで決まる）
//
// 数値を変える案は、書き換えた写しを --file に渡し、同じ --species / --seeds で回して表を比べる。
// AI は人と腕前が違うので、出てくる数字は「前後の比べ」「竜種どうし・地域どうしの比べ」に使う（難しさの絶対の高さは実プレイで合わせる）。
// -----------------------------------------------------------------
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { openGame, stepMany } from "./dt-harness.mjs";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const arg = (name, fallback) => { const i = args.indexOf(`--${name}`); return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback; };
const file = path.resolve(REPO_ROOT, arg("file", "prototypes/dragon-tide/index.html"));
const STEP_MS = 16;
const MS_PER_MIN = 60000;
const stageLimitMs = Number(arg("stage-limit-min", "30")) * MS_PER_MIN;
const stallMs = Number(arg("stall-min", "5")) * MS_PER_MIN;
const runLimitMs = Number(arg("run-limit-min", "240")) * MS_PER_MIN;
const sampleMs = Number(arg("sample-sec", "30")) * 1000;
// 1回の呼びかけで進める歩数（1秒ぶん）。打ち切りの判定と記録の取り込みはこの区切りで行う
const CHUNK_STEPS = Math.round(1000 / STEP_MS);
const setupExpr = arg("setup", "");
const parallel = Math.max(1, Number(arg("parallel", "4")));
const outPath = arg("out", "");

const seeds = arg("seeds", "")
  ? arg("seeds", "").split(",").map((s) => s.trim()).filter(Boolean)
  : Array.from({ length: Number(arg("runs", "1")) }, (_, i) => String(Number(arg("seed-base", "1")) + i));

// ページの中に記録係を仕込む。ゲームの関数を包むだけで、ゲームの状態や乱数には触らない
function installRecorder() {
  const now = () => performance.now();
  const rec = window.__dtRec = {
    events: [], cards: [], wipes: [], stages: [], samples: [], result: null,
    stage: null,
  };
  const aliveBuildings = () => { let n = 0; for (const s of settlements) if (!s.fallen && !s.isBoss && !s._isWall) n++; return n; };
  // DT-622: HUD の分子と同じ数え方（上限超えの竜は戦えている分だけ）。countFlockNow の無い古い版（--file）では前の数え方
  const flock = () => (typeof countFlockNow === "function" ? countFlockNow() : countAliveBoids() + flockOverflow);
  rec.aliveBuildings = aliveBuildings;
  rec.flock = flock;
  const stageInfo = () => ({
    number: runStageNumber, era: runStageIndex, eraName: CONTINENT_DEFS[runStageIndex] ? CONTINENT_DEFS[runStageIndex].name : "",
    shape: STAGE_SHAPES[runShape] ? STAGE_SHAPES[runShape].id : runShape, shapeName: STRINGS.shapeNames[runShape] ?? String(runShape),
    nation: runNationName(),
  });
  // ランを始めた時刻はゲームの runStartTime（beginRun で入る）
  const t = () => Math.round(now() - runStartTime);
  const wrap = (name, fn) => {
    const orig = window[name];
    if (typeof orig !== "function") return;
    window[name] = function (...a) { return fn(orig, this, a); };
  };
  rec.openStage = () => {
    // 前のステージが終わらないまま次が始まった（--setup の debugStartStage で差し替えたなど）。時間が経っていなければ捨てる
    const prev = rec.stage;
    if (prev && prev.endT === null) {
      if (t() - prev.startT < 1000) rec.stages.pop();
      else rec.closeStage("switched");
    }
    rec.stage = { ...stageInfo(), startT: t(), tierUpT: [], capitalT: null, endT: null, end: null, wipes: 0,
                  startFlock: flock(), startLevel: playerLevel, buildingsAtStart: aliveBuildings(),
                  lastProgressT: t(), lastBuildings: aliveBuildings() };
    rec.stages.push(rec.stage);
  };
  rec.closeStage = (end) => {
    const s = rec.stage;
    if (!s || s.endT !== null) return;
    s.endT = t(); s.end = end; s.minutes = +((s.endT - s.startT) / 60000).toFixed(2);
    s.endFlock = flock(); s.endLevel = playerLevel; s.endTier = powerTier + 1; s.buildingsLeft = aliveBuildings();
    delete s.lastProgressT; delete s.lastBuildings;
  };
  wrap("startStage", (orig, self, a) => { const r = orig.apply(self, a); rec.openStage(); return r; });
  wrap("triggerTierAdvance", (orig, self, a) => {
    const before = powerTier; const r = orig.apply(self, a);
    if (powerTier !== before && rec.stage) rec.stage.tierUpT.push({ t: t(), tier: powerTier + 1 });
    return r;
  });
  wrap("onCapitalFallen", (orig, self, a) => {
    if (rec.stage) { rec.stage.capitalT = t(); rec.closeStage("capital"); }
    return orig.apply(self, a);
  });
  wrap("triggerWipe", (orig, self, a) => {
    const by = lastDownBy && lastDownBy.attacker ? lastDownBy.attacker.name : null;
    const w = { t: t(), stage: runStageNumber, by, flockBefore: countJoinedBoids() + flockOverflow, livesLeft: runLives - 1 };
    rec.wipes.push(w);
    if (rec.stage) rec.stage.wipes++;
    return orig.apply(self, a);
  });
  wrap("triggerRunComplete", (orig, self, a) => { rec.result = rec.result || { outcome: "complete", t: t() }; return orig.apply(self, a); });
  wrap("triggerRunDefeat", (orig, self, a) => { rec.closeStage("defeat"); rec.result = rec.result || { outcome: "defeat", t: t() }; return orig.apply(self, a); });
  const cardKind = (def) => def.fuse ? "合成" : def.becomesSpecial ? "突然変異" : def.evo ? "進化"
    : (def.specialJoin !== undefined || def.stageJoin) ? "加入" : def.artifact ? "アーティファクト" : def.stageOnly ? "ステージ限定" : "強化";
  const cardName = (def) => (STRINGS.cards && STRINGS.cards[def.id] && STRINGS.cards[def.id].name) || def.name || def.id;
  const noteCard = (def, via) => rec.cards.push({ t: t(), stage: runStageNumber, id: def.id, name: cardName(def), kind: cardKind(def), via, level: playerLevel });
  wrap("chooseCard", (orig, self, a) => { if (upgradeCardsVisible && a[0]) noteCard(a[0], "レベルアップ"); return orig.apply(self, a); });
  const perkArmed = () => perkOfferVisible && perkOfferEl.classList.contains("armed");
  wrap("takePerkCard", (orig, self, a) => { if (perkArmed() && a[0]) noteCard(a[0], "強化カード"); return orig.apply(self, a); });
  wrap("takeSpecialLevel", (orig, self, a) => { if (perkArmed() && a[0]) noteCard(a[0], "特殊個体"); return orig.apply(self, a); });
  rec.sample = () => rec.samples.push({ t: t(), stage: runStageNumber, flock: flock(), joined: countJoinedBoids() + flockOverflow,
    level: playerLevel, tier: powerTier + 1, lives: runLives, buildings: aliveBuildings(), species: flockSpecies,
      speciesName: SPECIES_DEFS[flockSpecies] ? SPECIES_DEFS[flockSpecies].ja : flockSpecies, state: gameState });
}

async function runOne({ seed, species }) {
  const { browser, page, errors } = await openGame({ file, seed, noRender: true });
  try {
    await page.evaluate(installRecorder);
    // 竜種を決めてからランを始める（オートプレイの竜種選びは解放済みの竜種からしか選ばないため、ここで直接始める）
    const sid = await page.evaluate((sp) => {
      startAutoplay(sp);
      const all = SPECIES_CHOICES.map((ch) => ch.species);
      const id = all.includes(sp) ? sp : all[Math.floor(autoRandom() * all.length)];
      beginRun(id);
      return id;
    }, species);
    if (setupExpr) await page.evaluate((expr) => (0, eval)(expr), setupExpr);
    let stopReason = null, nextSample = 0;
    for (;;) {
      await stepMany(page, CHUNK_STEPS, { stepMs: STEP_MS, stopExpr: "window.__dtRec.result !== null" });
      if (errors.length) { stopReason = "error"; break; }
      const st = await page.evaluate(([stageLimitMs, stallMs, runLimitMs, sampleMs, nextSample]) => {
        const rec = window.__dtRec, t = performance.now() - runStartTime;
        if (rec.result) return { done: rec.result.outcome };
        let sampled = false;
        if (t >= nextSample) { rec.sample(); sampled = true; }
        const s = rec.stage;
        if (s && s.endT === null && gameState === "playing") {
          const b = rec.aliveBuildings();
          if (b < s.lastBuildings) { s.lastBuildings = b; s.lastProgressT = t; }
          if (t - s.startT > stageLimitMs) return { cut: "timeout", sampled };
          if (t - s.lastProgressT > stallMs) return { cut: "stalled", sampled };
        }
        if (t > runLimitMs) return { cut: "run-timeout", sampled };
        return { sampled, t };
      }, [stageLimitMs, stallMs, runLimitMs, sampleMs, nextSample]);
      if (st.sampled) nextSample += sampleMs;
      if (st.done) break;
      if (st.cut) { stopReason = st.cut; break; }
    }
    const rec = await page.evaluate((stopReason) => {
      const rec = window.__dtRec;
      if (!rec.result) { rec.closeStage(stopReason); rec.result = { outcome: stopReason, t: Math.round(performance.now() - runStartTime) }; }
      rec.sample();
      return {
        version: GAME_VERSION, seed: debugGetSeed(), species: flockSpecies, speciesName: SPECIES_DEFS[flockSpecies] ? SPECIES_DEFS[flockSpecies].ja : flockSpecies,
        startSpecies: null, outcome: rec.result.outcome, minutes: +(rec.result.t / 60000).toFixed(2),
        stagesCleared: rec.stages.filter((s) => s.end === "capital").length, lastStage: runStageNumber,
        wipes: rec.wipes.length, livesLeft: runLives, level: playerLevel, maxFlock: runMaxFlock, kills: runKills,
        specials: runSpecials.map((k) => (SPECIAL_DEFS[k] ? SPECIAL_DEFS[k].name : k)),
        stages: rec.stages, wipeList: rec.wipes, cards: rec.cards, samples: rec.samples,
      };
    }, stopReason);
    rec.startSpecies = sid;
    rec.startSpeciesName = await page.evaluate((id) => (SPECIES_DEFS[id] ? SPECIES_DEFS[id].ja : id), sid);
    if (errors.length) rec.errors = errors.slice(0, 5);
    return rec;
  } finally {
    await browser.close();
  }
}

// 竜種の一覧（all のとき）はページから取る
async function listSpecies() {
  const { browser, page } = await openGame({ file, seed: "1", noRender: true });
  const ids = await page.evaluate(() => SPECIES_CHOICES.map((ch) => ch.species));
  await browser.close();
  return ids;
}

const speciesArg = arg("species", "random");
const speciesList = speciesArg === "all" ? await listSpecies() : speciesArg.split(",").map((s) => s.trim()).filter(Boolean);
const jobs = [];
for (const species of speciesList) for (const seed of seeds) jobs.push({ species, seed });

const results = new Array(jobs.length);
let nextJob = 0;
// 1ラン終わるたびに --out へ書き足す（長い計測の途中で止まっても、それまでのランを失わないため）。
// --resume を付けると、--out にすでにある同じ竜種・シードのランは回さずに使う
const writeOut = () => {
  if (!outPath) return;
  fs.writeFileSync(path.resolve(outPath), JSON.stringify({ file: path.relative(REPO_ROOT, file), args, runs: results.filter(Boolean) }, null, 1));
};
if (hasResume() && outPath && fs.existsSync(path.resolve(outPath))) {
  const done = JSON.parse(fs.readFileSync(path.resolve(outPath), "utf8")).runs || [];
  for (let j = 0; j < jobs.length; j++) {
    const hit = done.find((r) => (r.startSpecies || r.species) === jobs[j].species && String(r.seed) === String(jobs[j].seed));
    if (hit && hit.outcome !== "error") results[j] = hit;   // 落ちたランは回し直す
  }
  process.stderr.write(`resume: ${results.filter(Boolean).length}/${jobs.length} ランは前の記録を使う\n`);
}
function hasResume() { return args.includes("--resume"); }
// 表と進み具合は、始めた竜種で分ける（突然変異で竜種が変わっても、どの竜種で始めたランかで比べたいため）。終わりの竜種が違えば「→」で添える
const runLabel = (r) => {
  const start = r.startSpeciesName || r.startSpecies || r.species;
  // ランが終わるとタイトルに戻って竜種が火竜に戻るので、終わりの竜種は最後の記録（30秒ごと）から取る
  const last = (r.samples || []).findLast((x) => x.state !== "title");
  const end = last && last.speciesName ? last.speciesName : (r.speciesName || r.species);
  return end && end !== start ? `${start}→${end}` : start;
};
const runGroup = (r) => r.startSpeciesName || r.startSpecies || r.species;

const started = Date.now();
async function worker() {
  for (;;) {
    const j = nextJob++;
    if (j >= jobs.length) return;
    if (results[j]) continue;   // --resume で前の記録を使うラン
    const t0 = Date.now();
    try { results[j] = await runOne(jobs[j]); }
    catch (e) { results[j] = { species: jobs[j].species, seed: jobs[j].seed, outcome: "error", errors: [String(e && e.stack || e)] }; }
    const r = results[j];
    writeOut();
    process.stderr.write(`  ${j + 1}/${jobs.length} ${runLabel(r)} seed=${jobs[j].seed} → ${r.outcome}` +
      ` ${r.minutes ?? "?"}分 ステージ${r.stagesCleared ?? "?"}つ 全滅${r.wipes ?? "?"} （実時間 ${((Date.now() - t0) / 1000).toFixed(0)}秒）\n`);
  }
}
await Promise.all(Array.from({ length: Math.min(parallel, jobs.length) }, worker));

if (outPath) {
  writeOut();
  process.stderr.write(`→ ${outPath}\n`);
}

// 竜種ごとの表：ランの結果の内訳・通せた割合・平均の長さ・全滅・ステージごとの平均分
const fmt = (x) => (Number.isFinite(x) ? x.toFixed(1) : "-");
const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : NaN);
const bySpecies = new Map();
for (const r of results) { const k = runGroup(r); if (!bySpecies.has(k)) bySpecies.set(k, []); bySpecies.get(k).push(r); }
console.log(`始めた竜種\tラン\t完了\t敗北\t打ち切り\t平均分\t平均ステージ\t平均全滅\t平均Lv\t最大群れ\tステージの平均分（1,2,3…）`);
for (const [k, rs] of bySpecies) {
  const ok = rs.filter((r) => r.outcome === "complete").length, lost = rs.filter((r) => r.outcome === "defeat").length;
  const perStage = [];
  for (const r of rs) for (const s of r.stages || []) if (s.end === "capital") (perStage[s.number - 1] ||= []).push(s.minutes);
  console.log([k, rs.length, ok, lost, rs.length - ok - lost, fmt(mean(rs.map((r) => r.minutes))), fmt(mean(rs.map((r) => r.stagesCleared))),
    fmt(mean(rs.map((r) => r.wipes))), fmt(mean(rs.map((r) => r.level))), fmt(mean(rs.map((r) => r.maxFlock))),
    perStage.map((xs) => fmt(mean(xs || []))).join(" ")].join("\t"));
}
const cut = results.filter((r) => !["complete", "defeat"].includes(r.outcome));
for (const r of cut) {
  const s = (r.stages || []).at(-1);
  console.log(`打ち切り: ${runLabel(r)} seed=${r.seed} ${r.outcome}${s ? ` ステージ${s.number}（${s.eraName}／${s.shapeName}）残り${s.buildingsLeft}棟` : ""}${r.errors ? " " + r.errors[0].split("\n")[0] : ""}`);
}
console.error(`elapsed ${((Date.now() - started) / 1000).toFixed(0)}s`);
