// -----------------------------------------------------------------
// レベルの最短手数をビームサーチで求める（par と limit の根拠）。
//   node prototypes/voxel-puzzle/solve.mjs            … 全レベル
//   node prototypes/voxel-puzzle/solve.mjs L07 --width 2000
// 乱数はゲーム本体と同じ「レベルIDから決まるシード」を使うので、盤面の増え方も一致する。
// -----------------------------------------------------------------
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const Core = require("./puzzle-core.js");
const LEVELS = require("./levels.js");

function makeRandomGenerator(seedValue) {   // mulberry32（本体と同じ）
  let state = seedValue >>> 0;
  return function nextRandom() {
    state = (state + 0x6D2B79F5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hashSeed(text) {
  let hash = 0x811C9DC5;
  for (let i = 0; i < text.length; i++) { hash ^= text.charCodeAt(i); hash = Math.imul(hash, 0x01000193); }
  return hash >>> 0;
}

// 乱数を「消費した回数」で持ち、複製した状態でも同じ列が続くようにする
function makeReplayableRng(seed) {
  const gen = makeRandomGenerator(seed);
  const values = [];
  return {
    at(count) {
      let cursor = count;
      return {
        next() { while (values.length <= cursor) values.push(gen()); return values[cursor++]; },
        get cursor() { return cursor; },
      };
    },
  };
}

function solve(level, width) {
  const seed = hashSeed(level.id);
  const rngSource = makeReplayableRng(seed);
  const root = Core.createState(level, null);
  let beam = [{ state: root, rngCount: 0, path: [] }];
  const maxDepth = level.limit + 3;
  let bestFail = null;
  for (let depth = 1; depth <= maxDepth; depth++) {
    const candidates = [];
    const seen = new Set();
    for (const node of beam) {
      for (const idx of Core.tappableCells(node.state)) {
        const state = Core.cloneState(node.state);
        const rng = rngSource.at(node.rngCount);
        state.rng = rng.next;
        const result = Core.tap(state, idx);
        if (!result.ok) continue;
        const key = state.cells.join(",") + "|" + state.aux.join(",") + "|" + state.bonus;
        if (seen.has(key)) continue;
        seen.add(key);
        const child = { state, rngCount: rng.cursor, path: [...node.path, idx] };
        if (state.status === "clear") return { taps: depth, path: child.path };
        candidates.push(child);
      }
    }
    if (candidates.length === 0) break;
    // 残りブロックが少ない順。同数なら拡げ石の貯金があるほうを優先
    candidates.sort((a, b) => (a.state.blocks - b.state.blocks) || (b.state.bonus - a.state.bonus));
    beam = candidates.slice(0, width);
    bestFail = beam[0];
  }
  return { taps: null, remaining: bestFail ? bestFail.state.blocks : null };
}

const args = process.argv.slice(2);
const widthArg = args.indexOf("--width");
const width = widthArg >= 0 ? Number(args[widthArg + 1]) : 600;
const only = args.filter((a) => /^L\d+$/.test(a));
const asJson = args.includes("--json");
const jsonOut = {};
let bad = 0;
for (const level of LEVELS) {
  if (only.length && !only.includes(level.id)) continue;
  const t0 = performance.now();
  const r = solve(level, width);
  const ms = (performance.now() - t0).toFixed(0);
  jsonOut[level.id] = r.path ? r.path.map((i) => Core.coords({ gx: level.size[0], gz: level.size[2] }, i)) : null;
  if (asJson) { if (r.taps === null || r.taps > level.limit) bad++; continue; }
  const pathText = r.path ? r.path.map((i) => Core.coords({ gx: level.size[0], gz: level.size[2] }, i).join(",")).join(" → ") : "";
  if (r.taps === null) {
    bad++;
    console.log(`${level.id} ${level.name}: 解けず（limit+3手で残り${r.remaining}） ${ms}ms`);
  } else {
    const flag = r.taps > level.limit ? " ★limit超過" : (r.taps !== level.par ? ` ★par=${level.par}と不一致` : "");
    if (flag) bad++;
    console.log(`${level.id} ${level.name}: 最短 ${r.taps}手 (par ${level.par} / limit ${level.limit})${flag} ${ms}ms  [${pathText}]`);
  }
}
if (asJson) console.log(JSON.stringify(jsonOut));
process.exit(bad ? 1 : 0);
