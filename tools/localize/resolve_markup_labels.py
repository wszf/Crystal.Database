# -*- coding: utf-8 -*-
"""Translate link/colour labels that are still English after the main pass.

Quest prose and some NPC pages wrap names in colour braces ("{Zombies/Crimson}").
The label table resolves most of them, but the legacy scripts use loose variants
("WoomyonWoods" for the map titled "WoomyonWoods(S)", "MirGuide Peter", ...), so
this pass resolves them with a normalized index plus a small manual table.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

ROOTS = ("NPCs", "SystemScripts", "Events", "Quests")
VAR = re.compile(r"<\$[^<>]*>")
VAR_ONLY = re.compile(r"\$[A-Za-z0-9_().,]+$")
CJK = re.compile(r"[\u4e00-\u9fff]")


def key(s: str) -> str:
    """Aggressive normalization: letters+digits only, lower case."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def variants(name: str):
    base = name.strip()
    yield base
    yield re.sub(r"\((?:[A-Za-z]|\d+)\)$", "", base)     # WoomyonWoods(S)
    yield re.sub(r"[_\s]+\d?F$", "", base)               # Cave_1F
    yield re.sub(r"(?:'s|\u2019s)$", "", base)           # Zombie's
    if base.lower().endswith("s"):
        yield base[:-1]                                  # Zombies -> Zombie


def main():
    extra_path = lib.DATA / "label_extra.json"
    extra = json.loads(extra_path.read_text(encoding="utf-8")) if extra_path.exists() else {}
    lookup = dict(lib.load("name_lookup.json"))
    index = {}
    for english, chinese in lookup.items():
        if not CJK.search(chinese):
            continue
        for variant in variants(english):
            index.setdefault(key(variant), chinese)
    for english, chinese in extra.items():
        index[key(english)] = chinese

    # Person names used inside quest prose ("{Jane/LimeGreen}") come from the
    # NPC catalogue, e.g. "CraftsLady_Jane" -> "工艺夫人_简".
    jev = json.loads(Path("/tmp/task357/Jev.json").read_text(encoding="utf-8"))
    npc_zh = {int(k): v for k, v in lib.load("npc_names.json").items()}
    for npc in jev["npcs"]:
        english = [x for x in re.split(r"[_\s]+", npc["name"]) if x]
        chinese = [x for x in re.split(r"[_\s]+", npc_zh[npc["index"]]) if x]
        if len(english) != len(chinese):
            continue
        for eng, chn in zip(english, chinese):
            if len(eng) >= 3:
                index.setdefault(key(eng), chn)

    unresolved = {}
    changed = 0
    for root in ROOTS:
        for path in sorted((lib.JEV / "Envir" / root).rglob("*.txt")):
            original = path.read_text(encoding="utf-8")
            out = []
            file_changed = False
            for line in original.splitlines():
                toks = lib.tokenize(line)
                if not any(t.kind != "text" and re.search(r"[A-Za-z]{2,}", VAR.sub("", t.vis)) for t in toks):
                    out.append(line)
                    continue
                parts = []
                for tok in toks:
                    if tok.kind == "text":
                        parts.append(tok.raw)
                        continue
                    vis = tok.vis
                    if not re.search(r"[A-Za-z]{2,}", VAR.sub("", vis)) or VAR_ONLY.fullmatch(vis.strip()):
                        parts.append(tok.raw)
                        continue
                    new = None
                    for variant in variants(vis):
                        new = index.get(key(variant))
                        if new:
                            break
                    if new is None:
                        unresolved.setdefault(vis.strip(), f"{path.relative_to(lib.JEV)}: {line.strip()[:90]}")
                        parts.append(tok.raw)
                        continue
                    sep = "" if tok.fixed else "/"
                    inner = new if tok.rest is None else f"{new}{sep}{tok.rest}"
                    if tok.kind == "link":
                        parts.append(f"<<{inner}>>")
                    elif tok.kind == "tag":
                        parts.append(f"<{inner}>")
                    else:
                        parts.append(f"{{{inner}}}")
                    file_changed = True
                newline = "".join(parts)
                out.append(newline)
            if file_changed:
                text = "\n".join(out)
                if original.endswith("\n"):
                    text += "\n"
                path.write_text(text, encoding="utf-8")
                changed += 1
    print("files changed", changed)
    print("still unresolved", len(unresolved))
    for label, where in sorted(unresolved.items())[:60]:
        print(f"  {label!r}  {where}")


if __name__ == "__main__":
    main()
