// -----------------------------------------------------------------
// Dragon Tide の名前の表（案帳 DT-635）
//
//   node tools/dt-names.mjs [--file prototypes/dragon-tide/index.html] [--out docs/narrative/dragon-tide-names.md]
//
// ゲームを開いて、竜種・特殊個体・敵・強化カードとアーティファクト・地域の
// 「内部の名前（キー）・画面の名前・説明があるか・図鑑に載っているか」を1つの表に書き出す。
// 図鑑に載っているかは、図鑑の各ページを実際に組み立てて、その文字の中に画面の名前があるかで見る
// （図鑑の作り方を写して判定すると、図鑑の作りが変わったときに表だけ古くなるため）。
// 名前はコード（STRINGS・SPECIES_DEFS・CODEX_*）が正本で、この表は写し。名前を変えたら作り直す。
// -----------------------------------------------------------------
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { openGame } from "./dt-harness.mjs";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const arg = (name, fallback) => { const i = args.indexOf(`--${name}`); return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback; };
const file = path.resolve(REPO_ROOT, arg("file", "prototypes/dragon-tide/index.html"));
const out = path.resolve(REPO_ROOT, arg("out", "docs/narrative/dragon-tide-names.md"));

const { browser, page, errors } = await openGame({ file, seed: "1", noRender: true });
const data = await page.evaluate(() => {
  // 図鑑の全ページの文字を集める
  const tabs = ["enemy", "building", "region", "shot", "dragon", "misc", "special", "card", "lore"];
  const codexText = {};
  for (const t of tabs) { codexTab = t; renderCodex(); codexText[t] = codexOverlayEl.textContent; }
  codexOverlayEl.classList.remove("visible");
  const inCodex = (name, tab) => !!name && codexText[tab].includes(name);
  const plain = (s) => String(s ?? "").replace(/^[^\p{L}\p{N}]+/u, "").trim();

  const species = Object.entries(SPECIES_DEFS).map(([key, d]) => ({
    key, name: d.ja, en: d.en ?? "", desc: !!d.desc, codex: inCodex(d.ja, "dragon"),
  }));
  const specials = Object.values(SPECIAL_DEFS).map((d) => ({
    key: d.key, name: d.name, en: "", desc: !!(CODEX_SPECIAL_DESC[d.key] ?? CODEX_SPECIAL_DESC[d.id]),
    codex: inCodex(d.name, "special"),
  }));
  const enemies = Object.keys(MOVER_DEFS).map((key) => {
    const name = CODEX_ENEMY_NAMES[key] ?? "";
    const debug = plain(DEBUG_ENEMY_LABELS[key] ?? "").replace(/[（(].*$/, "");
    return { key, name, en: "", debug, desc: !!MOVER_DEFS[key].attack, codex: inCodex(name, "enemy"),
      debugDiffers: !!name && !!debug && debug !== name.replace(/[（(].*$/, "") };
  });
  // 図鑑の「強化カード」ページに出るカード（通常・アーティファクト）
  const perks = PERK_CARD_DEFS.map((c) => {
    const t = perkCardText(c.id) ?? {};
    return { key: c.id, kind: c.artifact ? "アーティファクト" : "強化カード", name: t.name ?? "", desc: !!t.desc, codex: inCodex(t.name, "card") };
  });
  // レベルアップの三択の元になるカード（CARD_DEFS。特殊個体を加える sp_* など）。図鑑はどのページに載っていてもよい
  const anyTab = (name) => tabs.some((t) => inCodex(name, t));
  const cards = CARD_DEFS.map((c) => {
    const s = STRINGS.cards[c.id] ?? {};
    return { key: c.id, kind: c.id.startsWith("sp_") ? "特殊個体を加える" : "レベルアップのカード", name: s.name ?? "", desc: !!s.desc, codex: anyTab(s.name) };
  });
  const regions = STAGE_SHAPES.map((sh, i) => ({
    key: sh.id, name: STRINGS.shapeNames[i] ?? "", en: "", desc: true, codex: inCodex(STRINGS.shapeNames[i], "region"),
  }));
  return { version: GAME_VERSION, species, specials, enemies, perks, cards, regions };
});
await browser.close();
if (errors.length) { console.error(errors.join("\n")); process.exit(1); }

const mark = (b) => (b ? "○" : "**×**");
const esc = (s) => String(s).replace(/\|/g, "\\|");
const lines = [];
lines.push("# Dragon Tide 名前の表（竜種・特殊個体・敵・強化カード・アーティファクト・地域）");
lines.push("");
lines.push(`ゲームの版 ${data.version} から \`node tools/dt-names.mjs\` で作った写し（案帳 DT-635）。名前の正本はコード（STRINGS・SPECIES_DEFS・CODEX_*）。名前を変えたら作り直す。`);
lines.push("「図鑑」は図鑑の各ページを組み立てて、その文字の中に画面の名前があるかで見ている。× は図鑑に載っていないもの。");
lines.push("");
const gaps = [];
const table = (title, rows, cols) => {
  lines.push(`## ${title}（${rows.length}）`, "");
  lines.push("| " + cols.map((c) => c[0]).join(" | ") + " |");
  lines.push("|" + cols.map(() => "---").join("|") + "|");
  for (const r of rows) lines.push("| " + cols.map((c) => esc(c[1](r))).join(" | ") + " |");
  lines.push("");
  for (const r of rows) if (!r.codex || !r.name) gaps.push(`${title}：${r.name || "（名前なし）"}（${r.key}）${r.name ? "が図鑑に無い" : "に画面の名前が無い"}`);
};
table("竜種", data.species, [["内部の名前", (r) => r.key], ["画面の名前", (r) => r.name], ["英語", (r) => r.en], ["説明", (r) => mark(r.desc)], ["図鑑", (r) => mark(r.codex)]]);
table("特殊個体", data.specials, [["内部の名前", (r) => r.key], ["画面の名前", (r) => r.name], ["説明", (r) => mark(r.desc)], ["図鑑", (r) => mark(r.codex)]]);
table("敵", data.enemies, [["内部の名前", (r) => r.key], ["画面の名前（図鑑）", (r) => r.name], ["デバッグの名札", (r) => r.debug + (r.debugDiffers ? " ※違う" : "")], ["図鑑", (r) => mark(r.codex)]]);
table("強化カード・アーティファクト（図鑑の強化カード）", data.perks, [["内部の名前", (r) => r.key], ["種類", (r) => r.kind], ["画面の名前", (r) => r.name], ["説明", (r) => mark(r.desc)], ["図鑑", (r) => mark(r.codex)]]);
table("レベルアップのカード（CARD_DEFS）", data.cards, [["内部の名前", (r) => r.key], ["種類", (r) => r.kind], ["画面の名前", (r) => r.name], ["説明", (r) => mark(r.desc)], ["図鑑", (r) => mark(r.codex)]]);
table("地域", data.regions, [["内部の名前", (r) => r.key], ["画面の名前", (r) => r.name], ["図鑑", (r) => mark(r.codex)]]);
const debugDiff = data.enemies.filter((r) => r.debugDiffers);
lines.push("## そろっていない所", "");
if (!gaps.length && !debugDiff.length) lines.push("なし。");
for (const g of gaps) lines.push(`- ${g}`);
for (const r of debugDiff) lines.push(`- 敵：デバッグの名札「${r.debug}」と図鑑の名前「${r.name}」が違う（${r.key}）`);
lines.push("");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, lines.join("\n"));
console.log(`wrote ${path.relative(REPO_ROOT, out)}  gaps=${gaps.length} debugDiff=${debugDiff.length}`);
for (const g of gaps) console.log("  " + g);
for (const r of debugDiff) console.log(`  debug ${r.key}: ${r.debug} / ${r.name}`);
