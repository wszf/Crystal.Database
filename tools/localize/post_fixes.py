# -*- coding: utf-8 -*-
"""Targeted fixes for malformed markup in the legacy Jev scripts.

Each entry repairs an obvious typo in the original English file; they are kept
here (instead of inside the translators) so they are easy to audit.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

FIXES = [
    # Missing "{" left the deer colour code rendered as literal text.
    ("Envir/NPCs/WoomyonWoods/Castle-GI/Butcher.txt", "鹿/深红}", "{鹿/Crimson}"),
]


def main():
    for rel, old, new in FIXES:
        path = lib.JEV / rel
        text = path.read_text(encoding="utf-8")
        if old not in text:
            raise SystemExit(f"post fix not found: {rel}: {old!r}")
        path.write_text(text.replace(old, new), encoding="utf-8")
        print("fixed", rel)


if __name__ == "__main__":
    main()
