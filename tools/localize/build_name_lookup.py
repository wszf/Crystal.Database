# -*- coding: utf-8 -*-
"""Build data/name_lookup.json: every visible markup string -> Chinese.

The label table only covers UI-ish strings; colour braces and links also wrap
raw item/monster/map names ("{ForestYeti's/Crimson}", "<Woomataurus/@x>").
Those are resolved here from the finalized name tables, including the
possessive form the legacy scripts use.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


def main():
    jev = json.loads((lib.DATA / "english_catalog.json").read_text(encoding="utf-8"))
    labels = dict(lib.load("label_tm.json"))
    item = {int(k): v for k, v in lib.load("item_names.json").items()}
    mon = {int(k): v for k, v in lib.load("monster_names.json").items()}
    mp = {int(k): v for k, v in lib.load("map_titles.json").items()}
    npc = {int(k): v for k, v in lib.load("npc_names.json").items()}
    skill = {int(k): v for k, v in lib.load("skill_names.json").items()}

    pairs = []
    for rows, zh, fields in ((jev["items"], item, ("name",)),
                             (jev["monsters"], mon, ("name",)),
                             (jev["maps"], mp, ("title", "fileName")),
                             (jev["npcs"], npc, ("name",))):
        for row in rows:
            for field in fields:
                pairs.append((row[field], zh[row["index"]]))
    for row in jev["items"]:
        if row["index"] in skill:
            pairs.append((row["name"], skill[row["index"]]))

    added = {}
    for english, chinese in pairs:
        for key in (english, english + "'s", english + "\u2019s"):
            if key not in labels and key not in added:
                added[key] = chinese
    labels.update(added)
    lib.save("name_lookup.json", dict(sorted(labels.items())))
    print("labels", len(labels), "added", len(added))


if __name__ == "__main__":
    main()
