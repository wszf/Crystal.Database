# -*- coding: utf-8 -*-
"""Apply the Task 357 Jev localization to scripts, drops, recipes, and configs.

Run from anywhere:
    python3 Crystal.Database/tools/localize/apply_text.py

The script is idempotent for already-Chinese content (old Latin names only).
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
JEV = REPO / "Jev"
BASE = Path("/tmp/task357")

item_names = {int(k): v for k, v in json.loads((HERE / "item_names.json").read_text()).items()}
monster_names = {int(k): v for k, v in json.loads((HERE / "monster_names.json").read_text()).items()}
jev = json.loads((BASE / "Jev.json").read_text())

items_by_index = {x["index"]: x for x in jev["items"]}
monsters_by_index = {x["index"]: x for x in jev["monsters"]}

# Server lookup uses the last item with a duplicate legacy name.
item_map: dict[str, str] = {}
for x in jev["items"]:
    new = item_names[x["index"]]
    if x["name"].casefold() != "gold":
        item_map[x["name"].lower()] = new
monster_map: dict[str, str] = {}
for x in jev["monsters"]:
    monster_map[x["name"].lower()] = monster_names[x["index"]]

def _regex_map(mapping: dict[str, str]) -> re.Pattern[str]:
    keys = sorted(mapping, key=len, reverse=True)
    return re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(map(re.escape, keys)) + r")(?![A-Za-z0-9_])", re.IGNORECASE)

ITEM_RE = _regex_map(item_map)
MONSTER_RE = _regex_map(monster_map)

def replace_names(text: str, *, items: bool = True, monsters: bool = True) -> str:
    if items:
        text = ITEM_RE.sub(lambda m: item_map[m.group(1).lower()], text)
    if monsters:
        text = MONSTER_RE.sub(lambda m: monster_map[m.group(1).lower()], text)
    return text

# Exact translation memory for every script line in Jev/Envir.
tm: dict[str, str] = {}
tm_path = HERE / "prose_tm.tsv"
if tm_path.exists():
    for raw in tm_path.read_text(encoding="utf-8").splitlines():
        if not raw or "\t" not in raw:
            continue
        orig, translated = raw.split("\t", 1)
        tm[orig] = translated

ui_labels = json.loads((HERE / "ui_labels.json").read_text())
msg_map = json.loads((HERE / "messages.json").read_text()) if (HERE / "messages.json").exists() else {}

COMMON = [
    (r"\bBichon\b", "比奇"),
    (r"\bMongchon\b", "盟重"),
    (r"\bSabuk\b", "沙巴克"),
    (r"\bWooma\b", "沃玛"),
    (r"\bZuma\b", "祖玛"),
    (r"\bTaoist\b", "道士"),
    (r"\bWizard\b", "法师"),
    (r"\bWarrior\b", "战士"),
    (r"\bAssassin\b", "刺客"),
    (r"\bArcher\b", "弓箭手"),
    (r"\bGuild\b", "行会"),
    (r"\bHero\b", "英雄"),
]

# Tag forms used by the legacy script language: <text/@target[/Colour]> and
# <<text/@target[/Colour]>>.  Only visible text is touched.
TAG_RE = re.compile(r"(<+)([^<>\n]*?)(/@[A-Za-z0-9_()+\-]+)(/[A-Za-z]+)?(>+)")

def localize_tag(m: re.Match[str]) -> str:
    lead, label, target, colour, tail = m.groups()
    key = target.lower()
    if key in ui_labels and re.search(r"[A-Za-z]", label):
        label = ui_labels[key]
    return lead + label + target + (colour or "") + tail

def polish_visible(text: str) -> str:
    text = TAG_RE.sub(localize_tag, text)
    # LocalMessage/LineMessage: translate only the quoted string.
    m = re.match(r'(?i)^(LocalMessage|LineMessage)(\s+)"(.*)"(\s*(?:Hint|Shout|Whisper)?\s*)$', text)
    if m and m.group(3) in msg_map:
        text = m.group(1) + m.group(2) + '"' + msg_map[m.group(3)] + '"' + m.group(4)
    # Avoid touching technical tokens when applying the residual term glossary.
    chunks = re.split(r"(<[^<>]*>|\{[^{}]*\}|@[A-Za-z0-9_()+\-]+)", text)
    for i in range(0, len(chunks), 2):
        chunk = chunks[i]
        for pat, rep in COMMON:
            chunk = re.sub(pat, rep, chunk)
        chunks[i] = chunk
    return "".join(chunks)

SCRIPT_DIRS = [JEV / "Envir" / p for p in ("NPCs", "Quests", "SystemScripts", "Events")]
TEXT_SUFFIXES = {".txt"}

ITEM_SECTIONS = {"[TRADE]", "[RECIPE]"}
ITEM_COMMANDS = re.compile(
    r"^(?:CHECKITEM|TAKEITEM|GIVEITEM|TAKE\w*|GIVE\w*|CHECKMON\w*|MON\w*|MONGEN|PARAM3|CHECKPET|GIVEPET)\b",
    re.IGNORECASE,
)

def localize_code_line(line: str, in_item_section: bool) -> str:
    stripped = line.strip()
    upper = stripped.upper()
    if not stripped or stripped.startswith(("#", "//", "[", ";")):
        return line
    # MagicInfo.Name remains English because GIVESKILL resolves it directly.
    if upper.startswith("GIVESKILL"):
        return line
    if in_item_section or ITEM_COMMANDS.match(stripped):
        return replace_names(line)
    return line

def rewrite_script(path: Path) -> None:
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    ending = "\r\n" if "\r\n" in text else "\n"
    out_lines = []
    in_item_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper() in ITEM_SECTIONS:
            in_item_section = True
        elif stripped.startswith("[") and stripped.endswith("]"):
            in_item_section = False
        if stripped in tm:
            new = tm[stripped]
            if stripped != line:
                lead = line[:len(line) - len(line.lstrip())]
                trail = line[len(line.rstrip()):]
                new = lead + new + trail
        else:
            new = localize_code_line(line, in_item_section)
        out_lines.append(polish_visible(new))
    out = ending.join(out_lines)
    if text.endswith(("\n", "\r")):
        out += ending
    data = out.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)

def rewrite_with_names(path: Path) -> None:
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    text = replace_names(text, items=True, monsters=True)
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)

def rewrite_drop(path: Path) -> None:
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    # Gold is a hard-coded drop keyword and must stay untouched.
    text = replace_names(text, items=True, monsters=False)
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)

def main() -> None:
    for d in SCRIPT_DIRS:
        for path in sorted(d.rglob("*")):
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                rewrite_script(path)

    # Recipes: filenames identify output items, and contents contain item names.
    recipe_dir = JEV / "Envir" / "Recipe"
    for path in sorted(recipe_dir.glob("*.txt")):
        old = path.stem
        if old in item_map:
            newpath = path.with_name(item_map[old] + ".txt")
            rewrite_with_names(path)
            if newpath != path:
                path.replace(newpath)
        else:
            rewrite_with_names(path)

    # Drop files: root-level files for monsters whose DropPath is empty are
    # addressed by monster name; all other drop paths are literal.
    drop_dir = JEV / "Envir" / "Drops"
    for path in sorted(drop_dir.rglob("*.txt")):
        rewrite_drop(path)
    for x in jev["monsters"]:
        if x.get("dropPath"):
            continue
        src = drop_dir / (x["name"] + ".txt")
        dst = drop_dir / (monster_names[x["index"]] + ".txt")
        if src.exists() and src != dst:
            if dst.exists():
                raise SystemExit(f"drop rename collision: {src} -> {dst}")
            src.replace(dst)

    print("scripts rewritten; drops and recipes synchronized")

if __name__ == "__main__":
    main()
