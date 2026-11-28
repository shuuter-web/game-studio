// Dragon Tide（DT-624）: 音のかけら（サンプル）を作って prototypes/dragon-tide/assets/audio/*.wav に書き出す。
//
//   node tools/gen_dt_samples.mjs
//
// なぜファイルにするか：16ビット機の本当の音源は「短い録音（サンプル）を鳴らす」方式で、楽器らしさはその場で波形を作るより
// サンプルの方がずっと出る（DT-624 で Shooter と合意）。ゲームはこのかけらを高さを変えて鳴らすだけ（小さなトラッカー）。
// いまのかけらはこのスクリプトで合成したもの。後で録音や生成した音に差し替えるときは、同じ名前・同じ基準の高さ（INSTRUMENTS の base）で置けばよい。
// 低い質で作る（22050Hz・16bit・モノラル。パッドとホーンは 16000Hz）：16ビット機らしいこもりになり、ファイルも小さい。
// 乱数は自前の決まった列（毎回同じファイルになる。ゲームの乱数には触らない）。
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const OUT = join(dirname(fileURLToPath(import.meta.url)), "..", "prototypes", "dragon-tide", "assets", "audio");
const TAU = Math.PI * 2;
const midiHz = (m) => 440 * Math.pow(2, (m - 69) / 12);

function makeRandom(seed) {   // mulberry32
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function writeWav(name, rate, samples, peak = 0.89) {
  let max = 0;
  for (const v of samples) max = Math.max(max, Math.abs(v));
  const scale = max > 0 ? peak / max : 1;   // かけらごとに大きさをそろえる（鳴らす大きさは music.json の gain で決める）
  const n = samples.length;
  const buf = Buffer.alloc(44 + n * 2);
  buf.write("RIFF", 0); buf.writeUInt32LE(36 + n * 2, 4); buf.write("WAVE", 8);
  buf.write("fmt ", 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(1, 22);
  buf.writeUInt32LE(rate, 24); buf.writeUInt32LE(rate * 2, 28); buf.writeUInt16LE(2, 32); buf.writeUInt16LE(16, 34);
  buf.write("data", 36); buf.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) buf.writeInt16LE(Math.max(-32767, Math.min(32767, Math.round(samples[i] * scale * 32767))), 44 + i * 2);
  writeFileSync(join(OUT, name), buf);
  return buf.length;
}

/** 始めと終わりを短く丸めて、ぷつっと鳴らないようにする */
function fadeEdges(s, rate, inSec = 0.002, outSec = 0.02) {
  const a = Math.floor(rate * inSec), b = Math.floor(rate * outSec);
  for (let i = 0; i < a && i < s.length; i++) s[i] *= i / a;
  for (let i = 0; i < b && i < s.length; i++) s[s.length - 1 - i] *= i / b;
  return s;
}
function onePoleLow(s, rate, hz) {
  const k = 1 - Math.exp(-TAU * hz / rate);
  let y = 0;
  for (let i = 0; i < s.length; i++) { y += k * (s[i] - y); s[i] = y; }
  return s;
}

// --- 楽器 ---
/** ハープ：はじいた弦（Karplus-Strong）。線を引く間の駆け上がりと、薙ぎの和音 */
function harp(rate, midi, sec) {
  const rnd = makeRandom(11);
  const period = rate / midiHz(midi);
  const len = Math.floor(rate * sec);
  const out = new Float32Array(len);
  const n = Math.round(period);
  const ring = new Float32Array(n);
  for (let i = 0; i < n; i++) ring[i] = rnd() * 2 - 1;
  onePoleLow(ring, rate, 3000);
  let idx = 0;
  for (let i = 0; i < len; i++) {
    const next = (idx + 1) % n;
    const v = ring[idx];
    ring[idx] = (v + ring[next]) * 0.5 * 0.9975;
    out[i] = v;
    idx = next;
  }
  for (let i = 0; i < len; i++) out[i] += 0.25 * Math.sin(TAU * midiHz(midi) * i / rate) * Math.exp(-i / rate * 2.2);   // 胴の鳴り
  return fadeEdges(out, rate, 0.001, 0.1);
}
/** マリンバ：木の板。建物の崩壊が拍に乗るアルペジオになる */
function marimba(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  const rnd = makeRandom(23);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    out[i] = Math.sin(TAU * f * t) * Math.exp(-t * 5.5)
           + 0.35 * Math.sin(TAU * f * 3.93 * t) * Math.exp(-t * 22)
           + 0.12 * Math.sin(TAU * f * 9.2 * t) * Math.exp(-t * 60)
           + (t < 0.006 ? (rnd() * 2 - 1) * 0.5 * (1 - t / 0.006) : 0);   // 叩いた「こつ」
  }
  return fadeEdges(out, rate, 0.0005, 0.05);
}
/** オルゴール（金属の櫛）：卵の音階・強化のチャイム */
function musicBox(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    out[i] = Math.sin(TAU * f * t) * Math.exp(-t * 2.6)
           + 0.22 * Math.sin(TAU * f * 2 * t) * Math.exp(-t * 4.5)
           + 0.16 * Math.sin(TAU * f * 5.03 * t) * Math.exp(-t * 14)
           + 0.08 * Math.sin(TAU * f * 8.7 * t) * Math.exp(-t * 30);
  }
  return fadeEdges(out, rate, 0.0008, 0.08);
}
/** 鐘：警戒度が上がった・町の陥落 */
function bell(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  const partials = [[0.5, 1.0, 0.9], [1, 1.0, 1.4], [1.19, 0.5, 1.8], [1.56, 0.45, 2.4], [2.0, 0.4, 2.0], [2.74, 0.3, 3.6], [3.76, 0.18, 5], [5.4, 0.1, 7]];
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (const [ratio, amp, decay] of partials) v += amp * Math.sin(TAU * f * ratio * t) * Math.exp(-t * decay);
    out[i] = v;
  }
  return fadeEdges(out, rate, 0.001, 0.2);
}
const PAD_HARMONICS = 10;   // 基準 48（131Hz）を1オクターブ上げても 2.6kHz まで（22050Hz の半分より十分下）
/** パッド：少しずらした鋸波3本をこもらせた帯（首都の陥落の和音に使う） */
function pad(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  const detune = [-0.0045, 0, 0.0052];
  const phase = [0, 0.33, 0.71];
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    // v3.246.0（DT-624 手直し9・11/27 Shooter「どの地域でも常に鳴ってる歪んだ音のシンセ音」）: 素の鋸波は標本化の半分より上の倍音が
    // 折り返して、高さを上げて鳴らすほどざらついた歪みに聞こえた。倍音を数えて足す鋸波（sawH）にし、上の倍音も少なくする
    for (let k = 0; k < 3; k++) v += sawH((f * (1 + detune[k]) * t + phase[k]) % 1, PAD_HARMONICS) * 0.6;
    out[i] = v / 3 * (1 + 0.06 * Math.sin(TAU * 0.7 * t));
  }
  onePoleLow(out, rate, 1400); onePoleLow(out, rate, 2200);
  return fadeEdges(out, rate, 0.01, 0.3);
}
/** ベース：はじいた低い弦 */
function bass(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (let h = 1; h <= 8; h++) v += Math.sin(TAU * f * h * t) / h * Math.exp(-t * (1.5 + h * 1.2));
    out[i] = v;
  }
  return fadeEdges(out, rate, 0.002, 0.05);
}
/** 角笛（ホーン）：竜の主題を吹く。息を吹き込むと明るくなり、伸ばすと少し揺れる */
function horn(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  let phase = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const vib = t > 0.25 ? 0.0045 * Math.min(1, (t - 0.25) * 3) * Math.sin(TAU * 5.2 * t) : 0;
    phase += f * (1 + vib) / rate;
    const bright = 0.35 + 0.65 * Math.min(1, t / 0.06) * (0.75 + 0.25 * Math.exp(-t * 3));
    let v = 0;
    for (let h = 1; h <= 10; h++) v += Math.sin(TAU * phase * h) * Math.pow(bright, h - 1) / h;
    out[i] = v * Math.min(1, t / 0.03);
  }
  onePoleLow(out, rate, 3200);
  return fadeEdges(out, rate, 0.005, 0.15);
}
// 打楽器
function kick(rate) {
  const len = Math.floor(rate * 0.4), out = new Float32Array(len);
  let phase = 0;
  for (let i = 0; i < len; i++) { const t = i / rate; phase += (48 + 90 * Math.exp(-t * 30)) / rate; out[i] = Math.sin(TAU * phase) * Math.exp(-t * 9); }
  return fadeEdges(out, rate, 0.0005, 0.03);
}
function tom(rate) {   // 崩壊の「どん」。高さは今の和音の根音に合わせて変えて鳴らす（基準 MIDI 45）
  const rnd = makeRandom(31);
  const len = Math.floor(rate * 0.5), out = new Float32Array(len);
  let phase = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate; phase += midiHz(45) * (1 + 0.5 * Math.exp(-t * 25)) / rate;
    out[i] = Math.sin(TAU * phase) * Math.exp(-t * 7) + (rnd() * 2 - 1) * 0.3 * Math.exp(-t * 30);
  }
  return fadeEdges(onePoleLow(out, rate, 1800), rate, 0.0005, 0.04);
}
function noiseHit(rate, sec, seed, lowHz, highHz, decay, tone = null) {
  const rnd = makeRandom(seed);
  const len = Math.floor(rate * sec), out = new Float32Array(len);
  let lp = 0, prev = 0;
  const kl = 1 - Math.exp(-TAU * lowHz / rate);
  const kh = 1 - Math.exp(-TAU * highHz / rate);
  let hp = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const n = rnd() * 2 - 1;
    lp += kh * (n - lp);                   // 上を切る
    hp += kl * (lp - hp);                  // 下を切る（lp - hp が帯）
    let v = (lp - hp) * Math.exp(-t * decay);
    if (tone) v += tone[1] * Math.sin(TAU * tone[0] * t) * Math.exp(-t * tone[2]);
    out[i] = v; prev = v;
  }
  return fadeEdges(out, rate, 0.0005, 0.03);
}

// --- DT-624 手直し3：ジャズ・フュージョン・ソウルの曲のための楽器 ---
/** エレピ（電気ピアノ）：FM（変調の深さが減っていく）＋叩いた瞬間の金属の「きん」。和音の刻み */
function epiano(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const index = 1.6 * Math.exp(-t * 6) + 0.25;
    const mod = Math.sin(TAU * f * t) * index;
    out[i] = Math.sin(TAU * f * t + mod) * Math.exp(-t * 1.6) * (1 + 0.08 * Math.sin(TAU * 4.5 * t))
           + 0.28 * Math.sin(TAU * f * 14 * t) * Math.exp(-t * 45);
  }
  onePoleLow(out, rate, 4200);
  return fadeEdges(out, rate, 0.001, 0.15);
}
/** オルガン：引き出し（倍音）を重ね、ゆっくり揺らす（回るスピーカーの揺れ）。伸ばして和音の床 */
function organ(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  const bars = [[0.5, 0.5], [1, 1], [1.5, 0.45], [2, 0.6], [3, 0.3], [4, 0.25]];
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const trem = 1 + 0.12 * Math.sin(TAU * 6.3 * t);
    let v = 0;
    for (const [ratio, amp] of bars) v += amp * Math.sin(TAU * f * ratio * t + 0.4 * Math.sin(TAU * 6.3 * t) * ratio * 0.05);
    out[i] = v * trem + (t < 0.012 ? 0.3 * Math.sin(TAU * f * 6 * t) * (1 - t / 0.012) : 0);   // 鍵の「かち」
  }
  onePoleLow(out, rate, 3600);
  return fadeEdges(out, rate, 0.004, 0.1);
}
/** ウッドベース：はじいた低い弦（Karplus-Strong）に胴の「ぼん」を足す。歩くベース */
function upright(rate, midi, sec) {
  const rnd = makeRandom(61);
  const f = midiHz(midi), n = Math.round(rate / f), len = Math.floor(rate * sec);
  const ring = new Float32Array(n), out = new Float32Array(len);
  for (let i = 0; i < n; i++) ring[i] = rnd() * 2 - 1;
  onePoleLow(ring, rate, 700);
  let idx = 0;
  for (let i = 0; i < len; i++) {
    const next = (idx + 1) % n, v = ring[idx];
    ring[idx] = (v + ring[next]) * 0.5 * 0.996;
    const t = i / rate;
    out[i] = v * 0.8 + 0.9 * Math.sin(TAU * f * t) * Math.exp(-t * 3.2);
    idx = next;
  }
  onePoleLow(out, rate, 1600);
  return fadeEdges(out, rate, 0.002, 0.08);
}
/** クラビネット：細い矩形波を弾いた明るく短い音。ソウル・ファンクの刻み */
function clav(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  for (let i = 0; i < len; i++) {
    const t = i / rate, p = (f * t) % 1;
    const pulse = p < 0.22 ? 1 : -0.28;
    out[i] = pulse * Math.exp(-t * 7);
  }
  // 弾いた瞬間だけ明るく、すぐこもる
  const k0 = 1 - Math.exp(-TAU * 5000 / rate);
  let y = 0;
  for (let i = 0; i < len; i++) { const t = i / rate; const k = k0 * (0.25 + 0.75 * Math.exp(-t * 18)); y += k * (out[i] - y); out[i] = y; }
  return fadeEdges(out, rate, 0.0008, 0.05);
}
/** 金管の重奏（ブラスの一撃）：少しずらした鋸波2本に、吹いた瞬間に開く明るさ。ソウルの合いの手 */
function brass(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  const detune = [-0.006, 0.006];
  let y = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (const d of detune) { const p = (f * (1 + d) * t) % 1; v += p * 2 - 1; }
    const cutoff = 900 + 3200 * Math.min(1, t / 0.05) * (0.55 + 0.45 * Math.exp(-t * 6));
    const k = 1 - Math.exp(-TAU * cutoff / rate);
    y += k * (v * 0.5 - y);
    out[i] = y * Math.min(1, t / 0.02);
  }
  return fadeEdges(out, rate, 0.004, 0.12);
}
/** ライド（シンバル）：金属の倍音の束とノイズ。ジャズの刻み */
function ride(rate) {
  const rnd = makeRandom(71);
  const len = Math.floor(rate * 1.1), out = new Float32Array(len);
  const partials = [3170, 4120, 5230, 6370, 7410, 8730];
  let hp = 0, lp = 0;
  const kh = 1 - Math.exp(-TAU * 9000 / rate), kl = 1 - Math.exp(-TAU * 4000 / rate);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (let k = 0; k < partials.length; k++) v += Math.sign(Math.sin(TAU * partials[k] * t + k)) * 0.12;
    const n = rnd() * 2 - 1;
    lp += kh * (n - lp); hp += kl * (lp - hp);
    out[i] = (v * 0.5 + (lp - hp) * 1.2) * (Math.exp(-t * 3.2) * 0.7 + Math.exp(-t * 40) * 0.6);
  }
  return fadeEdges(out, rate, 0.0005, 0.1);
}
/** リム（スティックで縁を打つ「こっ」） */
function rim(rate) {
  const len = Math.floor(rate * 0.09), out = new Float32Array(len);
  const rnd = makeRandom(73);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    out[i] = Math.sin(TAU * 1750 * t) * Math.exp(-t * 70) + 0.6 * Math.sin(TAU * 520 * t) * Math.exp(-t * 55) + (rnd() * 2 - 1) * 0.4 * Math.exp(-t * 120);
  }
  return fadeEdges(out, rate, 0.0003, 0.02);
}
/** 手拍子：少しずつずれた数人ぶんのノイズの束 */
function clap(rate) {
  const rnd = makeRandom(79);
  const len = Math.floor(rate * 0.3), out = new Float32Array(len);
  const hits = [0, 0.009, 0.019, 0.027];
  let lp = 0, hp = 0;
  const kh = 1 - Math.exp(-TAU * 3200 / rate), kl = 1 - Math.exp(-TAU * 800 / rate);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let env = 0;
    for (const h of hits) if (t >= h) env = Math.max(env, Math.exp(-(t - h) * (h === hits[hits.length - 1] ? 22 : 140)));
    const n = rnd() * 2 - 1;
    lp += kh * (n - lp); hp += kl * (lp - hp);
    out[i] = (lp - hp) * env;
  }
  return fadeEdges(out, rate, 0.0003, 0.03);
}
/** ブラシ（スネアを擦る「さー」）：ゆっくり立ち上がって消えるノイズ */
function brush(rate) {
  const rnd = makeRandom(83);
  const len = Math.floor(rate * 0.35), out = new Float32Array(len);
  let lp = 0, hp = 0;
  const kh = 1 - Math.exp(-TAU * 6000 / rate), kl = 1 - Math.exp(-TAU * 1500 / rate);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const n = rnd() * 2 - 1;
    lp += kh * (n - lp); hp += kl * (lp - hp);
    out[i] = (lp - hp) * Math.min(1, t / 0.06) * Math.exp(-t * 7);
  }
  return fadeEdges(out, rate, 0.002, 0.04);
}

// --- DT-624 手直し4（エレクトロニカ・11/26 Shooter「音色を現代的なかっこいいエレクトロニカに」）---
/** のこぎり波（帯域を少し丸めた近似。高い倍音でざらつかないよう倍音を数で打ち切る） */
function sawH(phase, maxH) { let v = 0; for (let h = 1; h <= maxH; h++) v += Math.sin(TAU * phase * h) / h; return v; }
/** スーパーソウ：7本の少しずつずらしたのこぎり波を重ねた厚いパッド */
function synpad(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  const det = [-0.011, -0.0065, -0.003, 0, 0.0032, 0.0068, 0.0105], ph = [0, 0.13, 0.41, 0.77, 0.29, 0.58, 0.91];
  const maxH = Math.max(1, Math.floor(rate / 2 / (f * 1.02)) - 1);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (let k = 0; k < 7; k++) v += sawH(f * (1 + det[k]) * t + ph[k], Math.min(maxH, 24)) * (k === 3 ? 1 : 0.7);
    out[i] = v / 5;
  }
  onePoleLow(out, rate, 3600);
  return fadeEdges(out, rate, 0.02, 0.4);
}
/** プラック：明るく弾いてすぐ暗くなるシンセ（倍音ほど早く消える＝フィルターが閉じる感じ） */
function pluck(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  const maxH = Math.min(30, Math.floor(rate / 2 / f) - 1);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (let h = 1; h <= maxH; h++) v += Math.sin(TAU * f * h * t + (h % 2) * 0.3) / h * Math.exp(-t * (3 + h * 2.2));
    v += 0.35 * Math.sin(TAU * f * 1.004 * t) * Math.exp(-t * 4);
    out[i] = v;
  }
  return fadeEdges(out, rate, 0.001, 0.05);
}
/** サブベース：低い正弦にうすいのこぎりの歪みを足した太いベース */
function subbass(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const v = Math.sin(TAU * f * t) + 0.28 * sawH(f * t, 6) * Math.exp(-t * 3);
    out[i] = Math.tanh(v * 1.6) * Math.min(1, t / 0.004);
  }
  return fadeEdges(out, rate, 0.002, 0.06);
}
/** 電子のキック：深く下がる正弦と短いクリック */
function kick808(rate) {
  const len = Math.floor(rate * 0.55), out = new Float32Array(len);
  let phase = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    phase += (46 + 140 * Math.exp(-t * 38)) / rate;
    out[i] = Math.tanh(1.8 * Math.sin(TAU * phase) * Math.exp(-t * 6.5)) + (t < 0.004 ? (1 - t / 0.004) * 0.6 : 0);
  }
  return fadeEdges(out, rate, 0.0003, 0.04);
}
/** 電子のハイハット：高い矩形波を何本か重ねた金属の音（808 の作り方） */
function ehat(rate) {
  const len = Math.floor(rate * 0.07), out = new Float32Array(len);
  const fr = [3140, 4170, 5220, 6010, 7330, 8150];
  let prev = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (const q of fr) v += ((q * t) % 1) < 0.5 ? 1 : -1;
    const hp = v - prev; prev = v;   // 低い所を削る
    out[i] = hp * Math.exp(-t * 70);
  }
  return fadeEdges(out, rate, 0.0002, 0.01);
}
/** リード：細いのこぎり2本＋ビブラート。角笛のかわりに竜の主題を吹く */
function lead(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  let p1 = 0, p2 = 0;
  const maxH = Math.min(18, Math.floor(rate / 2 / f) - 1);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const vib = t > 0.2 ? 0.006 * Math.min(1, (t - 0.2) * 3) * Math.sin(TAU * 5.6 * t) : 0;
    p1 += f * (1 + vib) / rate; p2 += f * (1.006 + vib) / rate;
    out[i] = (sawH(p1, maxH) + sawH(p2, maxH)) * 0.5 * Math.min(1, t / 0.01);
  }
  onePoleLow(out, rate, 4200);
  return fadeEdges(out, rate, 0.003, 0.12);
}
/** FMベル：きらっとした金属の鈴（合いの手） */
function fmbell(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const idx = 3.2 * Math.exp(-t * 5);
    out[i] = Math.sin(TAU * f * t + idx * Math.sin(TAU * f * 3.5 * t)) * Math.exp(-t * 3.2);
  }
  return fadeEdges(out, rate, 0.001, 0.08);
}

// --- DT-624 手直し5：時代ごとの「文明の音楽」の楽器（竜の主題との綱引きの、町の側） ---
/** 皮の太鼓：低い胴の鳴りと、手で張った皮をたたく「ぱん」（石器時代・古代の枠太鼓は高さを上げて使う） */
function skinDrum(rate) {
  const rnd = makeRandom(61);
  const len = Math.floor(rate * 0.6), out = new Float32Array(len);
  let phase = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate; phase += midiHz(43) * (1 + 0.25 * Math.exp(-t * 18)) / rate;
    out[i] = Math.sin(TAU * phase) * Math.exp(-t * 6) + 0.45 * Math.sin(TAU * phase * 1.59) * Math.exp(-t * 14) + (rnd() * 2 - 1) * 0.5 * Math.exp(-t * 45);
  }
  return fadeEdges(onePoleLow(out, rate, 1400), rate, 0.0005, 0.05);
}
/** 骨の笛：息のまじった柔らかい笛（基音が強く、息のノイズが乗る） */
function flute(rate, midi, sec) {
  const rnd = makeRandom(67);
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  let phase = 0, breath = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const vib = t > 0.3 ? 0.005 * Math.min(1, (t - 0.3) * 2) * Math.sin(TAU * 4.6 * t) : 0;
    phase += f * (1 + vib) / rate;
    breath += 0.08 * ((rnd() * 2 - 1) - breath);
    const env = Math.min(1, t / 0.07);
    out[i] = (Math.sin(TAU * phase) + 0.18 * Math.sin(TAU * phase * 2) + 0.06 * Math.sin(TAU * phase * 3) + breath * 1.4 * (0.6 + 0.4 * Math.exp(-t * 6))) * env;
  }
  onePoleLow(out, rate, 3600);
  return fadeEdges(out, rate, 0.01, 0.15);
}
/** 合唱：「あー」の声。のこぎり波を数本ずらして、母音の山（フォルマント）だけを残す */
function choir(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), raw = new Float32Array(len);
  const detune = [0.994, 1, 1.006, 1.011];
  const ph = detune.map(() => 0);
  const maxH = Math.min(24, Math.floor(rate / 2 / f / 1.02) - 1);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    detune.forEach((d, k) => { ph[k] += f * d * (1 + 0.004 * Math.sin(TAU * (4.8 + k * 0.4) * t + k)) / rate; v += sawH(ph[k], maxH); });
    raw[i] = v * Math.min(1, t / 0.18);
  }
  // 「あ」の母音の山（約 750Hz・1200Hz）を2つの帯で取り出して足す
  const out = new Float32Array(len);
  for (const [hz, q, amp] of [[750, 6, 1], [1200, 7, 0.6], [2600, 8, 0.2]]) {
    const w = TAU * hz / rate, alpha = Math.sin(w) / (2 * q), cw = Math.cos(w);
    const b0 = alpha, b2 = -alpha, a0 = 1 + alpha, a1 = -2 * cw, a2 = 1 - alpha;
    let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
    for (let i = 0; i < len; i++) {
      const x = raw[i];
      const y = (b0 * x + b2 * x2 - a1 * y1 - a2 * y2) / a0;
      x2 = x1; x1 = x; y2 = y1; y1 = y;
      out[i] += y * amp;
    }
  }
  return fadeEdges(out, rate, 0.02, 0.3);
}
/** リュート：はじいた弦を明るく短く（ハープより鼻にかかった音・早く消える） */
function lute(rate, midi, sec) {
  const rnd = makeRandom(71);
  const period = rate / midiHz(midi);
  const len = Math.floor(rate * sec), out = new Float32Array(len);
  const n = Math.round(period), ring = new Float32Array(n);
  for (let i = 0; i < n; i++) ring[i] = (rnd() * 2 - 1) * (i < n * 0.3 ? 1 : 0.3);   // 弦の端近くをはじく＝倍音が多い
  let idx = 0;
  for (let i = 0; i < len; i++) {
    const next = (idx + 1) % n, v = ring[idx];
    ring[idx] = (v + ring[next]) * 0.5 * 0.993;
    out[i] = v; idx = next;
  }
  // 胴の共鳴（中音の山）で鼻にかける
  for (let i = 2; i < len; i++) out[i] += 0.35 * (out[i] - out[i - 2]);
  return fadeEdges(onePoleLow(out, rate, 4200), rate, 0.001, 0.08);
}
/** 金床：かーん、と高く長く残る金属（倍音が整数でない） */
function anvil(rate) {
  const len = Math.floor(rate * 1.2), out = new Float32Array(len);
  const parts = [[1, 1, 2.2], [2.76, 0.6, 3.5], [5.4, 0.35, 5], [8.9, 0.2, 8]];
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (const [m, a, d] of parts) v += a * Math.sin(TAU * midiHz(72) * m * t) * Math.exp(-t * d);
    out[i] = v * Math.min(1, t / 0.0008);
  }
  return fadeEdges(out, rate, 0.0005, 0.1);
}
/** アコーディオン：リードのこすれる音（細い矩形を2枚少しずらし、ゆっくり揺らす） */
function accordion(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  const maxH = Math.min(16, Math.floor(rate / 2 / f / 1.01) - 1);
  let p1 = 0, p2 = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    p1 += f / rate; p2 += f * 1.007 / rate;
    let v = 0;
    for (let h = 1; h <= maxH; h++) { const a = Math.sin(Math.PI * h * 0.3) / h; v += a * (Math.sin(TAU * p1 * h) + Math.sin(TAU * p2 * h)); }
    out[i] = v * Math.min(1, t / 0.04) * (0.9 + 0.1 * Math.sin(TAU * 5 * t));
  }
  onePoleLow(out, rate, 3800);
  return fadeEdges(out, rate, 0.005, 0.1);
}
/** テルミン：揺れの大きい澄んだ正弦波（電気時代の、はじめての電子の声） */
function theremin(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  let phase = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const vib = 0.012 * Math.min(1, t * 1.5) * Math.sin(TAU * 6.2 * t);
    phase += f * (1 + vib) / rate;
    out[i] = (Math.sin(TAU * phase) + 0.12 * Math.sin(TAU * phase * 2)) * Math.min(1, t / 0.12);
  }
  return fadeEdges(out, rate, 0.01, 0.2);
}
/** 銅鑼：低いうなりが後から膨らんで長く残る（最終王朝の宮廷） */
function gong(rate) {
  const rnd = makeRandom(79);
  const len = Math.floor(rate * 3.0), out = new Float32Array(len);
  const parts = [[1, 1, 0.9], [1.48, 0.7, 1.2], [2.1, 0.5, 1.6], [2.9, 0.35, 2.2], [3.7, 0.25, 3]];
  let nz = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (const [m, a, d] of parts) v += a * Math.sin(TAU * midiHz(38) * m * t * (1 + 0.002 * Math.sin(TAU * 0.7 * t))) * Math.exp(-t * d);
    nz += 0.2 * ((rnd() * 2 - 1) - nz);
    out[i] = v * (0.6 + 0.4 * Math.min(1, t / 0.35)) + nz * 0.25 * Math.exp(-t * 2.5);
  }
  return fadeEdges(onePoleLow(out, rate, 2600), rate, 0.002, 0.3);
}

// --- DT-624 手直し8（11/27・地域ごとの曲をゼロから作り直し、攻略が進むほど楽団が増える）---
/** 弦の合奏：少しずつずらしたのこぎり波5本に、ゆっくりした揺れ。パッドより明るく、刻み（壊している間のパート）にも使える */
function strings(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  const detune = [-0.006, -0.0025, 0, 0.003, 0.0065];
  const phase = [0.1, 0.43, 0.77, 0.21, 0.58];
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const vib = 1 + 0.0035 * Math.sin(TAU * 5.4 * t) * Math.min(1, t * 2);
    let v = 0;
    for (let k = 0; k < 5; k++) v += sawH((f * (1 + detune[k]) * vib * t + phase[k]) % 1, 12);
    out[i] = v / 5 * Math.min(1, t / 0.05);
  }
  onePoleLow(out, rate, 3600); onePoleLow(out, rate, 5200);
  return fadeEdges(out, rate, 0.004, 0.3);
}
/** ティンパニ：張った皮の大太鼓。高さを和音の根音に合わせて鳴らす（基準 MIDI 41） */
function timpani(rate) {
  const rnd = makeRandom(61);
  const f = midiHz(41), len = Math.floor(rate * 1.6), out = new Float32Array(len);
  const modes = [[1, 1.0, 2.2], [1.5, 0.45, 3.0], [1.98, 0.3, 4.0], [2.44, 0.15, 5.0]];
  let nz = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (const [m, a, d] of modes) v += a * Math.sin(TAU * f * m * t * (1 + 0.02 * Math.exp(-t * 20))) * Math.exp(-t * d);
    nz += 0.3 * ((rnd() * 2 - 1) - nz);
    out[i] = v + nz * 0.5 * Math.exp(-t * 40);
  }
  return fadeEdges(onePoleLow(out, rate, 2400), rate, 0.0005, 0.2);
}
/** 和太鼓：低く太い一打（胴鳴りが長い） */
function taiko(rate) {
  const rnd = makeRandom(67);
  const len = Math.floor(rate * 0.9), out = new Float32Array(len);
  let phase = 0, nz = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    phase += (62 + 70 * Math.exp(-t * 18)) / rate;
    nz += 0.25 * ((rnd() * 2 - 1) - nz);
    out[i] = Math.sin(TAU * phase) * Math.exp(-t * 4.5) + nz * 0.6 * Math.exp(-t * 28);
  }
  return fadeEdges(onePoleLow(out, rate, 1500), rate, 0.0005, 0.08);
}
/** 崩れる音（建物の崩壊の効果音。曲には組み込まない）：低い「どさっ」と、砕けた石がばらばら落ちる粒 */
function crumble(rate) {
  const rnd = makeRandom(71);
  const len = Math.floor(rate * 0.7), out = new Float32Array(len);
  let phase = 0, lp = 0, lp2 = 0;
  const grains = [];
  for (let k = 0; k < 18; k++) grains.push([0.03 + rnd() * 0.45, 0.25 + rnd() * 0.75]);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    phase += (55 + 40 * Math.exp(-t * 25)) / rate;
    const n = rnd() * 2 - 1;
    lp += 0.35 * (n - lp); lp2 += 0.06 * (n - lp2);
    let v = Math.sin(TAU * phase) * 0.9 * Math.exp(-t * 11) + lp2 * 2.2 * Math.exp(-t * 6);
    for (const [at, a] of grains) { const dt = t - at; if (dt > 0 && dt < 0.03) v += lp * a * Math.exp(-dt * 160); }
    out[i] = v;
  }
  return fadeEdges(onePoleLow(out, rate, 3200), rate, 0.0005, 0.1);
}

// --- DT-624 手直し11（11/28 Shooter「建物が壊れる音が雑音ノイズみたいで気持ち良く無い。一番大事な音なのでちゃんと気持ちいい音に。
//     建物の大きさや種類ごとに差をつけつつ」）---
// 前の crumble は「低い正弦の どさっ」＋「ろ過した白い雑音」で、雑音の比が大きくシャーという砂嵐に聞こえた。
// 雑音を音の芯に使うのをやめ、叩かれた物の鳴り（モード合成：減衰する正弦をいくつか重ねる＝木・石・金属の固有の響き）で組む。
//   1. 割れ（0秒）：材質の固有の響きを強く短く。歯切れの「パキッ／ガッ」
//   2. 胴（0秒〜）：高さが下がっていく低い正弦の「ドン」。大きい建物ほど低く長い＝重さ
//   3. 崩れ（大きい建物だけ）：少し遅れて2〜3回、低めの響きで「ガラガラッ」と構造が落ちる
//   4. 破片：材質の響きを高くした小さな粒を、跳ねて落ち着くように間隔を空けながら並べる（雑音でなく粒の音の連なり）
// 材質は木（石器時代の小屋）・石（古代〜近世・城壁・首都）・金属（産業時代〜）。大きさは小（tiny・small）と大（medium・large・首都）。
// 全部の粒を tanh で軽く飽和させて、音量を上げずに芯を太くする。
const SMASH_MATERIALS = {
  // 割れの響き：[Hz, 減り方（1秒あたり）, 大きさ]。木＝こもった低めの「コッ」、石＝硬く詰まった「ガッ」、金属＝長く残る非整数倍の「カーン」
  wood:  { modes: [[260, 26, 1], [520, 34, 0.8], [830, 48, 0.45], [1390, 70, 0.28]], debrisScale: [1.6, 3.2], debrisDecay: 1.6, bodyHz: 1 },
  stone: { modes: [[250, 40, 0.9], [610, 55, 0.7], [1180, 80, 0.5], [2150, 110, 0.32], [3300, 150, 0.18]], debrisScale: [1.3, 2.6], debrisDecay: 2.2, bodyHz: 0.85 },
  metal: { modes: [[290, 7, 0.5], [781, 8, 0.45], [1270, 10, 0.4], [1935, 13, 0.3], [2890, 17, 0.2]], debrisScale: [1.2, 2.4], debrisDecay: 2.6, bodyHz: 0.9 },
};
const SMASH_SIZES = {
  //  len＝長さ（秒）、bodyHz＝胴の高さ、bodyDecay＝胴の減り、bodyGain、breaks＝崩れの時刻、debris＝破片の数、debrisSpan＝破片が続く秒数
  s: { len: 0.6, bodyHz: 130, bodyDecay: 14, bodyGain: 0.4, crackGain: 1.0, breaks: [], debris: 9, debrisSpan: 0.32, rumble: 0 },
  l: { len: 1.4, bodyHz: 68, bodyDecay: 4.5, bodyGain: 0.5, crackGain: 1.0, breaks: [0.07, 0.16, 0.27], debris: 26, debrisSpan: 0.95, rumble: 0.08 },
};
function addModes(out, rate, at, amp, modes, scale, decayMul) {
  const i0 = Math.floor(at * rate);
  for (const [hz, dec, g] of modes) {
    const f = hz * scale, d = dec * decayMul;
    if (f > rate * 0.45) continue;
    const n = Math.min(out.length - i0, Math.floor(rate * Math.min(2.5, 7 / d)));
    for (let i = 0; i < n; i++) {
      const t = i / rate;
      // 立ち上がり 1ms（クリックにしない）
      out[i0 + i] += amp * g * Math.min(1, t / 0.001) * Math.exp(-t * d) * Math.sin(TAU * f * t);
    }
  }
}
function smash(rate, material, size, seed) {
  const m = SMASH_MATERIALS[material], z = SMASH_SIZES[size];
  const rnd = makeRandom(seed);
  const len = Math.floor(rate * z.len), out = new Float32Array(len);
  // 1. 割れ
  addModes(out, rate, 0, z.crackGain, m.modes, size === "l" ? 0.85 : 1.15, 1);
  // ほんの短い硬い当たり（2ms の帯域の狭い粒。雑音でなく高い響きの頭）
  addModes(out, rate, 0, 0.5, [[2600, 900, 1], [3900, 1200, 0.6]], 1, 1);
  // 2. 胴
  let phase = 0;
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    phase += (z.bodyHz * m.bodyHz * (1 + 1.2 * Math.exp(-t * 30))) / rate;
    // 2倍・3倍の音も足す：スマホのスピーカーは 200Hz より下がほとんど出ないので、低い基音が聞こえなくても倍音で「ドン」が分かるように
    out[i] += z.bodyGain * Math.min(1, t / 0.002) * Math.exp(-t * z.bodyDecay) *
              (Math.sin(TAU * phase) + 0.7 * Math.sin(TAU * phase * 2) * Math.exp(-t * 6) + 0.35 * Math.sin(TAU * phase * 3) * Math.exp(-t * 10));
  }
  // 3. 崩れ
  z.breaks.forEach((at, k) => addModes(out, rate, at + rnd() * 0.02, 0.75 - k * 0.15, m.modes, 0.7 + rnd() * 0.2, 0.8));
  // 大きい建物の地鳴り：低い正弦の重なり（雑音を使わない）
  if (z.rumble > 0) {
    for (let i = 0; i < len; i++) {
      const t = i / rate;
      const env = Math.min(1, t / 0.08) * Math.exp(-t * 2.6);
      out[i] += z.rumble * env * (Math.sin(TAU * 43 * t) + 0.6 * Math.sin(TAU * 61 * t + 1.3) + 0.4 * Math.sin(TAU * 89 * t + 0.4));
    }
  }
  // 4. 破片：はじめは詰んで、だんだん間遠に（跳ねて落ち着く）。小さい欠片ほど高い
  for (let k = 0; k < z.debris; k++) {
    const u = (k + rnd() * 0.8) / z.debris;
    const at = 0.025 + z.debrisSpan * Math.pow(u, 1.5);
    const sc = m.debrisScale[0] + rnd() * (m.debrisScale[1] - m.debrisScale[0]);
    const amp = 0.42 * Math.pow(1 - u, 1.2) * (0.6 + rnd() * 0.4);
    addModes(out, rate, at, amp, m.modes.slice(1, 4), sc, m.debrisDecay);
  }
  for (let i = 0; i < len; i++) out[i] = Math.tanh(out[i] * 1.4);
  return fadeEdges(onePoleLow(out, rate, 7000), rate, 0.0005, size === "l" ? 0.15 : 0.08);
}

// --- DT-624 手直し9（11/27・主旋律を常に鳴らさない・伴奏は単音で目立たせずに和音の分かる線）---
/** 柔らかい鍵盤（和音の線）：正弦の基音にわずかな2倍・3倍音。立ち上がりを丸め、ゆっくり減る。目立たずに和音の音を1つずつたどる */
function warm(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    const env = Math.min(1, t / 0.02) * (0.55 * Math.exp(-t * 2.2) + 0.45 * Math.exp(-t * 0.7));
    out[i] = env * (Math.sin(TAU * f * t) + 0.22 * Math.sin(TAU * f * 2 * t) * Math.exp(-t * 3) + 0.06 * Math.sin(TAU * f * 3 * t) * Math.exp(-t * 5));
  }
  return fadeEdges(out, rate, 0.002, 0.25);
}

const INSTRUMENTS = [
  // [ファイル名, 作り方, 基準の MIDI, 長さ（秒）, サンプリング周波数]
  ["harp.wav",     (r) => harp(r, 60, 1.6),     22050],
  ["marimba.wav",  (r) => marimba(r, 60, 0.9),  22050],
  ["musicbox.wav", (r) => musicBox(r, 72, 1.4), 22050],
  ["bell.wav",     (r) => bell(r, 57, 2.6),     16000],
  ["pad.wav",      (r) => pad(r, 48, 3.0),      22050],
  ["bass.wav",     (r) => bass(r, 36, 1.0),     16000],
  ["horn.wav",     (r) => horn(r, 60, 2.2),     16000],
  ["kick.wav",     (r) => kick(r),              22050],
  ["tom.wav",      (r) => tom(r),               22050],
  ["snare.wav",    (r) => noiseHit(r, 0.3, 41, 900, 7000, 16, [185, 0.5, 20]), 22050],
  ["hat.wav",      (r) => noiseHit(r, 0.08, 43, 5000, 10000, 60), 22050],
  ["shaker.wav",   (r) => noiseHit(r, 0.12, 47, 3000, 9000, 35), 22050],
  ["crash.wav",    (r) => noiseHit(r, 1.6, 53, 2500, 7500, 2.4), 16000],
  // DT-624 手直し3（ジャズ・フュージョン・ソウル）
  ["epiano.wav",   (r) => epiano(r, 60, 1.8),   16000],
  ["organ.wav",    (r) => organ(r, 60, 2.2),    16000],
  ["upright.wav",  (r) => upright(r, 36, 1.0),  16000],
  ["clav.wav",     (r) => clav(r, 60, 0.6),     16000],
  ["brass.wav",    (r) => brass(r, 60, 1.0),    16000],
  ["ride.wav",     (r) => ride(r),              22050],
  ["rim.wav",      (r) => rim(r),               22050],
  ["clap.wav",     (r) => clap(r),              22050],
  ["brush.wav",    (r) => brush(r),             22050],
  // DT-624 手直し4（エレクトロニカ）
  ["synpad.wav",   (r) => synpad(r, 48, 3.0),   22050],
  ["pluck.wav",    (r) => pluck(r, 60, 0.7),    22050],
  ["subbass.wav",  (r) => subbass(r, 36, 1.0),  16000],
  ["kick808.wav",  (r) => kick808(r),           22050],
  ["ehat.wav",     (r) => ehat(r),              32000],
  ["lead.wav",     (r) => lead(r, 60, 2.2),     22050],
  ["fmbell.wav",   (r) => fmbell(r, 72, 1.6),   22050],
  // DT-624 手直し5（時代ごとの文明の音楽）
  ["skindrum.wav", (r) => skinDrum(r),          16000],
  ["flute.wav",    (r) => flute(r, 72, 1.6),    16000],
  ["choir.wav",    (r) => choir(r, 57, 2.6),    16000],
  ["lute.wav",     (r) => lute(r, 60, 1.0),     22050],
  ["anvil.wav",    (r) => anvil(r),             22050],
  ["accordion.wav",(r) => accordion(r, 60, 1.6), 16000],
  ["theremin.wav", (r) => theremin(r, 72, 2.0), 16000],
  ["gong.wav",     (r) => gong(r),              16000],
  // DT-624 手直し8（地域ごとの曲の作り直し・楽団が増える・壊している間のパート・崩れる効果音）
  ["strings.wav",  (r) => strings(r, 60, 2.4),  16000],
  ["timpani.wav",  (r) => timpani(r),           16000],
  ["taiko.wav",    (r) => taiko(r),             16000],
  // crumble.wav は DT-624 手直し11 で smash_* に替えて外した
  // DT-624 手直し9（和音の線）
  ["warm.wav",     (r) => warm(r, 60, 2.0),     22050],
  // DT-624 手直し11（建物が壊れる音：材質 × 大きさ）
  ["smash_wood_s.wav",  (r) => smash(r, "wood", "s", 101),  22050],
  ["smash_wood_l.wav",  (r) => smash(r, "wood", "l", 102),  22050],
  ["smash_stone_s.wav", (r) => smash(r, "stone", "s", 103), 22050],
  ["smash_stone_l.wav", (r) => smash(r, "stone", "l", 104), 22050],
  ["smash_metal_s.wav", (r) => smash(r, "metal", "s", 105), 22050],
  ["smash_metal_l.wav", (r) => smash(r, "metal", "l", 106), 22050],
];

mkdirSync(OUT, { recursive: true });
let total = 0;
for (const [name, make, rate] of INSTRUMENTS) {
  const bytes = writeWav(name, rate, make(rate));
  total += bytes;
  console.log(`${name.padEnd(14)} ${(bytes / 1024).toFixed(1).padStart(6)} KB`);
}
console.log(`合計 ${(total / 1024).toFixed(1)} KB → ${OUT}`);
