# -*- coding: utf-8 -*-
"""Build the translated Server.MirDB payload (dump JSON) for the Go writer."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

WORK = lib.WORK
OUT = lib.OUT

MANUAL_NPC = {
    "bradly": "布拉德利",
    "mongchon": "盟重",
    "vincents": "文森特",
    "ann": "安",
    "han": "韩",
    "charleys": "查理",
    "mastershok": "肖克师傅",
    "lostsoul": "迷失灵魂",
    "mogu": "莫古",
}

MESSAGE_OVERRIDES = {
    "106:gotoMessage": "返回地下城南区1层的迷失灵魂 (202:204)",
}

# Game shop tab titles.  GameShopItem.Class must stay English ("All",
# "Warrior", ...) because the client compares it against those literals, but
# Category is only a display/filter label, so it is localized.
SHOP_CATEGORIES = {
    "Potion": "药水",
    "Transform": "变身",
    "Special": "特殊",
    "Scroll": "卷轴",
    "Mount": "坐骑",
    "Torch": "火把",
    "Creature": "召唤兽",
    "Fishing": "钓鱼",
    "Package": "礼包",
}


def norm(s):
    return re.sub(r"\s+", "", s).lower()


class Fixer:
    def __init__(self, jev):
        self.npc_zh = {int(k): v for k, v in lib.load("npc_names.json").items()}
        self.part = {}
        self.full = {}
        for npc in jev["npcs"]:
            en = npc["name"]
            zh = self.npc_zh[npc["index"]]
            self.full[norm(en)] = zh
            eparts = [p for p in re.split(r"[_\s]+", en) if p]
            zparts = zh.split("_")
            if len(zparts) != len(eparts):
                zparts = re.split(r"[_\s]+", zh)
            if len(zparts) != len(eparts):
                continue
            for i, part in enumerate(eparts):
                self.part.setdefault(part.lower(), zparts[i])
        self.part.update(MANUAL_NPC)
        self.labels = dict(lib.load("name_lookup.json"))
        self.label_re = re.compile(
            r"(?<![A-Za-z0-9])(?:" + "|".join(
                re.escape(k) for k in sorted(self.labels, key=len, reverse=True)
                if lib.has_words(k)) + r")(?![A-Za-z0-9])"
        )
        self.token_re = re.compile(r"[A-Za-z][A-Za-z._]{1,}")

    def fix(self, text: str) -> str:
        def repl(m):
            tok = m.group(0)
            key = norm(tok)
            if key in self.full:
                return self.full[key]
            low = tok.lower()
            if low in self.part:
                return self.part[low]
            return tok
        text = self.token_re.sub(repl, text)
        text = self.label_re.sub(lambda m: self.labels.get(m.group(0), m.group(0)), text)
        return text


def main():
    jev = json.loads((lib.DATA / "english_catalog.json").read_text(encoding="utf-8"))
    item_zh = {int(k): v for k, v in lib.load("item_names.json").items()}
    mon_zh = {int(k): v for k, v in lib.load("monster_names.json").items()}
    map_zh = {int(k): v for k, v in lib.load("map_titles.json").items()}
    npc_zh = {int(k): v for k, v in lib.load("npc_names.json").items()}
    quest_names = {int(k): v for k, v in lib.load("quest_names.json").items()}
    tool_cj = json.loads((lib.DATA / "tooltip_cj.json").read_text(encoding="utf-8"))
    tool_model = json.loads((lib.DATA / "tooltip_model.json").read_text(encoding="utf-8"))
    qmsg = json.loads((lib.DATA / "quest_messages.json").read_text(encoding="utf-8"))
    tool_fix = {int(k): v for k, v in lib.load("tooltip_fixes.json").items()}
    fixer = Fixer(jev)

    for row in jev["maps"]:
        row["title"] = map_zh[row["index"]]
    for row in jev["items"]:
        row["name"] = item_zh[row["index"]]
        if row.get("toolTip"):
            tip = tool_fix.get(row["index"]) or tool_model.get(str(row["index"])) or tool_cj.get(str(row["index"]))
            if tip:
                row["toolTip"] = tip
    for row in jev["monsters"]:
        row["name"] = mon_zh[row["index"]]
    for row in jev["npcs"]:
        row["name"] = npc_zh[row["index"]]
    for row in jev["quests"]:
        info = row["info"]
        name = quest_names[info["index"]]
        info["name"] = name["name"]
        info["group"] = name["group"]
        for field in ("gotoMessage", "killMessage", "itemMessage", "flagMessage"):
            value = info.get(field)
            if not value:
                continue
            translated = MESSAGE_OVERRIDES.get(f"{info['index']}:{field}") or qmsg.get(f"{info['index']}:{field}")
            if not translated:
                translated = value
            info[field] = fixer.fix(translated)

    for shop in jev["shops"]:
        shop["category"] = SHOP_CATEGORIES.get(shop["category"], shop["category"])

    jev["dragon"]["monsterName"] = mon_zh[392]
    jev["dragon"]["bodyName"] = mon_zh[393]
    for conquest in jev["conquests"]:
        conquest["name"] = "沙巴克城墙"
        for archer in conquest.get("archers") or []:
            archer["name"] = mon_zh.get(archer.get("monsterIndex"), "守卫")
        for gate in conquest.get("gates") or []:
            gate["name"] = "沙巴克城门"
        for wall in conquest.get("walls") or []:
            wall["name"] = {"LeftWall": "左墙", "CenterWall": "中央墙", "RightWall": "右墙"}.get(
                wall["name"], "城墙")
        for flag in (conquest.get("flags") or []) + (conquest.get("controlPoints") or []):
            if flag.get("name"):
                flag["name"] = "旗帜"

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "Jev_final.json").write_text(json.dumps(jev, ensure_ascii=False, indent=1), encoding="utf-8")

    # invariants
    for label, rows, field in (("item", jev["items"], "name"), ("monster", jev["monsters"], "name")):
        values = [r[field] for r in rows]
        assert len(values) == len(set(values)), f"duplicate {label} names"
        for value in values:
            assert not re.search(r"\s", value), (label, value)
            assert re.search(r"[\u4e00-\u9fff]", value), (label, value)
            assert not re.search(r"[A-Za-z]", value), (label, value)
    for row in jev["maps"]:
        assert re.search(r"[\u4e00-\u9fff]", row["title"]) and not re.search(r"[A-Za-z]", row["title"]), row
    for row in jev["npcs"]:
        assert not re.search(r"\s", row["name"]) and re.search(r"[\u4e00-\u9fff]", row["name"]), row
    shop_latin = sorted({s["category"] for s in jev["shops"]
                         if re.search(r"[A-Za-z]", s["category"])})
    print("shop category Latin residue:", shop_latin)
    residue = []
    for row in jev["quests"]:
        for field in ("gotoMessage", "killMessage", "itemMessage", "flagMessage", "name", "group"):
            value = row["info"].get(field) or ""
            if re.search(r"[A-Za-z]{2,}", value):
                residue.append((row["info"]["index"], field, value))
    print("quest message Latin residue:", len(residue))
    for r in residue[:30]:
        print("  ", r)
    print("maps", len(jev["maps"]), "items", len(jev["items"]), "monsters", len(jev["monsters"]),
          "npcs", len(jev["npcs"]), "quests", len(jev["quests"]))


if __name__ == "__main__":
    main()
