// -----------------------------------------------------------------
// ARCANE ARMOR の戦闘ロジックをヘッドレスで回す検証。
//
//   node prototypes/arcane-armor/verify.mjs            … 決定性・終了・勝率の表
//   node prototypes/arcane-armor/verify.mjs --battles 200
//
// index.html の <SIM>〜</SIM> 区間だけを取り出して実行する（描画・DOMには触らない区間）。
// 見ていること:
//   1. 同じシード＋同じ指令列で2回回すと最後まで同じ指紋になる（リプレイが成り立つ前提）
//   2. どの戦闘も制限時間内に決着する
//   3. 指令あり（AI）対 指令なし の勝率 ＝ 指令に意味があるか
// -----------------------------------------------------------------
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(here, "index.html"), "utf8");
const start = html.indexOf("// <SIM>"), end = html.indexOf("// </SIM>");
if (start < 0 || end < 0) throw new Error("<SIM> 区間が見つからない");
const sim = new Function(`${html.slice(start, end)}
  return { BALANCE, makeRandomGenerator, createBattle, stepBattle, needsPlayerCommand, issueOrder, chooseAiOrder, battleFingerprint, TEAM_PLAYER, TEAM_ENEMY };`)();

const argument = (name, fallback) => {
  const index = process.argv.indexOf(name);
  return index >= 0 ? Number(process.argv[index + 1]) : fallback;
};
const battles = argument("--battles", 60);
const tailTicks = 120;

/** playerPolicy: "ai" | "none" | 指令ログ（リプレイ） */
function run(seed, playerPolicy) {
  const battle = sim.createBattle(seed);
  const replay = Array.isArray(playerPolicy) ? new Map(playerPolicy.map((order) => [order.tick, order.skillId])) : null;
  const autoRandom = sim.makeRandomGenerator(seed ^ 0x5bd1e995);
  let guard = 0;
  while (!battle.over || battle.tick < battle.overTick + tailTicks) {
    if (replay) {
      const skillId = replay.get(battle.tick);
      if (skillId) sim.issueOrder(battle, sim.TEAM_PLAYER, skillId);
    } else if (sim.needsPlayerCommand(battle)) {
      if (playerPolicy === "ai") {
        const choice = sim.chooseAiOrder(battle, sim.TEAM_PLAYER, autoRandom);
        if (choice) sim.issueOrder(battle, sim.TEAM_PLAYER, choice);
      }
      battle.playerCommandTick = battle.tick;
    }
    sim.stepBattle(battle);
    battle.events.length = 0;
    if (++guard > 60 * 400) throw new Error(`seed ${seed}: 終わらない`);
  }
  return battle;
}

let failures = 0;
const summary = { ai: { wins: 0, seconds: 0 }, none: { wins: 0, seconds: 0 } };
for (let index = 0; index < battles; index++) {
  const seed = 1000 + index * 7919;
  const live = run(seed, "ai");
  // 記録した自軍の指令だけを渡して再計算する。敵の指令はシードから同じものが出るはず
  const playerOrders = live.orderLog.filter((order) => order.team === sim.TEAM_PLAYER);
  const replayed = run(seed, playerOrders);
  if (sim.battleFingerprint(live) !== sim.battleFingerprint(replayed) || live.overTick !== replayed.overTick) {
    failures++;
    console.log(`NG 決定性: seed ${seed} live ${sim.battleFingerprint(live)} / replay ${sim.battleFingerprint(replayed)}`);
  }
  const idle = run(seed, "none");
  for (const [key, battle] of [["ai", live], ["none", idle]]) {
    if (battle.winner === sim.TEAM_PLAYER) summary[key].wins++;
    summary[key].seconds += battle.overTick / sim.BALANCE.tickRate;
  }
}
const percent = (value) => `${(value / battles * 100).toFixed(0)}%`;
console.log(`戦闘数 ${battles}`);
console.log(`自軍AI指令  : 勝率 ${percent(summary.ai.wins)}  平均 ${(summary.ai.seconds / battles).toFixed(1)}秒`);
console.log(`自軍指令なし: 勝率 ${percent(summary.none.wins)}  平均 ${(summary.none.seconds / battles).toFixed(1)}秒`);
console.log(failures === 0 ? "OK 決定性（リプレイ一致）" : `NG ${failures} 件`);
process.exit(failures === 0 ? 0 : 1);
