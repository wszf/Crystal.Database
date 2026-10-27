# -*- coding: utf-8 -*-
"""Report visible English left in the localized Envir scripts."""
from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

ENVIR = lib.JEV / "Envir"
ENVIR_ROOTS = ("NPCs", "SystemScripts", "Events")
WORD = re.compile(r"[A-Za-z]{2,}")
# tokens that may legitimately stay in Latin script inside visible text
ALLOW = re.compile(r"\b(HP|MP|PK|GM|GT|NPC|Mir2|LOMCN|Crystal|Suprcode|OK|EXP|DC|MC|SC|AC|MAC|CPU|PT|USD)\b", re.I)


def visible(line: str) -> str:
    text = line
    text = re.sub(r"<\$[^>]*>", " ", text)          # variables
    text = re.sub(r"<[^<>]*>", " ", text)            # links / tags
    text = re.sub(r"\{[^{}]*\}", " ", text)          # colour braces
    text = re.sub(r"\[(MONSTER|NPC|ITEM):[^\]]*\]", " ", text, flags=re.I)
    text = re.sub(r"\([^()]*\)", " ", text)          # (visible/url) links
    return ALLOW.sub(" ", text)


def main():
    hits = collections.Counter()
    samples = collections.defaultdict(list)
    quests_hits = collections.Counter()
    for root in ENVIR_ROOTS:
        for path in (ENVIR / root).rglob("*.txt"):
            state = None
            section = None
            for line in path.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s.startswith("#"):
                    u = s.upper()
                    state = "say" if u.startswith(("#SAY", "#ELSESAY")) else ("cmd" if u.startswith(("#ACT", "#ELSEACT", "#IF")) else state)
                    continue
                if s.startswith("[@"):
                    section = s[2:-1]
                    state = None
                    continue
                if s.startswith("["):
                    section = None
                    state = None
                    continue
                if state != "say" or not s:
                    continue
                for m in WORD.finditer(visible(s)):
                    hits[m.group(0).lower()] += 1
                    if len(samples[m.group(0).lower()]) < 2:
                        samples[m.group(0).lower()].append(f"{path.relative_to(lib.JEV)}: {s[:90]}")
    for path in (ENVIR / "Quests").rglob("*.txt"):
        section = None
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("[@") and s.endswith("]"):
                section = s[2:-1]
                continue
            if s.startswith("["):
                section = None
                continue
            if section in ("Description", "TaskDescription", "ReturnDescription", "Completion") and s:
                for m in WORD.finditer(visible(s)):
                    quests_hits[m.group(0).lower()] += 1
    print("NPC/dialogue Latin words:", sum(hits.values()), "distinct", len(hits))
    for word, count in hits.most_common(40):
        print(f"  {count:5d} {word:16s} {samples[word][0]}")
    print("quest prose Latin words:", sum(quests_hits.values()), "distinct", len(quests_hits))
    for word, count in quests_hits.most_common(20):
        print(f"  {count:5d} {word}")


if __name__ == "__main__":
    main()
