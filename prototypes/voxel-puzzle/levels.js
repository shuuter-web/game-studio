// -----------------------------------------------------------------
// レベルデータ。layers[y] は下の段から。各段は奥(z=0)から手前の行。文字は puzzle-core の INFO.char
//   . 空  # 土  H 石  X 鉄  M 苔  m 苔石  E 卵  S 分裂石  B 爆弾  I 氷
//   r b y 共鳴   + 拡げ石   = | / 貫き石(x,y,z)   W 除草石
// limit は solve.mjs で求めた最短手数（par）に余裕を足したもの。par は表示用
// -----------------------------------------------------------------
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.PuzzleLevels = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  return [
    {
      id: "L01", name: "はじめの爆弾", size: [3, 2, 3], par: 1, limit: 2,
      hint: "爆弾は周り3×3×3を巻き込む。",
      layers: [
        ["###", "###", "###"],
        ["###", "#B#", "###"],
      ],
    },
    {
      id: "L02", name: "氷はつながる", size: [5, 1, 5], par: 3, limit: 4,
      hint: "氷は隣が壊れると割れる。石は2回。",
      layers: [
        ["IIIII", "I...I", "I.H.I", "I...I", "IIIII"],
      ],
    },
    {
      id: "L03", name: "三色の箱", size: [3, 3, 3], par: 3, limit: 3,
      hint: "共鳴は同じ色を全部壊す。",
      layers: [
        ["rby", "byr", "yrb"],
        ["byr", "yrb", "rby"],
        ["yrb", "rby", "byr"],
      ],
    },
    {
      id: "L04", name: "拡げ石", size: [3, 3, 3], par: 2, limit: 3,
      hint: "拡げ石を壊すと、次のタップが3×3×3になる。",
      layers: [
        ["###", "###", "###"],
        ["###", "###", "###"],
        ["...", ".+.", "..."],
      ],
    },
    {
      id: "L05", name: "鉄と貫き", size: [5, 4, 5], par: 2, limit: 3,
      hint: "鉄はタップできない。貫き石で一直線に抜く。",
      layers: [
        ["../..", ".....", "=XXX.", ".....", "..X.."],
        ["..X..", ".....", ".....", ".....", "....."],
        ["..X..", ".....", ".....", ".....", "....."],
        ["..|..", ".....", ".....", ".....", "....."],
      ],
    },
    {
      id: "L06", name: "苔は増える", size: [4, 1, 4], par: 4, limit: 5,
      hint: "苔は毎ターン隣に増える。先に潰す。",
      layers: [
        ["M.II", "..II", "II..", "II.M"],
      ],
    },
    {
      id: "L07", name: "卵", size: [5, 1, 5], par: 5, limit: 6,
      hint: "卵は3ターンで苔になる。",
      layers: [
        ["EIIIE", "IIIII", "IIBII", "IIIII", "EIIIE"],
      ],
    },
    {
      id: "L08", name: "分裂石", size: [5, 1, 5], par: 3, limit: 4,
      hint: "分裂石をタップで壊すと2つに増える。連鎖で壊す。",
      layers: [
        ["SS=SS", ".....", "S.=.S", ".....", "SS=SS"],
      ],
    },
    {
      id: "L09", name: "除草", size: [5, 2, 5], par: 6, limit: 7,
      hint: "除草石は苔・苔石・卵を全部壊す。",
      layers: [
        ["M.#.M", ".###.", "##B##", ".###.", "M.#.M"],
        [".....", ".....", "..W..", ".....", "....."],
      ],
    },
    {
      id: "L10", name: "鉄の箱", size: [5, 3, 5], par: 2, limit: 3,
      hint: "中に何かある。",
      layers: [
        ["IIIII", "IrbyI", "IbyrI", "IyrbI", "IIIII"],
        ["XXXXX", "X+.=X", "X.H.X", "X/.+X", "XXXXX"],
        ["XXXXX", "XXXXX", "XXBXX", "XXXXX", "XXXXX"],
      ],
    },
    {
      id: "L11", name: "苔の塔", size: [3, 5, 3], par: 3, limit: 4,
      hint: "柱を探す。",
      layers: [
        ["rIb", "IMI", "bIr"],
        ["I.I", "...", "I.I"],
        ["###", "#B#", "###"],
        ["...", ".|.", "..."],
        ["...", ".E.", "..."],
      ],
    },
    {
      id: "L12", name: "分裂の畑", size: [6, 2, 6], par: 5, limit: 6,
      hint: "何から壊すか。",
      layers: [
        ["SS=SSS", "B#..#B", "SSS=SS", ".#BB#.", "SS=SSS", "B....B"],
        ["......", ".....+", "......", "......", "......", "E....E"],
      ],
    },
    {
      id: "L13", name: "苔の巣", size: [5, 2, 5], par: 3, limit: 4,
      hint: "除草石はどこにある。",
      layers: [
        ["IIIII", "IMIMI", "IIWII", "IMIMI", "IIIII"],
        [".....", ".....", "..H..", ".....", "....."],
      ],
    },
    {
      id: "L14", name: "順番", size: [5, 2, 5], par: 3, limit: 3,
      hint: "拡げ石を2つ同時に壊すと5×5×5。",
      layers: [
        ["I+I+I", "IIBII", "IIIII", "SS=SS", ".XXX."],
        [".....", ".....", ".....", ".....", "..#.."],
      ],
    },
    {
      id: "L15", name: "全部入り", size: [6, 2, 6], par: 5, limit: 6,
      hint: "卵が孵る前に。",
      layers: [
        ["EIIIIE", "ISBBSI", "IB++BI", "IB++BI", "ISBBSI", "EIIIIE"],
        ["......", "......", "..HH..", "..HH..", "......", "......"],
      ],
    },
  ];
});
