// -----------------------------------------------------------------
// Dragon Tide をヘッドレスで決定的に回すための共通部分（dt-headless.mjs / dt-bench.mjs）
//
// 時計（performance.now / Date.now）とタイマー（setTimeout / setInterval / requestAnimationFrame）を
// 差し替えて、window.__dtStep(ms) で 1 歩ずつ進める。実機の速さや背景タブの間引きに左右されない。
// -----------------------------------------------------------------
import { pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

/** ゲームを開き、ゲームループが登録されるまで待つ。errors には実行時エラーが溜まる。 */
export async function openGame({ file, seed }) {
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
  return { browser, page, errors };
}
