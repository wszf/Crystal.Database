# -*- coding: utf-8 -*-
"""Resolve as many UI label translations as possible from the name tables."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

WORK = Path("/tmp/task357/work")


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def main():
    jev = json.loads((Path("/tmp/task357/Jev.json")).read_text(encoding="utf-8"))
    item_zh = lib.load("item_names.json")
    mon_zh = lib.load("monster_names.json")
    map_zh = lib.load("map_titles.json")
    npc_zh = lib.load("npc_names.json")
    skill_zh = lib.load("skill_names.json")

    item = {norm(x["name"]): item_zh[str(x["index"])] for x in jev["items"]}
    mon = {norm(x["name"]): mon_zh[str(x["index"])] for x in jev["monsters"]}
    mp = {}
    for x in jev["maps"]:
        mp[norm(x["fileName"])] = map_zh[str(x["index"])]
    skill = {norm(x["name"]): skill_zh[str(x["index"])] for x in jev["items"] if str(x["index"]) in skill_zh}
    npcn = {norm(x["name"]): npc_zh[str(x["index"])] for x in jev["npcs"]}

    units = json.loads((WORK / "units.json").read_text(encoding="utf-8"))
    resolved, pending = {}, []
    for row in units["labels"]:
        text = row["text"]
        if not lib.has_words(text):
            resolved[text] = text
            continue
        zh = lookup(text, item, mon, mp, skill, npcn)
        if zh:
            resolved[text] = zh
        else:
            pending.append(row)
    (WORK / "labels_resolved.json").write_text(json.dumps(resolved, ensure_ascii=False, indent=1), encoding="utf-8")
    (WORK / "labels_pending.json").write_text(json.dumps(pending, ensure_ascii=False, indent=1), encoding="utf-8")
    print("resolved", len(resolved), "pending", len(pending))
    for row in pending[:200]:
        print(row["count"], row["text"])


def lookup(text, *tables):
    for table in tables:
        value = _lookup_one(text.strip(), table)
        if value:
            return value
    # "Fencing 7" / "ShoulderDash 30"
    m = re.match(r"^(.*?\S)\s+(\d+)$", text.strip())
    if m:
        for table in tables:
            value = _lookup_one(m.group(1), table)
            if value:
                return f"{value} {m.group(2)}"
    return None


def _lookup_one(text, table):
    if not text:
        return None
    variants = [text, text.replace("_", " "), text.replace(" ", "")]
    for v in variants:
        hit = table.get(norm(v))
        if hit:
            return hit
    return None


if __name__ == "__main__":
    main()
