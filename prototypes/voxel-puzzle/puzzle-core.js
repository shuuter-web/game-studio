// -----------------------------------------------------------------
// SKETCH VOXEL PUZZLE — ルール（描画・入力から独立）
//
// ブラウザでは window.PuzzleCore、Node では require() で同じものが使える。
// 描画側はここが返す「波（wave）」を順に演出するだけで、状態の真実はここにある。
// solve.mjs も同じ関数で盤面を回して手数を検証するので、ここに Math.random は置かない
// （乱数は createState に渡された rng だけを使う）。
// -----------------------------------------------------------------
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.PuzzleCore = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // ブロックの種類。番号は cells(Uint8Array) に入る
  const T = {
    EMPTY: 0,
    PLAIN: 1,    // 土：何も起きない
    HARD: 2,     // 石：2回当てないと壊れない
    ARMOR: 3,    // 鉄：タップでは壊せない。連鎖や範囲に巻き込んで壊す
    MOSS: 4,     // 苔：毎ターン、隣の空きに苔石を1つ増やす
    LEAF: 5,     // 苔石：苔が増やしたもの。増えはしない
    EGG: 6,      // 卵：ターンが経つと苔になる
    SPLIT: 7,    // 分裂石：タップの範囲で壊すと土2つに分裂する。連鎖で壊せば分裂しない
    BOMB: 8,     // 爆弾：壊れると周り3×3×3を巻き込む
    ICE: 9,      // 氷：隣が壊れると割れる（氷づたいに伝わる）
    RED: 10,     // 共鳴（赤）：壊すと同じ色が全部壊れる
    BLUE: 11,
    YELLOW: 12,
    AMP: 13,     // 拡げ石：壊すと次のタップの範囲が1段広がる（最大5×5×5）
    LINE_X: 14,  // 貫き石：その軸の一直線を全部壊す
    LINE_Y: 15,
    LINE_Z: 16,
    WEED: 17,    // 除草石：壊すと苔・苔石・卵が全部壊れる
  };

  const INFO = {
    [T.PLAIN]:  { char: "#", name: "土",     rule: "ふつうのブロック。" },
    [T.HARD]:   { char: "H", name: "石",     rule: "2回当てないと壊れない。" },
    [T.ARMOR]:  { char: "X", name: "鉄",     rule: "タップでは壊せない。爆弾・貫き・範囲に巻き込む。" },
    [T.MOSS]:   { char: "M", name: "苔",     rule: "毎ターン、隣に苔石を1つ増やす。" },
    [T.LEAF]:   { char: "m", name: "苔石",   rule: "苔が増やしたもの。増えはしない。" },
    [T.EGG]:    { char: "E", name: "卵",     rule: "3ターン経つと苔になる。" },
    [T.SPLIT]:  { char: "S", name: "分裂石", rule: "タップで壊すと土2つに分裂。連鎖で壊せば分裂しない。" },
    [T.BOMB]:   { char: "B", name: "爆弾",   rule: "壊れると周り3×3×3を巻き込む。" },
    [T.ICE]:    { char: "I", name: "氷",     rule: "隣が壊れると割れる。氷づたいに伝わる。" },
    [T.RED]:    { char: "r", name: "共鳴・赤", rule: "壊すと同じ色が全部壊れる。" },
    [T.BLUE]:   { char: "b", name: "共鳴・青", rule: "壊すと同じ色が全部壊れる。" },
    [T.YELLOW]: { char: "y", name: "共鳴・黄", rule: "壊すと同じ色が全部壊れる。" },
    [T.AMP]:    { char: "+", name: "拡げ石", rule: "次のタップの範囲が1段広がる（3×3×3→5×5×5）。" },
    [T.LINE_X]: { char: "=", name: "貫き石", rule: "矢印の向きに一直線、全部壊す。" },
    [T.LINE_Y]: { char: "|", name: "貫き石", rule: "矢印の向きに一直線、全部壊す。" },
    [T.LINE_Z]: { char: "/", name: "貫き石", rule: "矢印の向きに一直線、全部壊す。" },
    [T.WEED]:   { char: "W", name: "除草石", rule: "壊すと苔・苔石・卵が全部壊れる。" },
  };
  const CHAR_TO_TYPE = { ".": T.EMPTY };
  for (const key of Object.keys(INFO)) CHAR_TO_TYPE[INFO[key].char] = Number(key);

  const EGG_TURNS = 3;
  const MAX_BONUS = 2;        // 拡げ石の重ねがけ上限（5×5×5）
  const NEIGHBORS6 = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];

  function isPlant(type) { return type === T.MOSS || type === T.LEAF || type === T.EGG; }
  function isColor(type) { return type === T.RED || type === T.BLUE || type === T.YELLOW; }

  // -----------------------------------------------------------------
  // 状態
  // -----------------------------------------------------------------
  function createState(level, rng) {
    const [gx, gy, gz] = level.size;
    const cells = new Uint8Array(gx * gy * gz);
    const aux = new Uint8Array(gx * gy * gz);   // 石のひび(1) / 卵の残りターン
    let blocks = 0;
    level.layers.forEach((rows, y) => {
      rows.forEach((row, z) => {
        for (let x = 0; x < row.length; x++) {
          const type = CHAR_TO_TYPE[row[x]];
          if (type === undefined) throw new Error(`未知の文字 "${row[x]}" (level ${level.id})`);
          if (!type) continue;
          const idx = (y * gz + z) * gx + x;
          cells[idx] = type;
          if (type === T.EGG) aux[idx] = EGG_TURNS;
          blocks++;
        }
      });
    });
    return {
      level, gx, gy, gz, cells, aux, rng,
      blocks, turn: 0, limit: level.limit,
      bonus: 0,           // 次のタップの範囲の広がり（0=1個、1=3×3×3、2=5×5×5）
      status: "play",
      totalBroken: 0,
    };
  }

  function cloneState(state) {
    // rng は関数なので複製できない。solver は自前で rng を差し替える前提
    return Object.assign({}, state, { cells: state.cells.slice(), aux: state.aux.slice() });
  }

  function index(state, x, y, z) { return (y * state.gz + z) * state.gx + x; }
  function coords(state, idx) {
    const x = idx % state.gx;
    const z = ((idx / state.gx) | 0) % state.gz;
    const y = (idx / (state.gx * state.gz)) | 0;
    return [x, y, z];
  }
  function inGrid(state, x, y, z) {
    return x >= 0 && y >= 0 && z >= 0 && x < state.gx && y < state.gy && z < state.gz;
  }
  function cellAt(state, x, y, z) { return inGrid(state, x, y, z) ? state.cells[index(state, x, y, z)] : 0; }

  /**
   * 露出している（6近傍のどこかが空いている）セルだけがタップできる。
   * y=0 の下は床（紙）なので空きと見なさない。床がないと、1段の盤面は全部が
   * 裏からタップできてしまい「囲って隠す」設計が成り立たない。
   */
  function isExposed(state, idx) {
    const [x, y, z] = coords(state, idx);
    for (const [dx, dy, dz] of NEIGHBORS6) {
      if (y + dy < 0) continue;                                   // 床
      if (!cellAt(state, x + dx, y + dy, z + dz)) return true;
    }
    return false;
  }
  function canTap(state, idx) {
    const type = state.cells[idx];
    if (!type || type === T.ARMOR) return false;
    return isExposed(state, idx);
  }
  function tappableCells(state) {
    const list = [];
    for (let idx = 0; idx < state.cells.length; idx++) if (canTap(state, idx)) list.push(idx);
    return list;
  }

  // -----------------------------------------------------------------
  // 1手（＝1ターン）
  // 戻り値の waves は「同時に起きたこと」の配列。描画側はこれを順に見せる。
  // -----------------------------------------------------------------
  function tap(state, idx) {
    if (state.status !== "play") return { ok: false, reason: "ended" };
    if (!canTap(state, idx)) return { ok: false, reason: state.cells[idx] === T.ARMOR ? "armor" : "empty" };

    const radius = state.bonus;
    state.bonus = 0;
    const [tx, ty, tz] = coords(state, idx);

    // 最初の波：タップの範囲（立方体）。ここで壊れた分裂石だけが分裂する
    let hits = [];
    for (let dy = -radius; dy <= radius; dy++) {
      for (let dz = -radius; dz <= radius; dz++) {
        for (let dx = -radius; dx <= radius; dx++) {
          const x = tx + dx, y = ty + dy, z = tz + dz;
          if (inGrid(state, x, y, z) && state.cells[index(state, x, y, z)]) hits.push(index(state, x, y, z));
        }
      }
    }

    const waves = [];
    let cause = "tap";
    let guard = 0;
    while (hits.length > 0 && guard++ < 200) {
      const wave = { broken: [], cracked: [], spawned: [] };
      const seen = new Set();
      const next = new Set();

      for (const at of hits) {
        if (seen.has(at)) continue;
        seen.add(at);
        const type = state.cells[at];
        if (!type) continue;

        if (type === T.HARD && state.aux[at] === 0) {
          state.aux[at] = 1;
          wave.cracked.push(at);
          continue;
        }
        // 壊れる
        state.cells[at] = 0;
        state.aux[at] = 0;
        state.blocks--;
        state.totalBroken++;
        wave.broken.push({ idx: at, type });

        const [x, y, z] = coords(state, at);
        if (type === T.BOMB) {
          for (let dy = -1; dy <= 1; dy++) for (let dz = -1; dz <= 1; dz++) for (let dx = -1; dx <= 1; dx++) {
            if (inGrid(state, x + dx, y + dy, z + dz)) next.add(index(state, x + dx, y + dy, z + dz));
          }
        } else if (isColor(type)) {
          for (let i = 0; i < state.cells.length; i++) if (state.cells[i] === type) next.add(i);
        } else if (type === T.LINE_X) {
          for (let i = 0; i < state.gx; i++) next.add(index(state, i, y, z));
        } else if (type === T.LINE_Y) {
          for (let i = 0; i < state.gy; i++) next.add(index(state, x, i, z));
        } else if (type === T.LINE_Z) {
          for (let i = 0; i < state.gz; i++) next.add(index(state, x, y, i));
        } else if (type === T.WEED) {
          for (let i = 0; i < state.cells.length; i++) if (isPlant(state.cells[i])) next.add(i);
        } else if (type === T.AMP) {
          state.bonus = Math.min(MAX_BONUS, state.bonus + 1);
        } else if (type === T.SPLIT && cause === "tap") {
          // 分裂：空いている隣に土を2つ。どこに出るかは乱数（シードで再現する）
          const empties = [];
          for (const [dx, dy, dz] of NEIGHBORS6) {
            if (inGrid(state, x + dx, y + dy, z + dz) && !state.cells[index(state, x + dx, y + dy, z + dz)]) {
              empties.push(index(state, x + dx, y + dy, z + dz));
            }
          }
          for (let n = 0; n < 2 && empties.length > 0; n++) {
            const pick = empties.splice(Math.floor(state.rng() * empties.length), 1)[0];
            wave.spawned.push({ idx: pick, type: T.PLAIN, from: at });
          }
        }
      }
      // 氷：この波で壊れたセルの隣にある氷は次の波で割れる
      for (const b of wave.broken) {
        const [x, y, z] = coords(state, b.idx);
        for (const [dx, dy, dz] of NEIGHBORS6) {
          if (cellAt(state, x + dx, y + dy, z + dz) === T.ICE) next.add(index(state, x + dx, y + dy, z + dz));
        }
      }
      // 分裂で生まれた土は、この波の連鎖には巻き込まれない（置いてから次へ）
      for (const s of wave.spawned) {
        if (state.cells[s.idx]) continue;
        state.cells[s.idx] = s.type;
        state.blocks++;
      }
      waves.push(wave);
      hits = [...next].filter((i) => state.cells[i]);
      cause = "chain";
    }

    // ターン終了
    state.turn++;
    const turnEnd = { hatched: [], grown: [] };
    if (state.blocks === 0) {
      state.status = "clear";
    } else {
      // 苔が増える（この時点で苔だったものだけ。孵ったばかりの苔は次のターンから）
      const mosses = [];
      for (let i = 0; i < state.cells.length; i++) if (state.cells[i] === T.MOSS) mosses.push(i);
      for (const at of mosses) {
        const [x, y, z] = coords(state, at);
        const empties = [];
        for (const [dx, dy, dz] of NEIGHBORS6) {
          if (inGrid(state, x + dx, y + dy, z + dz) && !state.cells[index(state, x + dx, y + dy, z + dz)]) {
            empties.push(index(state, x + dx, y + dy, z + dz));
          }
        }
        if (empties.length === 0) continue;
        const pick = empties[Math.floor(state.rng() * empties.length)];
        state.cells[pick] = T.LEAF;
        state.blocks++;
        turnEnd.grown.push({ idx: pick, type: T.LEAF, from: at });
      }
      for (let i = 0; i < state.cells.length; i++) {
        if (state.cells[i] !== T.EGG) continue;
        state.aux[i]--;
        if (state.aux[i] === 0) {
          state.cells[i] = T.MOSS;
          turnEnd.hatched.push(i);
        }
      }
      if (state.turn >= state.limit) state.status = "fail";
    }
    return { ok: true, waves, turnEnd, status: state.status };
  }

  /** レベルに出てくる種類（説明パネル用） */
  function typesInLevel(level) {
    const found = new Set();
    for (const rows of level.layers) for (const row of rows) for (const ch of row) {
      const type = CHAR_TO_TYPE[ch];
      if (type) found.add(type);
    }
    // 卵は苔になるので、卵があれば苔の説明も出す
    if (found.has(T.EGG)) found.add(T.MOSS);
    if (found.has(T.MOSS)) found.add(T.LEAF);
    return [...found].sort((a, b) => a - b);
  }

  return {
    T, INFO, CHAR_TO_TYPE, EGG_TURNS, MAX_BONUS, NEIGHBORS6,
    createState, cloneState, index, coords, inGrid, cellAt,
    isExposed, canTap, tappableCells, tap, typesInLevel, isPlant, isColor,
  };
});
