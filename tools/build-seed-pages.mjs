// -----------------------------------------------------------------
// ideas/seeds/*.md → docs/seeds/*.html を生成する。
//
// 企画書（docs/pitch/）から各案の全文へリンクするため。
// 種は増え続けるので、企画書を上げるたびに手で書き写すのは続かない。
// 記法は種テンプレートで使う範囲（見出し / 箇条書き / 表 / 引用 / 強調 / コード）に絞ってある。
//
//   node tools/build-seed-pages.mjs
//   node tools/build-seed-pages.mjs --check   … 生成物が最新かだけ確認（書き込まない）
// -----------------------------------------------------------------
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SEEDS_DIR = path.join(REPO_ROOT, "ideas/seeds");
const OUT_DIR   = path.join(REPO_ROOT, "docs/seeds");

// status ごとの見せ方。並び順もこの定義順にする
const STATUS = {
  promoted: { label: "GDD化", tone: "ok",   note: "本制作の設計へ進んだ種" },
  picked:   { label: "採用",   tone: "ok",   note: "判定を通過し、最大の賭けをプロトで潰す段階" },
  seed:     { label: "保留",   tone: "warn", note: "肉付け済み。判定待ち、または条件が変われば復活する" },
  dropped:  { label: "却下",   tone: "ng",   note: "落とした理由ごと残す。月次で見返し、市場が動いたら拾い直す" },
};

// -----------------------------------------------------------------
// Markdown → HTML（種テンプレートで使う記法だけ）
// -----------------------------------------------------------------
function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** 強調とコード。escapeHtml の後に呼ぶ（** と ` は escape で壊れない） */
function inline(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, (_, code) => `<code>${code}</code>`)
    .replace(/\*\*([^*]+)\*\*/g, (_, bold) => `<strong>${bold}</strong>`);
}

const isWide = (ch) => !!ch && ch.codePointAt(0) > 0x2e80;

/**
 * 折り返された行をつなぐ。日本語同士なら空白を入れない。
 * 空白を入れると和文の途中に隙間ができて読みにくくなる。
 */
function joinWrapped(lines) {
  return lines.reduce((acc, line) => {
    if (!acc) return line;
    const left = acc[acc.length - 1], right = line[0];
    return acc + (isWide(left) && isWide(right) ? "" : " ") + line;
  }, "");
}

function renderTable(rows) {
  // 2行目が |---|---| なら1行目は見出し
  const hasHeader = rows.length > 1 && /^\|[-: |]+\|$/.test(rows[1]);
  const cells = (row) => row.slice(1, -1).split("|").map((c) => c.trim());
  const body = hasHeader ? rows.slice(2) : rows;
  const out = ["<div class=\"scroll\"><table>"];
  if (hasHeader) {
    out.push("<thead><tr>" + cells(rows[0]).map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead>");
  }
  out.push("<tbody>");
  for (const row of body) {
    out.push("<tr>" + cells(row).map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>");
  }
  out.push("</tbody></table></div>");
  return out.join("\n");
}

function markdownToHtml(markdown) {
  const lines = markdown.split("\n");
  const out = [];
  let i = 0;

  const isBlockStart = (line) =>
    /^#{1,4} /.test(line) || /^\|/.test(line) || /^> /.test(line) ||
    /^- /.test(line) || /^\d+\. /.test(line) || line.trim() === "";

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === "") { i++; continue; }

    const heading = line.match(/^(#{1,4}) (.*)$/);
    if (heading) {
      const level = Math.min(4, heading[1].length + 1);   // ページのh1は表題なので1段下げる
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      i++;
      continue;
    }

    if (/^\|/.test(line)) {
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) rows.push(lines[i++].trim());
      out.push(renderTable(rows));
      continue;
    }

    if (/^> /.test(line)) {
      const quote = [];
      while (i < lines.length && /^> ?/.test(lines[i])) quote.push(lines[i++].replace(/^> ?/, ""));
      out.push(`<blockquote>${inline(joinWrapped(quote.filter((l) => l.trim())))}</blockquote>`);
      continue;
    }

    const bullet = /^- /.test(line);
    if (bullet || /^\d+\. /.test(line)) {
      const tag = bullet ? "ul" : "ol";
      const items = [];
      while (i < lines.length) {
        const match = lines[i].match(bullet ? /^- (.*)$/ : /^\d+\. (.*)$/);
        if (!match) {
          // 字下げされた行は直前の項目の続き
          if (items.length > 0 && /^\s+\S/.test(lines[i])) { items[items.length - 1].push(lines[i].trim()); i++; continue; }
          break;
        }
        items.push([match[1]]);
        i++;
      }
      out.push(`<${tag}>` + items.map((parts) => `<li>${inline(joinWrapped(parts))}</li>`).join("") + `</${tag}>`);
      continue;
    }

    const paragraph = [];
    while (i < lines.length && !isBlockStart(lines[i])) paragraph.push(lines[i++].trim());
    out.push(`<p>${inline(joinWrapped(paragraph))}</p>`);
  }
  return out.join("\n");
}

// -----------------------------------------------------------------
// 種ファイルの読み込み
// -----------------------------------------------------------------
function parseSeed(file) {
  const raw = fs.readFileSync(path.join(SEEDS_DIR, file), "utf8");
  const match = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  const meta = {};
  let body = raw;
  if (match) {
    for (const line of match[1].split("\n")) {
      const kv = line.match(/^([a-z-]+):\s*(.*)$/);
      if (kv) meta[kv[1]] = kv[2].replace(/\s+#.*$/, "").trim();
    }
    body = match[2];
  }
  // 本文先頭の「# 🌱 PLAYSEED: タイトル」は表題と重複するので落とす
  body = body.replace(/^\s*# .*\n/, "");
  return {
    file,
    slug: file.replace(/\.md$/, ""),
    id: meta["seed-id"] || file.slice(0, 6),
    title: meta.title || file,
    oneLiner: meta["one-liner"] || "",
    author: meta.author || "",
    date: meta.date || "",
    tags: (meta.tags || "").replace(/^\[|\]$/g, "").split(",").map((t) => t.trim()).filter(Boolean),
    status: STATUS[meta.status] ? meta.status : "seed",
    html: markdownToHtml(body),
  };
}

// -----------------------------------------------------------------
// ページの組み立て
// -----------------------------------------------------------------
function page({ title, description, body, depth }) {
  const up = "../".repeat(depth);
  return `<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>${escapeHtml(title)}</title>
${description ? `<meta name="description" content="${escapeHtml(description)}" />\n` : ""}<link rel="stylesheet" href="${up}seed.css" />
</head>
<body>
<div class="wrap">
${body}
</div>
</body>
</html>
`;
}

function seedPage(seed) {
  const st = STATUS[seed.status];
  const body = `
<nav class="crumb"><a href="./">← 種の一覧</a> ／ <a href="../../">プロトタイプ一覧</a></nav>
<header>
  <div class="kicker">${escapeHtml(seed.id)} ／ PLAYSEED</div>
  <h1>${escapeHtml(seed.title)}</h1>
  ${seed.oneLiner ? `<p class="one-liner">${escapeHtml(seed.oneLiner)}</p>` : ""}
  <div class="meta">
    <span class="badge ${st.tone}">${st.label}</span>
    ${seed.tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}
    ${seed.date ? `<span class="dim">${escapeHtml(seed.date)}</span>` : ""}
    ${seed.author ? `<span class="dim">${escapeHtml(seed.author)}</span>` : ""}
  </div>
</header>
<main>
${seed.html}
</main>
<footer>
  原文は <code>ideas/seeds/${escapeHtml(seed.file)}</code>。
  このページは <code>tools/build-seed-pages.mjs</code> が生成している。
  <a href="./">← 種の一覧へ</a>
</footer>`;
  return page({ title: `${seed.title} — ${seed.id} PLAYSEED`, description: seed.oneLiner, body, depth: 0 });
}

function indexPage(seeds) {
  const groups = Object.keys(STATUS)
    .map((key) => ({ key, ...STATUS[key], items: seeds.filter((s) => s.status === key).sort((a, b) => b.id.localeCompare(a.id)) }))
    .filter((g) => g.items.length > 0);

  const body = `
<nav class="crumb"><a href="../../">← プロトタイプ一覧</a></nav>
<header>
  <div class="kicker">ideas / seeds</div>
  <h1>種の一覧（PLAYSEED）</h1>
  <p class="one-liner">
    GDD化の前段。お題ごとに発散した案を1枚のプロットに落とし、トライアングル判定（面白さ・市場性・新規性）で
    採用・保留・却下に振り分けている。落とした種も理由ごと残してある。
  </p>
  <div class="meta">
    <span class="dim">全 ${seeds.length} 件</span>
    ${groups.map((g) => `<span class="badge ${g.tone}">${g.label} ${g.items.length}</span>`).join("")}
    <span class="dim"><a href="log.html">発散の記録（全スプリント）</a></span>
  </div>
</header>
<main>
${groups.map((g) => `
<section class="group">
  <h2><span class="badge ${g.tone}">${g.label}</span> <span class="group-note">${g.note}</span></h2>
  <ul class="seed-list">
    ${g.items.map((s) => `<li>
      <a href="${s.slug}.html">
        <span class="sid">${escapeHtml(s.id)}</span>
        <span class="stitle">${escapeHtml(s.title)}</span>
        <span class="sone">${escapeHtml(s.oneLiner)}</span>
      </a>
    </li>`).join("")}
  </ul>
</section>`).join("")}
</main>
<footer>
  原文は <code>ideas/seeds/</code>。このページは <code>tools/build-seed-pages.mjs</code> が生成している。
</footer>`;
  return page({ title: "種の一覧（PLAYSEED） — Game Studio", description: "発散した企画の種と、その判定の記録", body, depth: 0 });
}

function logPage(markdown) {
  const body = `
<nav class="crumb"><a href="./">← 種の一覧</a> ／ <a href="../../">プロトタイプ一覧</a></nav>
<header>
  <div class="kicker">ideas / seeds</div>
  <h1>発散の記録（Raw Seeds Log）</h1>
  <p class="one-liner">
    採否の前に、発散した全案を残したログ。不採用も練習回も消さずに蓄積し、月次で見返して
    市場が動いて化けた種を拾い直すためのもの。
  </p>
</header>
<main class="log">
${markdownToHtml(markdown.replace(/^# .*\n/, ""))}
</main>
<footer>
  原文は <code>ideas/seeds/_raw-seeds-log.md</code>。
  <a href="./">← 種の一覧へ</a>
</footer>`;
  return page({ title: "発散の記録（Raw Seeds Log） — Game Studio", description: "発散した全案の蓄積ログ", body, depth: 0 });
}

const CSS = `/* 種のページ共通スタイル。試作 voxel-sketch と同じ紙とインクの系統に揃えてある。
   tools/build-seed-pages.mjs が参照するだけで、生成物ではないので手で編集してよい。 */
:root {
  --paper: #efe8da; --paper-2: #f7f2e8;
  --ink: #2b2620; --ink-2: #6c645a;
  --rule: rgba(43,38,32,0.28); --rule-soft: rgba(43,38,32,0.14);
  --accent: #b4552e; --ok: #4d7c46; --warn: #a8762a; --ng: #a6453c;
}
@media (prefers-color-scheme: dark) {
  :root {
    --paper: #1a1814; --paper-2: #221f1a;
    --ink: #e8e0d2; --ink-2: #9c9285;
    --rule: rgba(232,224,210,0.30); --rule-soft: rgba(232,224,210,0.14);
    --accent: #e2895f; --ok: #86b87c; --warn: #d9ab5e; --ng: #dd8078;
  }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: var(--paper); color: var(--ink);
  font-family: "Hiragino Sans", "Noto Sans JP", system-ui, sans-serif;
  line-height: 1.85; -webkit-text-size-adjust: 100%;
  padding: 0 1.1rem 5rem;
}
.wrap { max-width: 780px; margin: 0 auto; }
a { color: var(--accent); text-underline-offset: 2px; }

.crumb { padding-top: 1.4rem; font-size: 0.78rem; color: var(--ink-2); }
.crumb a { color: var(--ink-2); }
header { padding: 1.6rem 0 1.2rem; border-bottom: 2px solid var(--ink); }
.kicker {
  font-family: ui-monospace, monospace; font-size: 0.72rem;
  letter-spacing: 0.16em; color: var(--ink-2);
}
h1 { font-size: clamp(1.4rem, 5vw, 2.05rem); line-height: 1.35; margin: 0.4rem 0 0.6rem; }
.one-liner { font-size: 0.98rem; }
.meta { margin-top: 1rem; display: flex; flex-wrap: wrap; gap: 0.4rem 0.6rem; align-items: center; font-size: 0.75rem; }
.dim { color: var(--ink-2); font-family: ui-monospace, monospace; }
.badge {
  font-family: ui-monospace, monospace; font-size: 0.7rem; letter-spacing: 0.08em;
  border: 1.5px solid currentColor; border-radius: 2px; padding: 0.1em 0.55em;
}
.badge.ok { color: var(--ok); } .badge.warn { color: var(--warn); } .badge.ng { color: var(--ng); }
.tag {
  font-family: ui-monospace, monospace; font-size: 0.68rem;
  border: 1.2px solid var(--rule); border-radius: 2px; padding: 0.08em 0.45em; color: var(--ink-2);
}

main h2 {
  font-size: 1.05rem; margin: 2.4rem 0 0.8rem;
  padding-bottom: 0.35rem; border-bottom: 1.5px solid var(--rule);
}
main h3 { font-size: 0.96rem; margin: 1.6rem 0 0.4rem; }
main h4 { font-size: 0.9rem; margin: 1.2rem 0 0.3rem; color: var(--ink-2); }
p { margin: 0.7rem 0; }
ul, ol { margin: 0.7rem 0 0.7rem 1.3rem; }
li { margin: 0.3rem 0; }
code {
  font-family: ui-monospace, monospace; font-size: 0.88em;
  background: var(--rule-soft); border-radius: 2px; padding: 0.08em 0.34em;
}
blockquote {
  margin: 1rem 0; padding: 0.6rem 0.9rem;
  border-left: 3px solid var(--accent); background: var(--paper-2);
  font-size: 0.92rem; color: var(--ink-2);
}
.scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.86rem; }
th, td { text-align: left; padding: 0.45rem 0.6rem; border-bottom: 1px solid var(--rule-soft); vertical-align: top; }
th {
  font-family: ui-monospace, monospace; font-size: 0.7rem; letter-spacing: 0.05em;
  color: var(--ink-2); font-weight: 400; border-bottom: 1.5px solid var(--rule); white-space: nowrap;
}

/* 一覧 */
.group { margin-top: 2.4rem; }
.group h2 { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.5rem; }
.group-note { font-size: 0.76rem; color: var(--ink-2); font-weight: 400; }
.seed-list { list-style: none; margin: 0.6rem 0 0; }
.seed-list li { margin: 0; }
.seed-list a {
  display: block; text-decoration: none; color: inherit;
  border-bottom: 1px solid var(--rule-soft); padding: 0.7rem 0.2rem;
}
.seed-list a:hover { background: var(--paper-2); }
.sid { font-family: ui-monospace, monospace; font-size: 0.7rem; color: var(--ink-2); margin-right: 0.6rem; }
.stitle { font-weight: 700; }
.sone { display: block; font-size: 0.82rem; color: var(--ink-2); line-height: 1.6; }

.log h2 { margin-top: 2.8rem; }
.log h3 { margin-top: 1.8rem; }

footer {
  margin-top: 3.5rem; padding-top: 1rem; border-top: 1.5px solid var(--rule);
  font-size: 0.78rem; color: var(--ink-2);
}
footer a { color: var(--ink-2); }
`;

// -----------------------------------------------------------------
// 実行
// -----------------------------------------------------------------
const checkOnly = process.argv.includes("--check");
const files = fs.readdirSync(SEEDS_DIR).filter((f) => /^PS-\d+.*\.md$/.test(f)).sort();
const seeds = files.map(parseSeed);

const outputs = new Map();
outputs.set("seed.css", CSS);
outputs.set("index.html", indexPage(seeds));
outputs.set("log.html", logPage(fs.readFileSync(path.join(SEEDS_DIR, "_raw-seeds-log.md"), "utf8")));
for (const seed of seeds) outputs.set(`${seed.slug}.html`, seedPage(seed));

let stale = 0;
fs.mkdirSync(OUT_DIR, { recursive: true });
for (const [name, content] of outputs) {
  const target = path.join(OUT_DIR, name);
  const current = fs.existsSync(target) ? fs.readFileSync(target, "utf8") : null;
  if (current === content) continue;
  stale++;
  if (!checkOnly) fs.writeFileSync(target, content, "utf8");
}
// 種を消したときに生成物が残らないようにする
for (const name of fs.readdirSync(OUT_DIR)) {
  if (outputs.has(name)) continue;
  stale++;
  if (!checkOnly) fs.rmSync(path.join(OUT_DIR, name));
}

if (checkOnly) {
  if (stale > 0) {
    console.error(`docs/seeds/ が古い（${stale}件）。node tools/build-seed-pages.mjs を実行して結果もコミットすること。`);
    process.exit(1);
  }
  console.log(`docs/seeds/ は最新（${seeds.length} 件の種）`);
} else {
  console.log(`生成: ${outputs.size} ファイル（種 ${seeds.length} 件）→ docs/seeds/`);
}
