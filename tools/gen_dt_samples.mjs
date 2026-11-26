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
/** パッド：少しずらした鋸波3本をこもらせた帯。和音の床 */
function pad(rate, midi, sec) {
  const f = midiHz(midi), len = Math.floor(rate * sec), out = new Float32Array(len);
  const detune = [-0.0045, 0, 0.0052];
  const phase = [0, 0.33, 0.71];
  for (let i = 0; i < len; i++) {
    const t = i / rate;
    let v = 0;
    for (let k = 0; k < 3; k++) { const p = (f * (1 + detune[k]) * t + phase[k]) % 1; v += p * 2 - 1; }
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

const INSTRUMENTS = [
  // [ファイル名, 作り方, 基準の MIDI, 長さ（秒）, サンプリング周波数]
  ["harp.wav",     (r) => harp(r, 60, 1.6),     22050],
  ["marimba.wav",  (r) => marimba(r, 60, 0.9),  22050],
  ["musicbox.wav", (r) => musicBox(r, 72, 1.4), 22050],
  ["bell.wav",     (r) => bell(r, 57, 2.6),     16000],
  ["pad.wav",      (r) => pad(r, 48, 3.0),      16000],
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
];

mkdirSync(OUT, { recursive: true });
let total = 0;
for (const [name, make, rate] of INSTRUMENTS) {
  const bytes = writeWav(name, rate, make(rate));
  total += bytes;
  console.log(`${name.padEnd(14)} ${(bytes / 1024).toFixed(1).padStart(6)} KB`);
}
console.log(`合計 ${(total / 1024).toFixed(1)} KB → ${OUT}`);
