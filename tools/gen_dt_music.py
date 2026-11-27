"""Dragon Tide（DT-624 手直し8・11/27）: 地域ごとの曲を組み立てて prototypes/dragon-tide/assets/audio/music.json の songs を書き出す。

  python3 tools/gen_dt_music.py          # music.json の songs・band・tug・destroy を書き直す（instruments・sfx・voiceLimit は残す）

なぜ生成するか：21地域＋タイトルの曲を1曲ずつ手で JSON に書くと、和音の音・旋律の高さを MIDI の番号で書くことになり、
直すときに読めない。ここでは曲を「調・旋法・和音の進み（度数）・主題（度数と長さ）・楽団の顔ぶれ・刻みの型」で書き、
MIDI の番号と伴奏の譜面に展開する。ゲームは music.json だけを読む（数値を直すだけなら music.json を直接いじってもよいが、
作り直すときはここを直して書き出す）。

曲の作り（11/27 Shooter「BGM は地域ごとを基本に」「ゼロベースで作り直す」「攻略を進めると楽団が充実していく、に注力」
「地域の一曲の中に、二つの主題を入れて綱引き」「破壊音は SE で、破壊している間は鳴るパートがあると良い」）:
  ・1地域1曲。同じ調・同じ速さの中に「文明の主題」（その地域の人々の曲）と「竜の主題」（攻め込む竜の側の曲）を持つ。
    4小節（phraseBars）ごとにどちらか一方の主題を弾く。竜の側に回す割合は攻略の進み具合で tug.start → tug.end（ゲーム側）。
    主題はそれぞれ8小節で、そちらの側が弾く2回に1回ずつ前半・後半を弾く。
  ・楽団（band）：攻略の進み具合（壊した街の割合）で段が上がり、鳴る楽器が増える（0＝和音の床と主題だけ → 1＝低音 →
    2＝刻み（打楽器）→ 3＝対旋律（分散和音）→ 4＝主題の重ね（別の楽器で）・節目のシンバル・フィル）。段はフレーズの頭でだけ変わる。
  ・壊している間のパート（destroy）：建物が続けて崩れている間だけ、刻みの弦（drive）と太鼓（driveDrum）がふくらむ。
  ・曲調：能天気にしない。文明の側も「攻め込まれる国の誇りと不安」を、その地域の楽器と旋法で。竜の側は同じ調で低く重く。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC = os.path.normpath(os.path.join(HERE, "..", "prototypes", "dragon-tide", "assets", "audio", "music.json"))

MODES = {
    "aeolian": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "harmonic": [0, 2, 3, 5, 7, 8, 11], "phrygdom": [0, 1, 4, 5, 7, 8, 10], "lydian": [0, 2, 4, 6, 7, 9, 11],
    "in": [0, 1, 5, 7, 8],   # 都節（陰音階）
}
QUALITY = {"m": [0, 3, 7], "M": [0, 4, 7], "d": [0, 3, 6], "p": [0, 7, 12], "s": [0, 5, 7],
           "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10], "M7": [0, 4, 7, 11]}
STEPS = 16

# 楽器ごとの大きさの目安（かけらの鳴りの強さが違うので、主題・重ねの大きさをここでそろえる）
LEAD_GAIN = {"flute": 0.12, "horn": 0.13, "brass": 0.10, "organ": 0.075, "choir": 0.11, "theremin": 0.09, "lead": 0.075,
             "clav": 0.10, "epiano": 0.12, "fmbell": 0.10, "musicbox": 0.11, "accordion": 0.09, "strings": 0.07}
# 主題の高さの真ん中の目安（楽器の鳴りのよい音域。主題はここに近い高さへオクターブ単位でずらす。spec の octave は使わない）
LEAD_CENTER = {"flute": 76, "musicbox": 79, "fmbell": 76, "theremin": 74, "horn": 60, "brass": 60, "choir": 62, "organ": 69,
               "strings": 57, "lead": 64, "clav": 69, "epiano": 69, "accordion": 67}
PAD_GAIN = {"pad": 0.06, "strings": 0.045, "organ": 0.04, "synpad": 0.05, "choir": 0.05}
COUNTER_GAIN = {"flute": 0.06, "harp": 0.06, "lute": 0.08, "marimba": 0.08, "pluck": 0.06, "fmbell": 0.05, "musicbox": 0.06, "bell": 0.04, "clav": 0.06}
BASS_GAIN = {"bass": 0.12, "upright": 0.12, "subbass": 0.12}

# 刻みの型（band 2 から。band 4 で足す節目は FULL）。[楽器, 鳴らす step, 強さ, 大きさ, 何小節ごと（無し＝毎小節）, 鳴らす小節]
GROOVES = {
    "folk":     [["skindrum", [0, 6, 8], [1, 0.6, 0.8], 0.13], ["shaker", [0, 2, 4, 6, 8, 10, 12, 14], [0.9, 0.4, 0.7, 0.4] * 2, 0.09]],
    "river":    [["shaker", list(range(16)), [0.8, 0.3, 0.5, 0.3] * 4, 0.06], ["rim", [4, 12], [1, 0.8], 0.07], ["tom", [0], [1], 0.08]],
    "court":    [["timpani", [0, 8], [1, 0.7], 0.12, None, None, True], ["snare", [12], [0.6], 0.06]],
    "march":    [["snare", [4, 12, 14], [1, 0.9, 0.5], 0.10], ["kick", [0, 8], [1, 0.8], 0.13], ["hat", [0, 2, 4, 6, 8, 10, 12, 14], [0.8, 0.4] * 4, 0.05]],
    "ritual":   [["taiko", [0, 10], [1, 0.7], 0.14], ["rim", [4, 12], [0.8, 1], 0.06], ["bell", [0], [1], 0.05, 4, 0]],
    "space":    [["kick808", [0, 10], [1, 0.7], 0.13], ["ehat", [0, 2, 4, 6, 8, 10, 12, 14], [0.6, 0.3] * 4, 0.05], ["clap", [12], [0.8], 0.07]],
    "train":    [["shaker", list(range(16)), [1, 0.35, 0.6, 0.35] * 4, 0.08], ["brush", [4, 12], [1, 0.9], 0.08], ["kick", [0, 8, 10], [1, 0.7, 0.5], 0.12]],
    "forest":   [["skindrum", [0, 6, 10], [1, 0.6, 0.7], 0.12], ["shaker", [0, 2, 4, 6, 8, 10, 12, 14], [0.8, 0.4] * 4, 0.07], ["rim", [3, 11], [0.6, 0.6], 0.05]],
    "electro":  [["kick808", [0, 4, 8, 12], [1, 0.8, 0.9, 0.8], 0.13], ["clap", [4, 12], [1, 1], 0.08], ["ehat", list(range(16)), [0.7, 0.3, 0.5, 0.3] * 4, 0.05]],
    "pulse":    [["kick", [0, 8], [1, 0.8], 0.12], ["ehat", [0, 2, 4, 6, 8, 10, 12, 14], [0.6, 0.3] * 4, 0.05], ["clap", [12], [0.8], 0.06], ["tom", [14], [0.6], 0.07]],
    "heavy":    [["taiko", [0, 7, 8], [1, 0.5, 0.8], 0.15], ["anvil", [4, 12], [0.5, 0.6], 0.04], ["gong", [0], [1], 0.06, 8, 0]],
    "airy":     [["shaker", [0, 2, 4, 6, 8, 10, 12, 14], [0.6, 0.3] * 4, 0.05], ["rim", [12], [0.7], 0.05], ["tom", [0], [0.8], 0.07]],
    "jungle":   [["skindrum", [0, 3, 6, 10, 12], [1, 0.6, 0.8, 0.7, 0.6], 0.12], ["shaker", list(range(16)), [0.7, 0.3, 0.5, 0.3] * 4, 0.05]],
    "taiko":    [["taiko", [0, 6, 8], [1, 0.6, 0.9], 0.15], ["rim", [4, 12, 14], [0.9, 1, 0.5], 0.07]],
    "hop":      [["rim", [0, 3, 6, 10, 12], [1, 0.6, 0.8, 0.7, 0.6], 0.07], ["tom", [8], [0.8], 0.08], ["shaker", [0, 2, 4, 6, 8, 10, 12, 14], [0.6, 0.3] * 4, 0.05]],
    "oompah":   [["kick", [0, 8], [1, 0.9], 0.13], ["snare", [4, 12], [0.8, 0.9], 0.08], ["hat", [0, 2, 4, 6, 8, 10, 12, 14], [0.7, 0.4] * 4, 0.04]],
    "gentle":   [["rim", [0], [0.8], 0.05], ["shaker", [8], [0.7], 0.05], ["tom", [0], [0.7], 0.07, 4, 0]],
    "tide":     [["rim", [0, 3, 6, 10, 12], [1, 0.5, 0.7, 0.6, 0.5], 0.06], ["shaker", [0, 2, 4, 6, 8, 10, 12, 14], [0.7, 0.3] * 4, 0.05], ["tom", [8], [0.7], 0.08]],
    "beacon":   [["skindrum", [0, 8, 11], [1, 0.8, 0.6], 0.13], ["shaker", [0, 2, 4, 6, 8, 10, 12, 14], [0.6, 0.3] * 4, 0.05], ["bell", [0], [1], 0.05, 4, 0]],
    "baroque":  [["timpani", [0, 8], [1, 0.7], 0.12, None, None, True], ["snare", [12], [0.5], 0.05]],
}
# band 4 の節目：8小節ごとのシンバル・4小節ごとのタムのフィル
FULL = [["crash", [0], [1], 0.07, 8, 0], ["tom", [12, 13, 14, 15], [0.6, 0.7, 0.8, 1], 0.08, 4, 3, True]]

BASS = {   # [step, 根音からの半音, 長さ]
    "rootfifth": [[0, 0, 6], [8, 7, 6]],
    "root4": [[0, 0, 3], [4, 0, 3], [8, 0, 3], [12, 7, 3]],
    "root8": [[s, 0 if s % 8 else 0, 2] for s in range(0, 16, 2)],
    "drone": [[0, 0, 16]],
    "synco": [[0, 0, 5], [6, 0, 3], [10, 7, 5]],
    "oompah": [[0, 0, 3], [8, 7, 3]],
    "pulse": [[0, 0, 2], [3, 0, 2], [8, 0, 2], [11, 7, 2], [14, 0, 2]],
}
COUNTER = {   # [step, 和音の何番目の音]（3＝1番目の1オクターブ上）
    "up8": [[0, 0], [2, 1], [4, 2], [6, 3], [8, 2], [10, 1], [12, 0], [14, 1]],
    "flow16": [[s, [0, 1, 2, 3, 4, 3, 2, 1][s % 8]] for s in range(16)],
    "sparse": [[0, 0], [6, 2], [8, 1], [14, 3]],
    "roll": [[0, 0], [3, 1], [6, 2], [8, 3], [11, 2], [14, 1]],
    "bells": [[0, 3], [4, 2], [8, 4], [12, 2]],
}
DRIVE = [[0, 0, 2], [2, 0, 2], [4, 7, 2], [6, 0, 2], [8, 0, 2], [10, 0, 2], [12, 7, 2], [14, 12, 2]]   # 壊している間の弦の刻み（8分）

#  曲の書き方：
#   mode・tonic（主題の0度の MIDI）・tempo・groove・bass・counter
#   civ / dragon: chords＝8小節の和音（"度数（0から）＋性質"。度数の前の b/# で半音下げ・上げ。性質 m M d p s 7 m7 M7）、
#                 theme＝8小節の主題（"度数:長さ" を空白で、小節を | で。度数は旋法の音の番号（0から・7で1オクターブ上・負は下）、
#                 + / - で半音上げ・下げ、r は休み。長さは16分音符の数で、1小節で16）、lead（楽器）・octave（主題をずらす半音）
#   pal: pad（和音の床）・counter（対旋律）・double（band 4 で主題を重ねる楽器）・doubleOctave・bassInst・drive（壊している間の刻み）・driveDrum
SONGS = {
    "title": dict(name="タイトル", mood="静かな序曲。笛の文明の主題と、角笛の竜の主題がゆっくり交互に", mode="aeolian", tonic=62, tempo=76,
        groove=None, bass="drone", counter="sparse", fixedBand=1,
        pal=dict(pad="strings", counter="harp", double="choir", bassInst="bass", drive="strings", driveDrum="timpani"),
        civ=dict(lead="flute", octave=12, chords="0m 5M 2M 6M 0m 5M 6M 4M",
                 theme="4:8 2:8 | 2:8 0:8 | 4:6 6:2 9:8 | 8:16 | 7:6 4:2 2:8 | 5:8 2:8 | 6:8 3:8 | 4:16"),
        dragon=dict(lead="horn", octave=-12, chords="0m 0m 5M 4M 0m 0m 5M 4M",
                    theme="0:8 4:8 | 2:8 0:8 | 5:8 2:8 | 1:8 4:8 | 0:4 2:4 4:8 | 7:16 | 5:6 4:2 2:8 | 4:16")),
    "continent": dict(name="大陸", mood="平原の町々の古い民謡（ドリア）。笛は郷愁、竜は重い角笛", mode="dorian", tonic=62, tempo=100,
        groove="folk", bass="rootfifth", counter="up8",
        pal=dict(pad="strings", counter="lute", double="choir", doubleOctave=-12, bassInst="bass", drive="strings", driveDrum="taiko"),
        civ=dict(lead="flute", octave=12, chords="0m 6M 3M 0m 0m 6M 3M 4M",
                 theme="7:4 4:4 2:4 4:4 | 6:6 3:2 1:8 | 5:6 3:2 0:8 | 2:4 1:4 0:8 | 7:4 4:4 2:4 4:4 | 6:4 7:4 8:8 | 7:6 5:2 3:8 | 4:12 r:4"),
        dragon=dict(lead="horn", octave=-12, chords="0m 2M 6M 0m 0m b5M 6M 4M",
                    theme="0:6 4:2 2:4 0:4 | 2:8 4:4 6:4 | 6:6 3:2 1:8 | 0:12 r:4 | 4:4 7:4 4:4 2:4 | 5-:8 2:4 0:4 | 1:4 3:4 6:8 | 4:8 1:8")),
    "riverline": dict(name="大河の線状都市", mood="大河に沿った都の祈り。流れる竪琴と笛、竜は低い金管", mode="aeolian", tonic=57, tempo=92,
        groove="river", bass="synco", counter="flow16",
        pal=dict(pad="pad", counter="harp", double="strings", doubleOctave=12, bassInst="upright", drive="strings", driveDrum="timpani"),
        civ=dict(lead="flute", octave=12, chords="0m 5M 2M 6M 0m 5M 3m 4M",
                 theme="4:4 2:2 4:2 7:8 | 7:4 5:4 2:8 | 4:6 2:2 6:8 | 6:4 3:4 1:8 | 4:4 7:4 9:4 7:4 | 7:6 5:2 2:8 | 3:4 5:4 7:8 | 6+:4 4:4 r:8"),
        dragon=dict(lead="brass", octave=0, chords="0m 0m 5M 4M 0m 3m 5M 4M",
                    theme="0:4 0:2 2:2 4:8 | 7:6 6:2 4:8 | 5:4 4:4 2:8 | 4:12 r:4 | 4:4 7:4 4:4 2:4 | 3:6 5:2 7:8 | 5:8 2:8 | 6+:4 4:4 1:8")),
    "citadel": dict(name="同心円の城塞都市", mood="鐘とオルガンの荘重な城塞（短調）。竜は低い金管で門を叩く", mode="aeolian", tonic=60, tempo=84,
        groove="court", bass="rootfifth", counter="bells",
        pal=dict(pad="organ", counter="harp", double="choir", doubleOctave=0, bassInst="bass", drive="strings", driveDrum="timpani"),
        civ=dict(lead="organ", octave=12, chords="0m 5M 3m 4M 0m 2M 5M 4M",
                 theme="7:8 4:4 2:4 | 5:8 7:4 5:4 | 3:8 5:4 3:4 | 6+:8 4:8 | 7:4 9:4 11:8 | 9:8 6:4 4:4 | 7:6 5:2 2:8 | 1:8 4:8"),
        dragon=dict(lead="brass", octave=-12, chords="0m 0m 5M 6M 0m 3m 5M 4M",
                    theme="0:4 2:4 4:8 | 7:6 6:2 4:8 | 5:8 0:8 | 6:8 3:4 1:4 | 4:4 7:4 4:4 2:4 | 3:8 5:8 | 2:8 0:8 | -1+:8 1:8")),
    "frontline": dict(name="長城の防衛線", mood="長城を守る兵の緊張した軍楽（短調の行進）。竜は角笛で城壁に迫る", mode="aeolian", tonic=62, tempo=112,
        groove="march", bass="root4", counter="up8",
        pal=dict(pad="strings", counter="flute", double="choir", doubleOctave=-12, bassInst="bass", drive="strings", driveDrum="taiko"),
        civ=dict(lead="brass", octave=0, chords="0m 6M 5M 4M 0m 6M 5M 4M",
                 theme="0:2 0:2 4:4 4:2 2:2 0:4 | 6:4 3:4 1:8 | 5:4 2:4 0:4 2:4 | 1:8 4:8 | 4:2 4:2 7:4 7:4 4:4 | 6:4 8:4 6:4 3:4 | 5:4 4:4 2:8 | 4:12 r:4"),
        dragon=dict(lead="horn", octave=-12, chords="0m 0m 5M 5M 3m 3m 4M 4M",
                    theme="0:6 2:2 4:8 | 7:6 6:2 4:8 | 5:6 4:2 2:8 | 0:8 2:8 | 3:6 5:2 7:8 | 5:4 3:4 0:8 | 1:6 4:2 6+:8 | 4:16")),
    "sanctuary": dict(name="四方の祠の結界", mood="祠を結ぶ祈り（都節）。尺八のような笛、竜は低い合唱でにじり寄る", mode="in", tonic=64, tempo=76,
        groove="ritual", bass="drone", counter="sparse",
        pal=dict(pad="choir", counter="lute", double="strings", doubleOctave=0, bassInst="bass", drive="strings", driveDrum="taiko", dragonPad="pad"),
        civ=dict(lead="flute", octave=12, chords="0p 1M 2m 0p 0p 2m 1M 0p",
                 theme="0:6 1:2 0:8 | 1:8 2:4 4:4 | 2:6 4:2 5:8 | 3:4 1:4 0:8 | 5:6 4:2 3:8 | 2:8 4:4 2:4 | 1:6 2:2 4:8 | 0:16"),
        dragon=dict(lead="choir", octave=0, chords="0p 0p 1M 1M 2m 2m 1M 0p",
                    theme="0:8 0:4 1:4 | 3:8 0:8 | 1:8 2:8 | 4:8 2:8 | 2:4 4:4 5:8 | 4:8 2:8 | 1:8 4:8 | 0:16")),
    "asteroids": dict(name="漂う岩塊の小惑星帯", mood="無重力の冷たい漂い。テルミンの文明の主題、竜はシンセのリード", mode="aeolian", tonic=59, tempo=90,
        groove="space", bass="synco", counter="flow16", muffleHz=7000,
        pal=dict(pad="synpad", counter="fmbell", double="strings", doubleOctave=0, bassInst="subbass", drive="pluck", driveDrum="tom"),
        civ=dict(lead="theremin", octave=12, chords="0m7 5M7 2M 6M 0m7 5M7 3m 4m",
                 theme="4:12 2:4 | 4:8 0:8 | 2:8 6:8 | 1:12 r:4 | 7:8 6:4 4:4 | 7:4 4:4 2:8 | 3:8 5:8 | 4:16"),
        dragon=dict(lead="lead", octave=0, chords="0m 0m 5M 4m 0m 0m 5M 6M",
                    theme="0:4 4:4 7:8 | 7:4 4:4 2:8 | 5:8 7:8 | 4:8 1:8 | 7:4 9:4 11:8 | 9:8 7:8 | 5:4 4:4 2:8 | 6:8 1:8")),
    "railway": dict(name="無人列車の走る軌道", mood="誰もいない列車の機械の反復と追走（ドリア）。クラビネットと金管", mode="dorian", tonic=55, tempo=120,
        groove="train", bass="root8", counter="up8",
        pal=dict(pad="pad", counter="marimba", double="strings", doubleOctave=12, bassInst="bass", drive="strings", driveDrum="snare"),
        civ=dict(lead="clav", octave=12, chords="0m 0m 3M 3M 6M 6M 0m 4m",
                 theme="4:2 4:2 2:2 0:2 4:4 2:4 | 7:4 4:4 2:8 | 3:2 3:2 5:4 7:8 | 5:4 3:4 0:8 | 6:2 6:2 8:4 6:8 | 3:4 1:4 -1:8 | 0:4 2:4 4:8 | 4:8 1:8"),
        dragon=dict(lead="brass", octave=0, chords="0m 2M 3M 0m 0m 2M 6M 4M",
                    theme="0:6 2:2 4:8 | 6:6 4:2 2:8 | 3:4 5:4 7:8 | 4:12 r:4 | 7:4 4:4 2:4 4:4 | 4:8 6:8 | 8:6 6:2 3:8 | 4:8 6+:8")),
    "forest": dict(name="森に覆われた大樹海", mood="深い森の神秘と危うさ（ドリア）。マリンバと笛、竜は合唱で木々を揺らす", mode="dorian", tonic=64, tempo=96,
        groove="forest", bass="synco", counter="roll",
        pal=dict(pad="pad", counter="marimba", double="horn", doubleOctave=-12, bassInst="upright", drive="strings", driveDrum="taiko", dragonPad="strings"),
        civ=dict(lead="flute", octave=12, chords="0m 6M 0m 3M 0m 6M 2M 4m",
                 theme="4:4 2:4 0:8 | 1:6 6:2 3:8 | 2:4 4:4 7:8 | 5:8 3:8 | 7:4 9:4 7:4 4:4 | 6:6 8:2 6:8 | 4:8 2:8 | 1:8 4:8"),
        dragon=dict(lead="choir", octave=0, chords="0m 0m 6M 6M 2M 2M 3M 4m",
                    theme="0:8 4:8 | 2:6 4:2 7:8 | 6:8 3:8 | 1:16 | 2:8 4:8 | 6:4 4:4 2:8 | 3:8 5:8 | 4:16")),
    "metro": dict(name="車列の流れる大都会", mood="夜の大都会の冷たい疾走（短調）。エレピの文明の主題、竜はシンセのリード", mode="aeolian", tonic=53, tempo=124,
        groove="electro", bass="pulse", counter="flow16", muffleHz=9000,
        pal=dict(pad="synpad", counter="pluck", double="strings", doubleOctave=12, bassInst="subbass", drive="pluck", driveDrum="kick808"),
        civ=dict(lead="epiano", octave=12, chords="0m7 5M7 2M 6M 0m7 5M7 3m7 4m7",
                 theme="4:4 6:4 7:4 6:4 | 4:8 2:8 | 6:6 4:2 2:8 | 1:8 6:8 | 7:4 9:4 11:4 9:4 | 9:8 7:8 | 7:4 5:4 3:8 | 4:16"),
        dragon=dict(lead="lead", octave=0, chords="0m 0m 5M 6M 0m 0m 3m 4M",
                    theme="0:2 0:2 7:4 4:6 6:2 | 2:8 0:8 | 5:4 7:4 9:8 | 8:8 6:8 | 7:4 4:4 2:4 4:4 | 0:16 | 3:8 5:8 | 6+:8 4:8")),
    "plateau": dict(name="光線の塔が立つ高原", mood="澄んだ高原と光線の塔の不穏な唸り（ドリア）。FM の鐘と金管", mode="dorian", tonic=57, tempo=108,
        groove="pulse", bass="rootfifth", counter="up8",
        pal=dict(pad="synpad", counter="pluck", double="strings", doubleOctave=0, bassInst="bass", drive="strings", driveDrum="tom"),
        civ=dict(lead="fmbell", octave=12, chords="0m 3M 6M 0m 0m 3M 2M 4m",
                 theme="4:4 7:4 4:8 | 5:8 3:8 | 6:6 8:2 6:8 | 4:12 r:4 | 7:4 9:4 11:8 | 10:8 7:8 | 9:6 6:2 4:8 | 4:16"),
        dragon=dict(lead="brass", octave=0, chords="0m 0m b5M 6M 0m 0m b5M 4M",
                    theme="0:6 2:2 4:8 | 7:8 4:8 | 5-:8 0:8 | 6:8 1:8 | 4:4 7:4 9:8 | 7:16 | 9:8 7:4 5-:4 | 6+:8 4:8")),
    "heroland": dict(name="英雄が守る王国", mood="英雄の国の気高い国歌（ヘ長調の響き）と、それを呑む竜のニ短調の合唱", mode="aeolian", tonic=62, tempo=96,
        groove="court", bass="root4", counter="up8",
        pal=dict(pad="strings", counter="harp", double="brass", doubleOctave=0, bassInst="bass", drive="strings", driveDrum="timpani"),
        civ=dict(lead="horn", octave=0, chords="2M 6M 5M 2M 2M 5M 6M 2M",
                 theme="2:4 4:4 6:4 9:4 | 8:8 6:8 | 7:6 5:2 2:8 | 4:12 r:4 | 9:4 8:4 9:4 11:4 | 12:8 9:8 | 8:6 6:2 3:8 | 2:16"),
        dragon=dict(lead="choir", octave=0, chords="0m 5M 6M 0m 0m 5M 4M 4M",
                    theme="0:4 2:4 4:8 | 5:8 2:8 | 3:8 6:8 | 4:6 2:2 0:8 | 7:6 4:2 2:8 | 5:8 7:8 | 6+:8 4:8 | 1:8 4:8")),
    "wasteland": dict(name="巨岩を拝む荒地", mood="乾いた荒地の岩への祈り（フリギア）。合唱と和太鼓・金床、竜は角笛", mode="phrygian", tonic=60, tempo=80,
        groove="heavy", bass="drone", counter="sparse",
        pal=dict(pad="pad", counter="marimba", double="brass", doubleOctave=-12, bassInst="bass", drive="strings", driveDrum="taiko"),
        civ=dict(lead="choir", octave=0, chords="0p 1M 0p 6m 0p 1M 5M 0p",
                 theme="0:6 1:2 0:8 | 1:8 3:8 | 4:8 4:4 2:4 | 6:8 1:8 | 7:8 4:8 | 8:8 5:8 | 7:6 5:2 2:8 | 0:16"),
        dragon=dict(lead="horn", octave=-12, chords="0p 0p 1M 1M 6m 6m 1M 0p",
                    theme="0:4 0:4 4:8 | 7:6 6:2 4:8 | 8:8 5:8 | 3:16 | 6:8 8:8 | 10:8 8:8 | 8:6 5:2 3:8 | 0:16")),
    "skyland": dict(name="雲海に浮かぶ浮き城の空", mood="雲海に浮かぶ城の浮遊感と寂しさ（リディア）。オルゴールと竪琴、竜は弦で影を落とす", mode="lydian", tonic=65, tempo=88,
        groove="airy", bass="rootfifth", counter="flow16",
        pal=dict(pad="pad", counter="harp", double="choir", doubleOctave=-12, bassInst="bass", drive="strings", driveDrum="timpani"),
        civ=dict(lead="musicbox", octave=12, chords="0M7 1M 0M7 1M 5m 1M 0M7 4M",
                 theme="4:4 6:4 4:8 | 5:8 3:8 | 2:4 4:4 6:8 | 1:12 r:4 | 5:4 7:4 9:8 | 8:8 5:8 | 6:6 4:2 2:8 | 4:16"),
        dragon=dict(lead="strings", octave=-12, chords="5m 2m 1M 5m 5m 2m 6m 1M",
                    theme="5:8 2:8 | 2:6 4:2 6:8 | 1:8 5:8 | 5:16 | 9:8 7:8 | 6:8 4:8 | 6:8 3:8 | 1:16")),
    "serpent": dict(name="蛇神を祀る密林の国", mood="蛇神の妖しさ（フリギア・ドミナント）。蛇使いの笛、竜は金管で絡みつく", mode="phrygdom", tonic=64, tempo=104,
        groove="jungle", bass="synco", counter="roll",
        pal=dict(pad="strings", counter="marimba", double="choir", doubleOctave=-12, bassInst="bass", drive="strings", driveDrum="taiko"),
        civ=dict(lead="flute", octave=12, chords="0M 1M 0M 1M 6m 3m 1M 0M",
                 theme="0:2 1:2 2:4 4:4 2:4 | 3:6 1:2 5:8 | 4:4 2:4 0:8 | 1:12 r:4 | 6:4 8:4 10:8 | 7:6 5:2 3:8 | 1:6 3:2 5:8 | 0:16"),
        dragon=dict(lead="brass", octave=-12, chords="0M 0M 1M 1M 3m 3m 1M 0M",
                    theme="0:4 2:4 4:8 | 7:6 6:2 4:8 | 5:8 3:8 | 1:16 | 3:4 5:4 7:8 | 5:8 3:8 | 1:6 3:2 5:8 | 4:8 0:8")),
    "swordway": dict(name="剣の道の国", mood="張りつめた剣気（都節）。笛と琴、和太鼓、竜は低い合唱", mode="in", tonic=57, tempo=92,
        groove="taiko", bass="drone", counter="roll",
        pal=dict(pad="pad", counter="lute", double="horn", doubleOctave=-12, bassInst="bass", drive="strings", driveDrum="taiko", dragonPad="strings"),
        civ=dict(lead="flute", octave=12, chords="0p 1M 2m 0p 0p 2m 1M 0p",
                 theme="0:6 1:2 0:8 | 1:8 2:8 | 2:6 4:2 5:8 | 3:8 0:8 | 5:6 4:2 3:8 | 4:8 2:8 | 1:6 2:2 4:8 | 0:16"),
        dragon=dict(lead="choir", octave=0, chords="0p 0p 2m 2m 1M 1M 0p 0p",
                    theme="0:8 3:8 | 5:8 3:8 | 2:8 4:8 | 5:8 2:8 | 1:8 4:8 | 6:8 4:8 | 5:8 3:8 | 0:16")),
    "mushroom": dict(name="増えるキノコの里", mood="ひそかに増えるキノコの不思議と不気味さ（ドリア）。オルゴールとマリンバ、竜はシンセ", mode="dorian", tonic=59, tempo=100,
        groove="hop", bass="synco", counter="roll",
        pal=dict(pad="pad", counter="marimba", double="strings", doubleOctave=0, bassInst="upright", drive="marimba", driveDrum="tom"),
        civ=dict(lead="musicbox", octave=12, chords="0m 3M 0m 3M 2M 6M 0m 4m",
                 theme="4:4 2:4 0:4 2:4 | 3:4 5:4 7:8 | 4:6 7:2 4:8 | 5:12 r:4 | 6:4 4:4 2:8 | 8:8 6:8 | 7:4 4:4 2:8 | 4:16"),
        dragon=dict(lead="lead", octave=0, chords="0m 0m 2M 3M 0m 0m 6M 4M",
                    theme="0:4 0:4 4:8 | 7:8 4:8 | 6:8 2:8 | 5:8 3:8 | 4:4 2:4 0:8 | 2:16 | 6:8 1:8 | 6+:8 4:8")),
    "bombland": dict(name="爆弾玉の国", mood="火薬の国の暗い行進（和声的短音階）。アコーディオンのずんちゃっ、竜は低い金管", mode="harmonic", tonic=62, tempo=116,
        groove="oompah", bass="oompah", counter="up8",
        pal=dict(pad="pad", counter="marimba", double="choir", doubleOctave=-12, bassInst="bass", drive="strings", driveDrum="tom"),
        civ=dict(lead="accordion", octave=0, chords="0m 4M 0m 4M 3m 0m 4M 0m",
                 theme="4:2 4:2 2:2 0:2 2:8 | 6:4 1:4 4:8 | 7:4 4:4 2:8 | 1:12 r:4 | 5:4 3:4 0:8 | 2:4 4:4 7:8 | 6:6 5:2 4:8 | 0:16"),
        dragon=dict(lead="brass", octave=-12, chords="0m 0m 5M 4M 0m 3m 5M 4M",
                    theme="0:4 4:4 7:8 | 7:4 4:4 2:8 | 5:8 2:8 | 4:4 6:4 8:8 | 7:6 4:2 2:8 | 3:8 5:8 | 5:4 4:4 2:8 | 1:8 4:8")),
    "flowergarden": dict(name="竜食い花の園", mood="甘く妖しい罠の花園（和声的短音階）。オルゴールと竪琴、竜は合唱", mode="harmonic", tonic=57, tempo=84,
        groove="gentle", bass="rootfifth", counter="flow16",
        pal=dict(pad="pad", counter="harp", double="strings", doubleOctave=0, bassInst="bass", drive="strings", driveDrum="timpani", dragonPad="strings"),
        civ=dict(lead="musicbox", octave=12, chords="0m 5M 3m 4M 0m 5M 3m 4M",
                 theme="4:4 7:4 9:8 | 7:4 5:4 2:8 | 5:6 3:2 0:8 | 6:8 4:8 | 9:4 11:4 9:8 | 7:6 5:2 2:8 | 3:4 5:4 7:8 | 4:16"),
        dragon=dict(lead="choir", octave=0, chords="0m 0m 3m 3m 5M 5M 4M 4M",
                    theme="0:8 4:8 | 2:6 0:2 4:8 | 3:8 5:8 | 7:16 | 5:8 2:8 | 0:8 2:8 | 6:8 4:8 | 1:8 4:8")),
    "beach": dict(name="宿借りの浜", mood="寄せては返す波と、殻にこもる浜の不穏（ドリア）。FM の鐘とマリンバ、竜は金管", mode="dorian", tonic=54, tempo=104,
        groove="tide", bass="synco", counter="roll",
        pal=dict(pad="pad", counter="marimba", double="strings", doubleOctave=12, bassInst="upright", drive="strings", driveDrum="tom"),
        civ=dict(lead="fmbell", octave=12, chords="0m 3M 0m 3M 6M 2M 3M 4m",
                 theme="4:4 2:4 0:8 | 3:6 5:2 7:8 | 2:4 4:4 7:8 | 5:12 r:4 | 6:4 8:4 10:8 | 9:8 6:8 | 7:6 5:2 3:8 | 4:16"),
        dragon=dict(lead="brass", octave=0, chords="0m 0m 6M 6M 2M 3M 4m 4m",
                    theme="0:4 4:4 7:8 | 7:6 4:2 2:8 | 6:8 3:8 | 8:8 6:8 | 2:6 4:2 6:8 | 3:8 7:8 | 4:8 6:8 | 4:16")),
    "beacon": dict(name="烽火の連なる丘陵", mood="丘から丘へ呼び交わす角笛と烽火の警戒（短調）。竜は合唱で丘を越える", mode="aeolian", tonic=61, tempo=98,
        groove="beacon", bass="rootfifth", counter="up8",
        pal=dict(pad="strings", counter="lute", double="brass", doubleOctave=0, bassInst="bass", drive="strings", driveDrum="taiko"),
        civ=dict(lead="horn", octave=0, chords="0m 6M 5M 6M 0m 6M 5M 4m",
                 theme="0:4 4:4 7:8 | 6:6 3:2 1:8 | 5:4 7:4 9:8 | 8:12 r:4 | 7:4 4:4 2:4 4:4 | 6:8 3:8 | 5:6 2:2 0:8 | 4:16"),
        dragon=dict(lead="choir", octave=0, chords="0m 0m 5M 5M 3m 3m 4M 4M",
                    theme="0:8 2:8 | 4:6 2:2 0:8 | 5:8 2:8 | 0:16 | 3:8 5:8 | 7:6 5:2 3:8 | 6+:8 4:8 | 1:8 4:8")),
    "starfort": dict(name="星形の巨城", mood="壮麗な宮廷と攻城の緊迫（短調）。オルガン・弦・ティンパニ、竜は金管の行進", mode="aeolian", tonic=62, tempo=90,
        groove="baroque", bass="root4", counter="flow16",
        pal=dict(pad="organ", counter="harp", double="choir", doubleOctave=0, bassInst="bass", drive="strings", driveDrum="timpani", dragonPad="strings"),
        civ=dict(lead="organ", octave=12, chords="0m 4M 5M 2M 3m 0m 3m 4M",
                 theme="7:4 6+:4 7:8 | 8:8 4:8 | 5:4 7:4 9:8 | 6:6 4:2 2:8 | 3:4 5:4 7:8 | 9:6 7:2 4:8 | 5:8 3:8 | 4:4 6+:4 8:8"),
        dragon=dict(lead="brass", octave=-12, chords="0m 5M 6M 4M 0m 5M 6M 4M",
                    theme="0:4 2:4 4:4 7:4 | 5:8 2:8 | 6:6 3:2 1:8 | 6+:8 4:8 | 7:6 4:2 2:8 | 5:4 7:4 9:8 | 8:8 6:8 | 4:16")),
}

WARN = []


def deg_semi(mode, d, acc=0):
    sc = MODES[mode]
    n = len(sc)
    return sc[d % n] + 12 * (d // n) + acc


def parse_deg(tok):
    acc = 0
    while tok and tok[-1] in "+-" and len(tok) > 1 and not (tok[-1] == "-" and tok[:-1] == ""):
        acc += 1 if tok[-1] == "+" else -1
        tok = tok[:-1]
    return int(tok), acc


def parse_chord(tok):
    acc = 0
    if tok[0] in "b#":
        acc = -1 if tok[0] == "b" else 1
        tok = tok[1:]
    i = 0
    while i < len(tok) and tok[i].isdigit():
        i += 1
    return int(tok[:i]), acc, tok[i:]


def build_chord(mode, tonic, tok):
    d, acc, q = parse_chord(tok)
    root_rel = deg_semi(mode, d, acc)
    root_pc = (tonic + root_rel) % 12
    ivs = QUALITY[q]
    pcs = [(root_pc + iv) % 12 for iv in ivs]
    # 和音の音：上の3音を 60〜72 のあたりに（効果音・分散和音の高さの基準）
    tones = sorted({60 + ((pc - 60) % 12) for pc in pcs})[:3] if q != "p" else sorted({60 + ((pc - 60) % 12) for pc in pcs[:2]} | {60 + ((pcs[0] - 60) % 12) + 12})
    bass = 36 + ((root_pc - 36) % 12)
    if bass > 45:
        bass -= 12
    # 効果音の音階：旋法の音を基本に、和音の音を入れる（ラの長三和音ではド#）
    sc = [x for x in MODES[mode]]
    key_pc = tonic % 12
    rel = [(p - key_pc) % 12 for p in pcs]
    for r in rel:
        if r not in sc:
            near = min(range(len(sc)), key=lambda k: min(abs(sc[k] - r), 12 - abs(sc[k] - r)))
            sc[near] = r
    names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    return {"name": names[root_pc] + ({"m": "m", "M": "", "d": "dim", "p": "5", "s": "sus4", "7": "7", "m7": "m7", "M7": "maj7"}[q]),
            "root": bass, "tones": tones, "scale": sorted(set(sc)), "_pcs": pcs}


def build_theme(song_id, side, mode, tonic, spec, chords):
    bars = [b.strip() for b in spec["theme"].split("|")]
    if len(bars) != 8:
        raise SystemExit(f"{song_id}.{side}: 主題は8小節（{len(bars)}）")
    out = []
    for bi, b in enumerate(bars):
        notes, s = [], 0
        for tok in b.split():
            dt, ln = tok.split(":")
            ln = int(ln)
            if dt != "r":
                d, acc = parse_deg(dt)
                midi = tonic + deg_semi(mode, d, acc) + spec.get("octave", 0)
                notes.append([s, midi, ln])
                if s in (0, 8) and ln > 2 and (midi % 12) not in chords[bi]["_pcs"]:
                    WARN.append(f"{song_id}.{side} 小節{bi + 1} step{s}: {midi} が和音 {chords[bi]['name']} の音でない")
            s += ln
        if s != STEPS:
            raise SystemExit(f"{song_id}.{side} 小節{bi + 1}: 長さの合計 {s}（16 にする）")
        out.append(notes)
    # 楽器の鳴りのよい音域へオクターブ単位でずらす（和音の確かめは高さの種類だけなので、ずらしても変わらない）
    allm = [n[1] for bar in out for n in bar]
    shift = 12 * round((LEAD_CENTER[spec["lead"]] - sum(allm) / len(allm)) / 12)
    for bar in out:
        for n in bar:
            n[1] += shift
    return out


def drum_tracks(groove, band, prefix):
    tr = []
    for row in groove:
        inst, steps, acc, gain = row[:4]
        every = row[4] if len(row) > 4 else None
        offset = row[5] if len(row) > 5 else None
        pitched = row[6] if len(row) > 6 else False
        t = {"name": f"{prefix}{inst}", "inst": inst, "type": "drum", "gain": gain, "steps": steps, "accents": acc[:len(steps)], "band": band}
        if every:
            t["everyBars"] = every
            t["barOffset"] = offset if offset is not None else every - 1
        if pitched:
            t["pitchSteps"] = [0 if inst != "tom" else 7 - k * 2 for k in range(len(steps))]
            t["pitchFromRoot"] = -12 if inst == "timpani" else 0
        tr.append(t)
    return tr


def build_song(song_id, s):
    mode, tonic = s["mode"], s["tonic"]
    pal = s["pal"]
    song = {"name": s["name"], "_about": s["mood"], "tempo": s["tempo"], "key": tonic, "keyScale": MODES[mode]}
    if s.get("muffleHz"):
        song["muffleHz"] = s["muffleHz"]
    if s.get("fixedBand") is not None:
        song["fixedBand"] = s["fixedBand"]
    for side in ("civ", "dragon"):
        sp = s[side]
        chords = [build_chord(mode, tonic, t) for t in sp["chords"].split()]
        if len(chords) != 8:
            raise SystemExit(f"{song_id}.{side}: 和音は8小節")
        theme = build_theme(song_id, side, mode, tonic, sp, chords)
        for c in chords:
            del c["_pcs"]
        song[side] = {"lead": sp["lead"], "gain": LEAD_GAIN[sp["lead"]], "chords": chords, "theme": theme}
    # 強化・レベルアップのチャイム：竜の主題の最初の3音（オルゴールの高さへ）
    first = [n[1] for bar in song["dragon"]["theme"] for n in bar][:3]
    shift = 12 * round((62 - first[0]) / 12)   # sfxChime が chime.octave（12）を足して鳴らす
    song["motif"] = [m + shift for m in first]
    # 文明・竜が入れ替わったフレーズの頭の合図
    song["civ"]["enter"] = {"inst": "bell", "midi": tonic % 12 + 72, "gain": 0.08}
    song["dragon"]["enter"] = {"inst": "crash", "midi": 60, "gain": 0.06}
    tracks = []
    pad = pal["pad"]
    tracks.append({"name": "pad", "inst": pad, "type": "chord", "gain": PAD_GAIN[pad], "octave": -12, "attack": 0.35, "release": 0.8, "band": 0,
                   **({"side": "civ"} if pal.get("dragonPad") else {})})
    if pal.get("dragonPad"):
        dp = pal["dragonPad"]
        tracks.append({"name": "dragonPad", "inst": dp, "type": "chord", "gain": PAD_GAIN[dp], "octave": -12, "attack": 0.35, "release": 0.8, "band": 0, "side": "dragon"})
    tracks.append({"name": "theme", "type": "theme", "band": 0})
    bi = pal.get("bassInst", "bass")
    tracks.append({"name": "bass", "inst": bi, "type": "bass", "gain": BASS_GAIN[bi], "notes": BASS[s["bass"]], "band": 1})
    if s.get("groove"):
        tracks += drum_tracks(GROOVES[s["groove"]], 2, "")
    ci = pal["counter"]
    tracks.append({"name": "counter", "inst": ci, "type": "arp", "gain": COUNTER_GAIN[ci], "notes": COUNTER[s["counter"]], "band": 3,
                   "octave": 12 if ci in ("lute", "marimba", "pluck", "clav") else 0})
    dbl = pal["double"]
    tracks.append({"name": "double", "type": "theme", "inst": dbl, "gain": round(LEAD_GAIN.get(dbl, 0.08) * 0.7, 3),
                   "octave": pal.get("doubleOctave", -12), "band": 4})
    if s.get("groove"):
        tracks += drum_tracks(FULL, 4, "full_")
    # 壊している間のパート（destroy: 建物が続けて崩れている間だけ、その強さで鳴る）
    dv = pal["drive"]
    tracks.append({"name": "drive", "inst": dv, "type": "bass", "gain": 0.06 if dv == "strings" else 0.07, "octave": 24 if dv == "strings" else 36,
                   "notes": DRIVE, "destroy": True})
    dd = pal["driveDrum"]
    tracks.append({"name": "driveDrum", "inst": dd, "type": "drum", "gain": 0.14 if dd in ("taiko", "timpani") else 0.1,
                   "steps": [0, 4, 8, 10, 12], "accents": [1, 0.7, 0.9, 0.6, 0.8], "destroy": True,
                   **({"pitchSteps": [0, 0, 7, 7, 0], "pitchFromRoot": -12} if dd == "timpani" else {})})
    song["tracks"] = tracks
    return song


def main():
    music = json.load(open(MUSIC, encoding="utf-8"))
    keep = {k: music[k] for k in ("instruments", "_sfx", "sfx", "_mix", "voiceLimit") if k in music}
    for name in ("strings", "timpani", "taiko", "crumble"):
        keep["instruments"][name] = {"file": f"{name}.wav", "base": {"strings": 60, "timpani": 41, "taiko": 45, "crumble": 60}[name]}
    songs = {sid: build_song(sid, s) for sid, s in SONGS.items()}
    out = {
        "_about": ("Dragon Tide の曲と効果音の譜面（DT-624）。ゲームの小さなトラッカーが読む。音の高さは MIDI の番号（60＝ド4）。"
                   "step は16分音符の番号（1小節＝16）。songs は tools/gen_dt_music.py で書き出す（曲を作り直すときはそちらを直す）"),
        "stepsPerBar": STEPS,
        "_songs": ("DT-624 手直し8（11/27）：1地域1曲（キーは STAGE_SHAPES の id。タイトル画面は title）。曲ごとに tempo・key・keyScale、"
                   "civ（文明の主題）と dragon（竜の主題）のそれぞれに lead（主題の楽器）・chords（8小節）・theme（8小節。[step, 高さ, 長さ]）、"
                   "tracks（伴奏。band＝鳴らし始める楽団の段、side＝その側のフレーズだけ、destroy＝壊している間だけ。type は chord・arp・bass・drum・theme）"),
        "songs": songs,
        "phraseBars": 4,
        "_band": ("楽団の段（0〜4）。攻略の進み具合（壊した街の割合）が thresholds を越えるごとに1段上がり、その段までの tracks が鳴る"
                  "（0＝和音の床と主題・1＝低音・2＝刻み・3＝対旋律・4＝主題の重ねと節目）。首都を落とすと最後の段。段はフレーズの頭でだけ変わる"),
        "band": {"thresholds": [0, 0.12, 0.3, 0.55, 0.8]},
        "_tug": ("文明の主題と竜の主題の綱引き。フレーズ（phraseBars 小節）ごとにどちらか一方の主題を弾く。竜の側に回す割合は進み具合で start → end。"
                 "首都を落とすと竜の側だけ。calls＝出来事（警戒度アップ・大きな進化・首都の陥落）で、次から竜の側にするフレーズの数"),
        "tug": {"start": 0.25, "end": 1.0, "calls": {"alert": 1, "evolve": 1, "capitalFall": 2}},
        "_destroy": ("壊している間のパート（tracks の destroy）。崩れた建物の数を windowSec 秒の窓でならし、fullCount 棟で最大。"
                     "minLevel より小さいときは鳴らさない（1棟崩れただけでは入らない）。attackSec でふくらみ、releaseSec で引く"),
        "destroy": {"windowSec": 1.5, "fullCount": 6, "minLevel": 0.25, "attackSec": 0.4, "releaseSec": 2.0},
    }
    out.update(keep)
    # 崩壊は曲に組み込まない（11/27 Shooter「破壊音は破壊音で SE として」）。拍に寄せず、崩れる音をそのまま鳴らす
    out["sfx"]["collapse"] = {"inst": "crumble", "gain": 0.16, "pitches": [0, -3, -5, -1, -4, -2], "minGapSec": 0.035}
    out["_sfx"] = ("効果音。要所の単発（陥落・警戒度・レベルアップのチャイム・卵・線を引く音と薙ぎの和音）は次の16分音符の格子に寄せ、高さはその時の和音から選ぶ。"
                   "建物の崩壊（collapse）は曲に組み込まず、崩れる音をすぐ鳴らす（高さは pitches を順に回す。ゲームの乱数は使わない）")
    json.dump(out, open(MUSIC, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"songs {len(songs)} → {MUSIC}")
    for w in WARN:
        print("注意:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
