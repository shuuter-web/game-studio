// -----------------------------------------------------------------
// prototypes/ の単一HTMLゲームを機械的に検証する。
//
//   node tools/check.mjs                     … prototypes/*/index.html を全部
//   node tools/check.mjs prototypes/dragon-tide/index.html
//   node tools/check.mjs --hook              … Claude Code の hook から（stdinのJSONで対象を決める）
//
// AIが「できました」と自己申告する代わりに、これを通してから完了報告するためのもの。
// 追加したい検査は CHECKS に関数を足す（引数はファイル1件分のコンテキスト）。
// -----------------------------------------------------------------
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// -----------------------------------------------------------------
// 検査本体
// -----------------------------------------------------------------

/**
 * <script> の中身を BOM なし UTF-8 で書き出して `node --check` にかける。
 * PowerShell の Out-File は UTF-16 になり文字化けで誤判定するため、必ず Node 側で書く。
 */
function checkSyntax({ scripts, fileLabel }, fail) {
  scripts.forEach((script, index) => {
    const temp = path.join(os.tmpdir(), `dtcheck-${process.pid}-${index}.js`);
    fs.writeFileSync(temp, script.code, { encoding: "utf8" });
    try {
      execFileSync(process.execPath, ["--check", temp], { stdio: "pipe" });
    } catch (error) {
      // node のエラー行番号を、元HTMLでの行番号に読み替えて出す
      const raw = String(error.stderr || error.message);
      const shifted = raw.replace(
        new RegExp(`${temp.replace(/[\\^$.*+?()[\]{}|]/g, "\\$&")}:(\\d+)`, "g"),
        (_, lineNo) => `${fileLabel}:${Number(lineNo) + script.startLine - 1}`,
      );
      fail(`構文エラー\n${shifted.trim()}`);
    } finally {
      fs.rmSync(temp, { force: true });
    }
  });
}

/**
 * シード付きRNGを持つファイルでは Math.random() を禁止する。
 * 直接呼ぶと乱数列がシードから外れ、リプレイ・回帰テスト・ヘッドレス実行が壊れるため。
 * 例外的に使う行には `// allow-math-random` を付ける。
 */
function checkDeterministicRandom({ text, lines, fileLabel }, fail) {
  if (!text.includes("makeRandomGenerator")) return;   // RNG未導入のプロトは対象外
  const offenders = [];
  lines.forEach((line, index) => {
    if (line.includes("Math.random") && !line.includes("allow-math-random")) {
      offenders.push(`${fileLabel}:${index + 1}: ${line.trim().slice(0, 90)}`);
    }
  });
  if (offenders.length > 0) {
    fail(
      `Math.random() の直接呼び出しが ${offenders.length} 件。` +
      `ロジックは random()、演出は fxRandom() を使う。\n` + offenders.join("\n"),
    );
  }
}

/** 参照しているアセットが実在するか（生成漏れ・リネーム漏れの検出） */
function checkAssetsExist({ text, dir, fileLabel }, fail) {
  const referenced = new Set(
    [...text.matchAll(/["'`](assets\/[A-Za-z0-9_\-./]+\.(?:png|jpg|jpeg|webp|svg))["'`]/g)]
      .map((match) => match[1]),
  );
  const missing = [...referenced].filter((rel) => !fs.existsSync(path.join(dir, rel)));
  if (missing.length > 0) fail(`存在しないアセットを参照: ${missing.join(", ")} (${fileLabel})`);
}

/** バージョン表記があり vX.Y.Z 形式であること（deploy スキルがこれを読む） */
function checkVersion({ text, fileLabel }, fail) {
  const match = text.match(/const GAME_VERSION\s*=\s*"([^"]+)"/);
  if (!match) return;   // バージョンを持たないプロトは対象外
  if (!/^v\d+\.\d+\.\d+$/.test(match[1])) {
    fail(`GAME_VERSION の形式が不正: "${match[1]}" (${fileLabel})`);
  }
}

const CHECKS = [checkSyntax, checkDeterministicRandom, checkAssetsExist, checkVersion];

// -----------------------------------------------------------------
// 実行
// -----------------------------------------------------------------

function extractScripts(text) {
  const scripts = [];
  for (const match of text.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)) {
    scripts.push({
      code: match[1],
      startLine: text.slice(0, match.index).split("\n").length,   // <script> タグの行
    });
  }
  return scripts;
}

function checkFile(file) {
  const absolute = path.resolve(REPO_ROOT, file);
  const fileLabel = path.relative(REPO_ROOT, absolute).replace(/\\/g, "/");
  const text = fs.readFileSync(absolute, "utf8");
  const context = {
    text,
    lines: text.split("\n"),
    scripts: extractScripts(text),
    dir: path.dirname(absolute),
    fileLabel,
  };
  const failures = [];
  for (const check of CHECKS) check(context, (message) => failures.push(message));
  return { fileLabel, failures };
}

function targetsFromArgs(args) {
  const explicit = args.filter((a) => !a.startsWith("--"));
  if (explicit.length > 0) return explicit;
  return fs.readdirSync(path.join(REPO_ROOT, "prototypes"), { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => `prototypes/${entry.name}/index.html`)
    .filter((rel) => fs.existsSync(path.join(REPO_ROOT, rel)));
}

/** hook モード: stdin の JSON から編集対象を受け取り、prototypes 配下のときだけ検査する */
async function targetsFromHook() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  let payload = {};
  try { payload = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}"); } catch { /* 無視 */ }
  const edited = payload?.tool_input?.file_path;
  if (!edited) return [];
  const rel = path.relative(REPO_ROOT, path.resolve(edited)).replace(/\\/g, "/");
  return (rel.startsWith("prototypes/") && rel.endsWith(".html")) ? [rel] : [];
}

const args = process.argv.slice(2);
const isHook = args.includes("--hook");
const targets = isHook ? await targetsFromHook() : targetsFromArgs(args);

if (targets.length === 0) process.exit(0);

let failed = 0;
for (const target of targets) {
  const { fileLabel, failures } = checkFile(target);
  if (failures.length === 0) {
    if (!isHook) console.log(`OK   ${fileLabel}`);
  } else {
    failed += failures.length;
    console.error(`NG   ${fileLabel}`);
    for (const message of failures) console.error(`  - ${message}`);
  }
}

if (failed > 0) {
  console.error(`\ncheck 失敗: ${failed} 件。修正してから完了report すること。`);
  // hook では exit 2 が Claude へのブロッキング・フィードバックになる
  process.exit(isHook ? 2 : 1);
}
if (!isHook) console.log(`\ncheck 通過: ${targets.length} ファイル`);
