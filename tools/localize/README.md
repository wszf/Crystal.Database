# Jev 简体中文本地化管线

把 `Jev/`（官方英文数据库，`Server.MirDB` 版本 111/0）转换为简体中文，并在不改动任何
结构标识（索引、文件名、路径、脚本命令、`@目标`、`<$变量>`、颜色名）的前提下同步
`Envir/` 与 `Configs/` 里的全部交叉引用。

英文原件保存在 `wszf/english-baseline` 分支。本目录只包含可重复运行的脚本与词典，
所有译文都按 **记录索引** 映射（英文名 → 中文名），因此一个英文引用永远指向它原本
指向的那条记录。

## 输入

| 文件 | 说明 |
|---|---|
| `data/english_catalog.json` | 从英文基线 `Server.MirDB` 解析出的完整导出（索引、英文名、掉落路径、任务、商店等），是索引映射的唯一依据 |
| `data/item_names.json` / `monster_names.json` / `map_titles.json` / `npc_names.json` / `quest_names.json` / `skill_names.json` | 逐索引译本表（1628 / 555 / 463 / 375 / 154 / 111） |
| `data/tm.json` | 翻译记忆：`label`（界面/链接标签）、`line`（NPC 对话行）、`quest`（任务段落） |
| `data/label_fixes.json` / `label_extra.json` | 人工校订的标签 |
| `data/label_tm.json` → `data/name_lookup.json` | 由标签 + 名录合成的最终标签查找表（含 `'s` 所有格形式） |
| `data/tooltip_fixes.json` / `tooltip_cj.json` / `tooltip_model.json` | 物品说明（`ItemInfo.ToolTip`）人工/模型译稿 |
| `data/quest_messages.json` | 任务 `goto/kill/item/flagMessage` 译稿 |

## 运行（从英文基线开始）

```bash
# 1. 恢复英文原件（在 Crystal.Database 仓库根目录）
git checkout english-baseline -- Jev     # 或 rsync 一份英文基线

cd tools/localize
python3 apply.py                  # 脚本正文/掉落/配方/任务 + 重命名掉落与配方文件
python3 post_fixes.py             # 修复原件中残缺的 {颜色} 标记
python3 clean_markers.py          # 清除模型产生的 [[...]] 标记、修正个别残留英文
python3 restore_variables.py      # 把 <$变量> 强制还原为原文（应为 0 处）
python3 resolve_markup_labels.py  # 解析剩余英文链接/颜色标签（应为 0 处未解析）
python3 audit_markup.py           # 校验 @目标/颜色多重度未变（必须 0 drift）
python3 audit_text.py             # 列出可见文本中仍为英文的片段（应只剩术语缩写）
python3 apply_configs.py          # Configs/*.ini、Language.ini、Notice/LoginNotice/LineMessage
python3 prepare_db.py             # 生成 /tmp/task357/final/Jev_final.json（Server.MirDB 载荷）
```

`apply.py` 的统计（`/tmp/task357/work/apply_report.json`）应满足：
`quest_kill_missing`、`drop_missing`（指英文原件中本来就不存在的记录）之外无新增缺失；
`renamed` = 106（`DropPath` 为空、以怪物名定位掉落文件的怪物数）。

## 写回 `Server.MirDB`

`Server.MirDB` 必须保持 **111/0** 版本（上游 Jev 的版本），不能让 117 版本的写入器
补写新字段。用 Go 侧的 v111 写入器：

```bash
cp tools/localize/go/zz_task357_tool_test.go \
   ../Crystal.GoServer/internal/legacyworld/          # 临时放入，用完删除
cd ../Crystal.GoServer
T357_MODE=writev111 T357_DIR=<...>/Crystal.Database/Jev \
  T357_INPUT=/tmp/task357/final/Jev_final.json \
  go test ./internal/legacyworld -run TestTask357 -count=1
rm internal/legacyworld/zz_task357_tool_test.go
```

同一辅助程序还提供：
`T357_MODE=roundtrip111`（写回后重新解析并逐字段比对）、
`T357_MODE=export`（导出 `ExportDirectory` 结果，用于与英文基线对比）、
`T357_MODE=dump`（重新生成 `english_catalog.json` 这类导出）。

## 不可破坏的约束

* `MapInfo.FileName`、`NoReconnectMap`、`MonsterInfo.DropPath`、`NPCInfo.FileName`、
  `QuestDatabaseRecord.FileName`、`MagicInfo.Name`（技能按英文名查找）、
  `GameShopItem.Class`（客户端按 `All/Warrior/...` 字面量比较）永不翻译。
* `ItemInfo.Name`、`MonsterInfo.Name` 全局唯一且不含空白：掉落、配方、商店都按
  名字（去空格、忽略大小写）解析。
* `DropPath` 为空的怪物，其掉落文件按怪物名查找，因此文件必须随 `MonsterInfo.Name`
  一起重命名；其余怪物的掉落文件路径不变。
* 掉落文件里的 `Gold`、`GROUP`、`LV1`… 与配方里的 `Amount/Chance/Gold` 是关键字，
  保持英文。
* 脚本里的 `#IF/#ACT/#SAY`、`GOTO`、`@目标`、`<$变量>`、颜色名（`/Crimson` 等）保持原样；
  只翻译可见文本与物品/怪物引用。

## 已知的原件缺陷（保持与英文一致，不擅自修复）

* `Envir/Quests/HolySword/8.txt` 的 `EvilHeart`、`Wasteland/Red Cave/2.txt` 的
  `BoxofHolyWater(1)`、`PrajnaIsland/PIVillage/1.txt` 的 `BoxofHolyWater(3)`
  指向目录中不存在的记录（英文原件同样无法解析），保留英文。
* `Configs/Mines.ini` 的 `PlatinumOre/RubyOre/NephriteOre/AmethystOre`、
  `Setup.ini` 的 `AncientBatName/TucsonGeneralEgg` 同样没有对应记录。
* 部分 NPC `[Trade]` 条目（如 `Amulet(M)`、`PheenixBead`）引用了目录中不存在的物品，
  英文原件也会跳过；本次仅翻译可解析的条目，因此 NPC 商品数量与英文完全一致。
