# -*- coding: utf-8 -*-
"""Remove markup the translation model invented and fix leftover English names.

The model sometimes wrapped names in "[[Name]]" / "[[English:中文]]" markers.
Those are not Crystal markup and would be rendered literally, so they are
rewritten to plain Chinese (or to the matching item/monster/map name).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

ROOTS = ("NPCs", "SystemScripts", "Events", "Quests")
MARKER = re.compile(r"\[\[([^\[\]]+)\]\]")

STAT_WORDS = {
    "赤金": "防御",
    "黯金": "魔防",
    "防护": "攻击",
}

TEXT_FIXES = [
    # "CastleGi-Ryoong" is the map whose Chinese title is 封魔谷.
    ("城堡Gi-Ryoong", "封魔谷"),
    ("城堡 Gi-Ryoong", "封魔谷"),
    ("8o'clock", "8点钟"),
    ("4o'clock", "4点钟"),
]


def norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


def build_tables():
    jev = json.loads((lib.DATA / "english_catalog.json").read_text(encoding="utf-8"))
    item = {int(k): v for k, v in lib.load("item_names.json").items()}
    mon = {int(k): v for k, v in lib.load("monster_names.json").items()}
    mp = {int(k): v for k, v in lib.load("map_titles.json").items()}
    npc = {int(k): v for k, v in lib.load("npc_names.json").items()}
    tables = []
    for rows, zh, fields in ((jev["items"], item, ("name",)),
                             (jev["monsters"], mon, ("name",)),
                             (jev["maps"], mp, ("title", "fileName")),
                             (jev["npcs"], npc, ("name",))):
        table = {}
        for row in rows:
            for field in fields:
                table.setdefault(norm(row[field]), zh[row["index"]])
        tables.append(table)
    return tables


def resolve(name, tables):
    key = norm(name)
    for table in tables:
        if key in table:
            return table[key]
    return None


def rewrite(text, tables):
    def repl(m):
        inner = m.group(1).strip()
        if "/" in inner:                       # [[Title/url]] -> (Title/url)
            return f"({inner})"
        if ":" in inner:
            left, right = inner.split(":", 1)
            hit = resolve(left, tables)
            if hit:
                return hit
            if left and not re.search(r"[A-Za-z]", left):
                return inner                   # e.g. 等级:80
            return right.strip()
        hit = resolve(inner, tables)
        return hit or inner
    return MARKER.sub(repl, text)


def fix_stat_line(line: str) -> str:
    if "防御属性" not in line:
        return line
    for old, new in STAT_WORDS.items():
        line = line.replace(old, new)
    return line


def main():
    tables = build_tables()
    touched = 0
    for root in ROOTS:
        for path in sorted((lib.JEV / "Envir" / root).rglob("*.txt")):
            original = path.read_text(encoding="utf-8")
            text = rewrite(original, tables)
            text = "\n".join(fix_stat_line(x) for x in text.split("\n"))
            for old, new in TEXT_FIXES:
                text = text.replace(old, new)
            if text != original:
                path.write_text(text, encoding="utf-8")
                touched += 1
    print("files cleaned:", touched)


if __name__ == "__main__":
    main()
