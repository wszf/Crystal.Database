# -*- coding: utf-8 -*-
"""Translate Configs/*.ini and the player-facing notice files."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

WORK = Path("/tmp/task357/work")
JEV = lib.JEV
CONFIGS = JEV / "Configs"

MONSTER_KEYS = {
    "SkeletonName", "BugBatName", "ShinsuName", "Zuma1", "Zuma2", "Zuma3", "Zuma4",
    "Zuma5", "Zuma6", "Zuma7", "Turtle1", "Turtle2", "Turtle3", "Turtle4", "Turtle5",
    "BoneMonster1", "BoneMonster2", "BoneMonster3", "BoneMonster4",
    "BehemothMonster1", "BehemothMonster2", "BehemothMonster3",
    "HellKnight1", "HellKnight2", "HellKnight3", "HellKnight4",
    "HellBomb1", "HellBomb2", "HellBomb3",
    "GeneralMeowMeowMob1", "GeneralMeowMeowMob2", "GeneralMeowMeowMob3", "GeneralMeowMeowMob4",
    "KingHydraxMob", "HornedCommanderMob", "HornedCommanderBombMob", "SnowWolfKingMob",
    "ScrollMob1", "ScrollMob2", "ScrollMob3", "ScrollMob4", "WhiteSnake",
    "AngelName", "BombSpiderName", "CloneName", "FishMonster", "AssassinCloneName",
    "VampireName", "ToadName", "SnakeTotemName", "SnakesName", "StoneName",
    "AncientBatName", "TucsonGeneralEgg",
}
ITEM_VALUE_KEYS = {"ItemName", "SealItemName", "OreName", "CreatureBlackStoneName"}

LANGUAGE = {
    "Welcome": "欢迎来到{0}服务器。",
    "OnlinePlayers": "在线玩家：{0}",
    "LowLevel": "你的等级不足。",
    "LowGold": "金币不足。",
    "LowDC": "你的攻击力不足。",
    "LowMC": "你的魔法力不足。",
    "LowSC": "你的道术不足。",
    "LevelUp": "恭喜！你升级了，生命值和魔法值已恢复。",
    "WeaponLuck": "幸运降临在你的武器上。",
    "WeaponCurse": "诅咒缠绕着你的武器。",
    "WeaponNoEffect": "没有效果。",
    "InventoryIncreased": "背包容量已增加。",
    "ExpandedStorageExpiresOn": "扩展仓库到期时间",
    "GameName": "传奇2",
    "FaceToTrade": "你必须面向对方才能交易。",
    "NoTownTeleport": "此处无法使用回城卷。",
    "CanNotRandom": "此处无法使用随机传送。",
    "CanNotDungeon": "此处无法使用地牢逃脱卷。",
    "CannotResurrection": "存活时无法使用复活卷轴。",
    "CanNotDrop": "此地图无法丢弃物品。",
    "NotFemale": "你不是女性。",
    "NotMale": "你不是男性。",
    "NotInGuild": "你不在任何公会中。",
    "NewMail": "你有新邮件。",
    "CouldNotFindPlayer": "找不到玩家 {0}",
    "NoMentorship": "你目前没有可取消的师徒关系。",
    "AllowingMentorRequests": "你已允许拜师请求。",
    "BlockingMentorRequests": "你已屏蔽拜师请求。",
    "NoBagSpace": "你的背包空间不足。",
}

MINES = {"BichonMines": "比奇矿区", "MineralMines": "矿场矿区"}

GUILD_BUFFS = {
    "Reputation": "声望",
    "Specialized Crafter": "打造专精",
    "Specialized Miner": "采矿专精",
    "Gem Success Rate": "宝石成功率",
    "Specialized Fisher": "钓鱼专精",
    "Skill Experiance": "技能经验",
    "Field Experience": "打怪经验",
    "Hero Experience": "英雄经验",
    "Max Health": "最大生命",
    "Max Mana": "最大魔法",
    "Physical Defence": "物理防御",
    "Health Recovery": "生命恢复",
    "Mana Recovery": "魔法恢复",
    "Guild House Rate": "公会房屋产出率",
    "Physical Damage": "物理伤害",
    "Magic Defence": "魔法防御",
}


class Resolver:
    def __init__(self):
        jev = json.loads((Path("/tmp/task357/Jev.json")).read_text(encoding="utf-8"))
        self.item_zh = {int(k): v for k, v in lib.load("item_names.json").items()}
        self.mon_zh = {int(k): v for k, v in lib.load("monster_names.json").items()}
        self.item_by = {norm(x["name"]): x["index"] for x in jev["items"]}
        self.mon_by = {norm(x["name"]): x["index"] for x in jev["monsters"]}

    def item(self, token):
        idx = self.item_by.get(norm(token))
        return self.item_zh.get(idx) if idx is not None else None

    def mon(self, token):
        idx = self.mon_by.get(norm(token))
        return self.mon_zh.get(idx) if idx is not None else None


def norm(s):
    return re.sub(r"\s+", "", s).lower()


def rewrite_ini(path: Path, fn, stats):
    original = path.read_text(encoding="utf-8")
    out = []
    changed = 0
    for line in original.splitlines():
        stripped = line.strip()
        if not stripped or stripped[0] in ";#[" or "=" not in line:
            out.append(line)
            continue
        key, value = line.split("=", 1)
        new = fn(key.strip(), value)
        if new != value:
            changed += 1
            out.append(f"{key}={new}")
        else:
            out.append(line)
    text = "\n".join(out)
    if original.endswith("\n"):
        text += "\n"
    if text != original:
        path.write_text(text, encoding="utf-8")
    stats[path.name] = changed


def main():
    r = Resolver()
    stats = {}
    last_section = {"name": ""}

    def generic(key, value):
        if key in MONSTER_KEYS:
            new = r.mon(value.strip())
            return new or value
        if key in ITEM_VALUE_KEYS:
            new = r.item(value.strip())
            return new or value
        return value

    for path in sorted(CONFIGS.iterdir()):
        # HeroConfig.info is a binary hero table, not an INI file.
        if path.suffix.lower() != ".ini":
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if path.name == "Language.ini":
            rewrite_ini(path, lambda k, v: LANGUAGE.get(k, v), stats)
        elif path.name == "Mines.ini":
            def mines(k, v, _path=path):
                if k == "Name":
                    return MINES.get(v.strip(), v)
                if k.endswith("-ItemName"):
                    return r.item(v.strip()) or v
                return v
            rewrite_ini(path, mines, stats)
        elif path.name == "FishingSystem.ini":
            def fishing(k, v):
                if k == "Monster":
                    return r.mon(v.strip()) or v
                return v
            rewrite_ini(path, fishing, stats)
        elif path.name == "GuildSettings.ini":
            def guild(k, v):
                if k == "Name":
                    return GUILD_BUFFS.get(v.strip(), v)
                if k == "ItemName":
                    return r.item(v.strip()) or v
                return v
            rewrite_ini(path, guild, stats)
        else:
            rewrite_ini(path, generic, stats)

    # Player-facing notices use "(visible/url)" markup.
    for name in ("Notice.txt", "LoginNotice.txt"):
        path = JEV / "Envir" / name
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        out = []
        for line in original.splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("TITLE="):
                out.append("TITLE=欢迎来到《传奇2》")
                continue
            out.append(translate_notice(line))
        text = "\n".join(out)
        if original.endswith("\n"):
            text += "\n"
        path.write_text(text, encoding="utf-8")
        stats[name] = 1

    path = JEV / "Envir" / "LineMessage.txt"
    if path.exists():
        path.write_text(
            "欢迎来到 Suprcode 发布的 Crystal Mir 2。\n"
            "请关注 JevLomcn 的 GitHub 以获取最新的数据库版本。\n"
            "www.LOMCN.net\n"
            "现已支持 .NET 8\n",
            encoding="utf-8",
        )
        stats["LineMessage.txt"] = 1

    print(json.dumps(stats, ensure_ascii=False, indent=1))


NOTICE = {
    "Welcome to Legend of Mir 2": "欢迎来到《传奇2》",
    "!!MUST READ!!": "!!必读!!",
    "By clicking close and continuing to play the": "点击关闭并继续游戏，即表示你同意",
    "game you are agreeing to the terms of": "以下服务条款。",
    "service above.": "",
}
NOTICE_EXTRA = {"LOMCN": "LOMCN", "DATABASE": "数据库"}


def translate_notice(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return line

    def repl(m):
        vis, url = m.group(1), m.group(2)
        return f"({NOTICE.get(vis, NOTICE_EXTRA.get(vis, vis))}/{url})"

    new = re.sub(r"\(([^()]*)/([^()]*)\)", repl, stripped)
    if stripped in NOTICE:
        new = NOTICE[stripped]
    elif new == stripped:
        text = NOTICE.get(stripped, stripped)
        new = text
    return new


if __name__ == "__main__":
    main()
