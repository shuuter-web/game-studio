// -----------------------------------------------------------------
// Dragon Tide の調査用：決まった地域でオートプレイを回し、途中で式を評価したり画面の絵を撮ったりする
//
//   node tools/dt-probe.mjs --stage 0,11 --ticks 1500 [--seed 4242] [--species fire] [--file …]
//        [--setup "式"]（地域に入った直後に1回）[--each "式"]（毎歩）[--probe "式"]（--every 歩ごとと最後に出す）
//        [--shot out.png]（最後に画面を撮る）[--shot-every 500]（out-00500.png のように途中も撮る）
//
// dt-headless.mjs は指紋を比べる道具、こちらは新しい仕掛けが動いているか・どう見えるかを確かめる道具。
// -----------------------------------------------------------------
import path from "node:path";
import { fileURLToPath } from "node:url";
import { openGame } from "./dt-harness.mjs";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const arg = (name, fallback) => { const i = args.indexOf(`--${name}`); return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback; };
const file = path.resolve(REPO_ROOT, arg("file", "prototypes/dragon-tide/index.html"));
const ticks = Number(arg("ticks", "1000")), every = Number(arg("every", "0")), shotEvery = Number(arg("shot-every", "0"));
const shot = arg("shot", ""), setup = arg("setup", ""), each = arg("each", ""), probe = arg("probe", ""), stage = arg("stage", "");
const STEP_MS = 16;

const { browser, page, errors } = await openGame({ file, seed: arg("seed", "4242") });
await page.evaluate((sp) => { startAutoplay(sp); }, arg("species", "fire"));
for (let guard = 0; !(await page.evaluate(() => gameState === "playing")); guard++) {
  if (guard > 5000) throw new Error("ランが始まらなかった");
  await page.evaluate((ms) => window.__dtStep(ms), STEP_MS);
}
if (stage) { const [era, shape] = stage.split(",").map(Number); await page.evaluate(([e, sh]) => debugStartStage(e, sh), [era, shape]); }
if (setup) await page.evaluate((expr) => (0, eval)(expr), setup);
const show = async (t) => { if (probe) console.log(`tick ${t}`, JSON.stringify(await page.evaluate((expr) => (0, eval)(expr), probe))); };
for (let t = 1; t <= ticks && !errors.length; t++) {
  await page.evaluate(([ms, expr]) => { window.__dtStep(ms); if (expr) (0, eval)(expr); }, [STEP_MS, each]);
  if (every > 0 && t % every === 0) await show(t);
  if (shot && shotEvery > 0 && t % shotEvery === 0) await page.screenshot({ path: shot.replace(/\.png$/, `-${String(t).padStart(5, "0")}.png`) });
}
await show(ticks);
if (shot) await page.screenshot({ path: shot });
if (errors.length) { console.log("実行時エラー:\n" + errors.slice(0, 5).join("\n")); process.exitCode = 1; }
await browser.close();
