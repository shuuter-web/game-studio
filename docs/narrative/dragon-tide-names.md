# Dragon Tide 名前の表（竜種・特殊個体・敵・強化カード・アーティファクト・地域）

ゲームの版 v3.225.0 から `node tools/dt-names.mjs` で作った写し（案帳 DT-635）。名前の正本はコード（STRINGS・SPECIES_DEFS・CODEX_*）。名前を変えたら作り直す。
「図鑑」は図鑑の各ページを組み立てて、その文字の中に画面の名前があるかで見ている。× は図鑑に載っていないもの。

## 竜種（27）

| 内部の名前 | 画面の名前 | 英語 | 説明 | 図鑑 |
|---|---|---|---|---|
| fire | 火竜 | Fire Dragon | ○ | ○ |
| ice | 氷竜 | Ice Dragon | ○ | ○ |
| shadow | 影竜 | Shadow Dragon | ○ | ○ |
| crimson | 緋竜 | Crimson Dragon | ○ | ○ |
| falcon | 隼竜 | Falcon Dragon | ○ | ○ |
| swallow | 燕竜 | Swallow Dragon | ○ | ○ |
| hornet | 蜂竜 | Hornet Dragon | ○ | ○ |
| gargoyle | ガーゴイル | Gargoyle | ○ | ○ |
| ufo | UFO | Saucer | ○ | ○ |
| comet | 彗星竜 | Comet Dragon | ○ | ○ |
| bomber | 爆竜 | Bomber Dragon | ○ | ○ |
| wayward | 惑竜 | Wayward Dragon | ○ | ○ |
| frog | 蛙竜 | Frog Dragon | ○ | ○ |
| shark | 鮫竜 | Shark Dragon | ○ | ○ |
| tortoise | 亀竜 | Tortoise Dragon | ○ | ○ |
| thunder | 雷雲竜 | Thunderhead Dragon | ○ | ○ |
| ball | 塊竜 | Clump Dragon | ○ | ○ |
| mole | 土竜 | Mole Dragon | ○ | ○ |
| magnet | 磁竜 | Magnet Dragon | ○ | ○ |
| twin | 双子竜 | Twin Dragon | ○ | ○ |
| wisp | 鬼火 | Will-o'-Wisp | ○ | ○ |
| flail | 鉄鎖竜 | Flail Dragon | ○ | ○ |
| whale | 鯨竜 | Whale Dragon | ○ | ○ |
| wyvern | 飛竜 | Wyvern | ○ | ○ |
| cannon | 砲撃竜 | Bombard Dragon | ○ | ○ |
| ray | 光線竜 | Laser Dragon | ○ | ○ |
| bone | 屍竜 | Bone Dragon | ○ | ○ |

## 特殊個体（23）

| 内部の名前 | 画面の名前 | 説明 | 図鑑 |
|---|---|---|---|
| beacon | 光剣 | **×** | ○ |
| heavy | 止まらぬ鉄塊 | **×** | ○ |
| deflect | 暴食 | **×** | ○ |
| rainbow | 極光 | **×** | ○ |
| mecha | ロケットマン | **×** | ○ |
| wake | 煽る風 | **×** | ○ |
| wedge | 穿つ楔 | **×** | ○ |
| heal | 癒し手 | **×** | ○ |
| frost | 凍て霧 | **×** | ○ |
| laser | 天穿 | **×** | ○ |
| chain | 鉄鎖 | **×** | ○ |
| drum | 軍鼓 | **×** | ○ |
| link | 結び竜 | **×** | **×** |
| aim | 狙い火 | **×** | ○ |
| recall | 還る槍 | **×** | ○ |
| hush | 口封じ | **×** | ○ |
| shell | 籠る殻 | **×** | **×** |
| bundle | 束ね陣 | **×** | **×** |
| scatter | 広げ陣 | **×** | **×** |
| skybow | 虹弓 | **×** | ○ |
| barrier | 結界線 | **×** | ○ |
| dice | 賽振り | **×** | **×** |
| broadside | 右舷砲 | **×** | ○ |

## 敵（96）

| 内部の名前 | 画面の名前（図鑑） | デバッグの名札 | 図鑑 |
|---|---|---|---|
| mammoth | マンモス | マンモス | ○ |
| colossus | コロッサス | コロッサス | ○ |
| knights | 騎士団 | 騎士団 | ○ |
| ironclad | 陸上甲鉄艦 | 陸上甲鉄艦 | ○ |
| balloon | 爆撃気球 | 爆撃気球 | ○ |
| harpoon_knight | 竜狩りの騎士 |  | ○ |
| moving_fortress | 動く砦 | 動く砦 | ○ |
| stone_titan | 岩脚の巨像 | 岩脚の巨像 | ○ |
| rock_giant | 岩の巨人 | 岩の巨人 | ○ |
| fortress_turret | 動く砦の砲台 |  | ○ |
| war_elephant | 戦象 | 戦象 | ○ |
| war_elephant_rider | 戦象の弓兵 |  | ○ |
| prism_bearer | プリズム運び | プリズム運び | ○ |
| scythe_chariot | 鎌付き戦車 | 鎌付き戦車 | ○ |
| scythe_convoy | 鎌付き戦車の車列 | 鎌付き戦車の車列 | ○ |
| eater_flower | 竜食い花 | 竜食い花 | ○ |
| seed_flower | 種を飛ばす花 | 種を飛ばす花 | ○ |
| pollen_flower | 花粉の花 | 花粉の花 | ○ |
| hive_flower | 巣の花 | 巣の花 | ○ |
| flower_bee | 花蜂 | 花蜂 | ○ |
| flower_sprout | 花の芽 | 花の芽 | ○ |
| queen_petal | 女王花の花びら | 女王花の花びら | ○ |
| bomb_batter | 打ち返す兵 | 打ち返す兵 | ○ |
| bomb_roller | 玉転がしの兵 | 玉転がしの兵 | ○ |
| hero_shield | 盾投げの騎士 |  | ○ |
| hero_mage | 大魔法使い |  | ○ |
| hero_archer | 英雄の弓手 |  | ○ |
| longbowmen | 遠矢の弓隊 | 遠矢の弓隊 | ○ |
| troop_airship | 落下兵の飛行船 | 落下兵の飛行船 | ○ |
| paratrooper | 落下兵 |  | ○ |
| ring_rider | 輪乗りの騎兵 |  | ○ |
| blast_rock | 爆ぜ岩 |  | ○ |
| wind_rider | 風乗りの兵 | 風乗りの兵 | ○ |
| sky_carrier | 浮き砦 | 浮き砦 | ○ |
| sky_mine | 浮き機雷 | 浮き機雷 | ○ |
| serpent_coil | 町を巻く大蛇 |  | ○ |
| serpent_god | 蛇神 |  | ○ |
| sword_runner | 剣士 | 剣士 | ○ |
| sword_charger | 突進の剣士 | 突進の剣士 | ○ |
| sword_militia | 足軽 | 足軽 | ○ |
| sword_brute | 大太刀 | 大太刀 | ○ |
| sword_beast | 剣の巨獣 | 剣の巨獣 | ○ |
| serpent_spitter | 毒吐き蛇 | 毒吐き蛇 | ○ |
| serpent_crawl | 這い大蛇 | 這い大蛇 | ○ |
| kite_soldier | 雷凧の兵 | 雷凧の兵 | ○ |
| rush_gate | 湧き出る門 |  | ○ |
| raider | レイダー | レイダー | ○ |
| warlord | ウォーロード | ウォーロード | ○ |
| shockman | 衝撃兵 | 衝撃兵 | ○ |
| healer | 治癒塔 | 治癒塔 | ○ |
| summoner | 召喚門 | 召喚門 | ○ |
| behemoth_core | 巨獣（コア） | 巨獣 | ○ |
| behemoth_arm | 巨獣の腕 | 巨獣の腕 | ○ |
| shieldman | 鏡の盾兵 | 鏡の盾兵 | ○ |
| splitter | 分裂体 | 分裂体 | ○ |
| splitter_mid | 分裂体（中） | 分裂体 | ○ |
| splitter_small | 分裂体（小） | 分裂体 | ○ |
| lurker | 潜行者 | 潜行者 | ○ |
| teslawagon | 雷撃塔車 | 雷撃塔車 | ○ |
| flamewagon | 火吹き車 | 火吹き車 | ○ |
| miasma | 瘴気塔 | 瘴気塔 | ○ |
| clubmen | 石打ちの衆 | 石打ちの衆 | ○ |
| bullchariot | 牡牛戦車 | 牡牛戦車 | ○ |
| batteringram | 破城槌 | 破城槌 | ○ |
| grapeshot | 散弾砲車 | 散弾砲車 | ○ |
| steamhammer | 蒸気打鉄 | 蒸気打鉄 | ○ |
| repulsor | 反発塔車 | 反発塔車 | ○ |
| concussion | 衝撃砲 | 衝撃砲 | ○ |
| gravitygun | 重力砲 | 重力砲 | ○ |
| mammoth_lord | 長牙のマンモス | 長牙のマンモス | ○ |
| gilded_colossus | 黄金の巨像 | 黄金の巨像 | ○ |
| siegetower | 攻城塔 | 攻城塔 | ○ |
| grenadiers | 擲弾兵隊 | 擲弾兵隊 | ○ |
| armortrain | 装甲列車 | 装甲列車 | ○ |
| teslagiant | 雷公 | 雷公 | ○ |
| bomberwing | 爆撃飛行隊 | 爆撃飛行隊 | ○ |
| annihilator | 殲滅砲兵 | 殲滅砲兵 | ○ |
| walker_hull | 多脚戦車 | 多脚戦車 | ○ |
| walker_leg | 多脚戦車の脚 | 多脚戦車の脚 | ○ |
| railgun_loco | 列車砲列（機関車） | 列車砲列 | ○ |
| railgun_tail |  |  | **×** |
| railgun_car | 列車砲列の砲車 | 列車砲列の砲車 | ○ |
| railcar | 装甲軌道車 | 装甲軌道車 | ○ |
| railram | 衝角機関車 | 衝角機関車 | ○ |
| forest_ambusher | 森の伏兵 | 森の伏兵 | ○ |
| forest_giant | 森番の巨人 | 森番の巨人 | ○ |
| metro_car | 渋滞の車 | 渋滞の車 | ○ |
| metro_truck | 渋滞の箱バン | 渋滞の箱バン | ○ |
| metro_police | パトカー | パトカー | ○ |
| metro_tank | 戦車 | 戦車 | ○ |
| hero |  |  | **×** |
| metro_heli | 攻撃ヘリ | 攻撃ヘリ | ○ |
| treasure | 財宝馬車 | 財宝馬車 | ○ |
| caravan | 行商の隊 | 行商の隊 | ○ |
| caravan_guard | 行商の隊の護衛 | 行商の隊の護衛 | ○ |
| eggconvoy | 竜卵の輸送隊 |  | ○ |

## 強化カード・アーティファクト（図鑑の強化カード）（29）

| 内部の名前 | 種類 | 画面の名前 | 説明 | 図鑑 |
|---|---|---|---|---|
| scale | アーティファクト | 硬鱗 | ○ | ○ |
| tide | アーティファクト | 再生の潮 | ○ | ○ |
| magnet | アーティファクト | 吸引域 | ○ | ○ |
| resonance | アーティファクト | 竜鱗共鳴 | ○ | ○ |
| cat_direct | アーティファクト | 直撃の牙 | ○ | ○ |
| cat_shot | アーティファクト | 烈火の喉 | ○ | ○ |
| cat_blast | アーティファクト | 爆ぜる心臓 | ○ | ○ |
| fsp_direct | アーティファクト | 特殊個体の牙 | ○ | ○ |
| fsp_shot | アーティファクト | 特殊個体の喉 | ○ | ○ |
| fsp_impact | アーティファクト | 特殊個体の膂力 | ○ | ○ |
| fsp_hp | アーティファクト | 特殊個体の鱗 | ○ | ○ |
| fsp_revive | アーティファクト | 特殊個体の再起 | ○ | ○ |
| fsp_more | アーティファクト | 連れ合い | ○ | ○ |
| f_rush | アーティファクト | 逆襲の血 | ○ | ○ |
| f_egg_power | アーティファクト | 卵の力 | ○ | ○ |
| f_fall_roar | アーティファクト | 陥落の咆哮 | ○ | ○ |
| f_triumph | アーティファクト | 凱旋 | ○ | ○ |
| f_egg_wave | アーティファクト | 孵化の衝撃 | ○ | ○ |
| f_salute | アーティファクト | 祝砲 | ○ | ○ |
| f_dice | アーティファクト | 博打の賽 | ○ | ○ |
| f_giant | アーティファクト | 巨竜化 | ○ | ○ |
| f_rage | アーティファクト | 逆鱗 | ○ | ○ |
| f_lance | アーティファクト | 一番槍 | ○ | ○ |
| f_call | アーティファクト | 親竜の呼び声 | ○ | ○ |
| f_shell | アーティファクト | 籠る殻 | ○ | ○ |
| f_bundle | アーティファクト | 束ね陣 | ○ | ○ |
| f_scatter | アーティファクト | 広げ陣 | ○ | ○ |
| f_ebb | アーティファクト | 退き潮 | ○ | ○ |
| f_heat | アーティファクト | いきり立つ血 | ○ | ○ |

## レベルアップのカード（CARD_DEFS）（25）

| 内部の名前 | 種類 | 画面の名前 | 説明 | 図鑑 |
|---|---|---|---|---|
| scale | レベルアップのカード | 硬鱗 | ○ | ○ |
| tide | レベルアップのカード | 再生の潮 | ○ | ○ |
| magnet | レベルアップのカード | 吸引域 | ○ | ○ |
| brood | レベルアップのカード | 大繁殖 | ○ | **×** |
| resonance | レベルアップのカード | 竜鱗共鳴 | ○ | ○ |
| cat_direct | レベルアップのカード | 直撃の牙 | ○ | ○ |
| cat_shot | レベルアップのカード | 烈火の喉 | ○ | ○ |
| cat_blast | レベルアップのカード | 爆ぜる心臓 | ○ | ○ |
| sp_rainbow | 特殊個体を加える | 極光 | ○ | ○ |
| sp_beacon | 特殊個体を加える | 光剣 | ○ | ○ |
| sp_heavy | 特殊個体を加える | 止まらぬ鉄塊 | ○ | ○ |
| sp_deflect | 特殊個体を加える | 暴食 | ○ | ○ |
| sp_mecha | 特殊個体を加える | ロケットマン | ○ | ○ |
| sp_wake | 特殊個体を加える | 煽る風 | ○ | ○ |
| sp_wedge | 特殊個体を加える | 穿つ楔 | ○ | ○ |
| sp_heal | 特殊個体を加える | 癒し手 | ○ | ○ |
| sp_frost | 特殊個体を加える | 凍て霧 | ○ | ○ |
| sp_chain | 特殊個体を加える | 鉄鎖 | ○ | ○ |
| sp_drum | 特殊個体を加える | 軍鼓 | ○ | ○ |
| sp_aim | 特殊個体を加える | 狙い火 | ○ | ○ |
| sp_recall | 特殊個体を加える | 還る槍 | ○ | ○ |
| sp_hush | 特殊個体を加える | 口封じ | ○ | ○ |
| sp_barrier | 特殊個体を加える | 結界線 | ○ | ○ |
| sp_skybow | 特殊個体を加える | 虹弓 | ○ | ○ |
| sp_broadside | 特殊個体を加える | 右舷砲 | ○ | ○ |

## 地域（21）

| 内部の名前 | 画面の名前 | 図鑑 |
|---|---|---|
| continent | 大陸 | ○ |
| riverline | 大河の線状都市 | ○ |
| citadel | 同心円の城塞都市 | ○ |
| frontline | 長城の防衛線 | ○ |
| sanctuary | 四方の祠の結界 | ○ |
| asteroids | 漂う岩塊の小惑星帯 | ○ |
| railway | 無人列車の走る軌道 | ○ |
| forest | 森に覆われた大樹海 | ○ |
| metro | 車列の流れる大都会 | ○ |
| plateau | 光線の塔が立つ高原 | ○ |
| heroland | 英雄が守る王国 | ○ |
| wasteland | 巨岩を拝む荒地 | ○ |
| skyland | 雲海に浮かぶ浮き城の空 | ○ |
| serpent | 蛇神を祀る密林の国 | ○ |
| swordway | 剣の道の国 | ○ |
| mushroom | 増えるキノコの里 | ○ |
| bombland | 爆弾玉の国 | ○ |
| flowergarden | 竜食い花の園 | ○ |
| beach | 宿借りの浜 | ○ |
| beacon | 烽火の連なる丘陵 | ○ |
| starfort | 星形の巨城 | ○ |

## そろっていない所

- 特殊個体：結び竜（link）が図鑑に無い
- 特殊個体：籠る殻（shell）が図鑑に無い
- 特殊個体：束ね陣（bundle）が図鑑に無い
- 特殊個体：広げ陣（scatter）が図鑑に無い
- 特殊個体：賽振り（dice）が図鑑に無い
- 敵：（名前なし）（railgun_tail）に画面の名前が無い
- 敵：（名前なし）（hero）に画面の名前が無い
- レベルアップのカード（CARD_DEFS）：大繁殖（brood）が図鑑に無い
