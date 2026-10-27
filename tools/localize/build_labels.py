# -*- coding: utf-8 -*-
"""Rebuild data/label_tm.json with the final name tables taking priority.

The map titles come from cjlaaa (index + FileName matched) and are the
authentic Simplified Chinese Mir2 names, so a link label that names a map must
use the same string as the map record; otherwise NPC links disagree with the
map the player is standing on.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

WORK = lib.WORK


def norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


def main():
    jev = json.loads((lib.DATA / "english_catalog.json").read_text(encoding="utf-8"))
    labels = dict(lib.load("label_tm.json"))
    fixes = dict(lib.load("label_fixes.json"))
    item_zh = {int(k): v for k, v in lib.load("item_names.json").items()}
    mon_zh = {int(k): v for k, v in lib.load("monster_names.json").items()}
    map_zh = {int(k): v for k, v in lib.load("map_titles.json").items()}
    npc_zh = {int(k): v for k, v in lib.load("npc_names.json").items()}

    def table(rows, zh, field="name"):
        out = {}
        for row in rows:
            out.setdefault(norm(row[field]), []).append(zh[row["index"]])
        return out

    items = table(jev["items"], item_zh)
    monsters = table(jev["monsters"], mon_zh)
    maps = table(jev["maps"], map_zh, "title")
    npcs = table(jev["npcs"], npc_zh)

    stats = {"map": 0, "item": 0, "monster": 0, "keep": 0}
    for key in sorted(labels):
        n = norm(key)
        hit = None
        for name, table_, kind in ((maps, maps, "map"), (items, items, "item"),
                                   (monsters, monsters, "monster")):
            values = table_.get(n)
            if not values:
                continue
            uniq = sorted(set(values), key=lambda v: (-values.count(v), len(v), v))
            if labels[key] in uniq:
                hit = labels[key]
            elif len(uniq) == 1:
                # Only unambiguous names are forced: several maps can share an
                # English title (e.g. ZumaTemple), and a floor-specific Chinese
                # name would then leak into a generic link label.
                hit = uniq[0]
                stats[kind] += 1
            else:
                hit = labels[key]
            break
        if hit is None:
            stats["keep"] += 1
            continue
        labels[key] = hit

    # Item labels that must match the item record exactly.
    item_by_name = {norm(x["name"]): item_zh[x["index"]] for x in jev["items"]}
    for key in ("TownTeleport", "Townteleport"):
        if key in labels:
            labels[key] = item_by_name.get(norm(key), labels[key])

    lib.save("label_tm.json", dict(sorted(labels.items())))
    print(json.dumps(stats, ensure_ascii=False))
    print("labels", len(labels), "fixes-not-in-labels",
          len([k for k in fixes if k not in labels]))


if __name__ == "__main__":
    main()
