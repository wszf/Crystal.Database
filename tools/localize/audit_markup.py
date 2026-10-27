# -*- coding: utf-8 -*-
"""Verify that script markup survived localization.

Every @target and every colour name used by the client's markup regexes must
still be present with the same multiplicity; only visible text may change.
Malformed legacy markup ("<Text@Target>") is compared in its original form.
"""
from __future__ import annotations

import collections
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

ROOTS = ("NPCs", "SystemScripts", "Events", "Quests")
REPO = lib.JEV.parent
TARGET = re.compile(r"[/@](@[A-Za-z0-9_()+\-]+)(?=[/>])")
COLOUR = re.compile(r"[/@]([A-Za-z]{3,})(?=[}>])")


def tokens(text: str):
    out = collections.Counter()
    for m in TARGET.finditer(text):
        out[("target", m.group(1))] += 1
    for m in COLOUR.finditer(text):
        out[("colour", m.group(1).lower())] += 1
    return out


def main() -> int:
    problems = []
    changed = subprocess.run(
        ["git", "-C", str(REPO), "diff", "--name-only", "--", "Jev/Envir"],
        capture_output=True, text=True, check=True).stdout.split()
    for rel in changed:
        if not rel.endswith(".txt") or not rel.startswith(tuple(f"Jev/Envir/{r}/" for r in ROOTS)):
            continue
        old = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{rel}"],
                             capture_output=True, text=True).stdout
        new = (REPO / rel).read_text(encoding="utf-8")
        a, b = tokens(old), tokens(new)
        if a != b:
            problems.append((rel, (a - b), (b - a)))
    for rel, lost, extra in problems[:30]:
        print(rel)
        if lost:
            print("   lost ", dict(lost))
        if extra:
            print("   extra", dict(extra))
    print("files with markup drift:", len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
