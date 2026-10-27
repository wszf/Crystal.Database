# -*- coding: utf-8 -*-
"""Compose data/label_tm.json from the resolved name tables, the model's UI
labels and the hand-written fixes (in increasing priority)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

WORK = lib.WORK


def main():
    model = json.loads((lib.DATA / "tm.json").read_text(encoding="utf-8"))["label"]
    resolved = json.loads((WORK / "labels_resolved.json").read_text(encoding="utf-8"))
    fixes = dict(lib.load("label_fixes.json"))
    labels = dict(lib.load("label_tm.json"))   # keep variables and earlier work
    labels.update(model)
    labels.update(resolved)
    labels.update(fixes)
    lib.save("label_tm.json", dict(sorted(labels.items())))
    print("label_tm", len(labels), "model", len(model), "resolved", len(resolved), "fixes", len(fixes))


if __name__ == "__main__":
    main()
