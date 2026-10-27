# -*- coding: utf-8 -*-
"""Extract every visible-text unit from Jev Envir scripts into work/units.json."""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

WORK = Path("/tmp/task357/work")
SCRIPT_ROOTS = ("NPCs", "SystemScripts", "Events")
QUEST_ROOT = "Quests"


def iter_script_files():
    envir = lib.JEV / "Envir"
    for root in SCRIPT_ROOTS:
        base = envir / root
        if base.is_dir():
            yield from sorted(p for p in base.rglob("*.txt"))


def iter_quest_files():
    base = lib.JEV / "Envir" / QUEST_ROOT
    yield from sorted(base.rglob("*.txt"))


def make_quest(path, section, buf):
    text = "\n".join(buf)
    toks = lib.tokenize(text)
    render, _ = lib.render_placeholders(toks, {})
    return {"file": str(path.relative_to(lib.JEV / "Envir")), "section": section,
            "text": text, "render": render}


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    labels = collections.Counter()
    renders = collections.Counter()   # placeholder render -> original line
    originals = {}
    for path in iter_script_files():
        state = None
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                upper = stripped.upper()
                if upper.startswith(("#SAY", "#ELSESAY")):
                    state = "say"
                elif upper.startswith(("#ACT", "#ELSEACT", "#IF")):
                    state = "cmd"
                continue
            if stripped.startswith("[@"):
                # A page header implicitly opens a SAY block: plain lines that
                # follow it are dialogue until the next #IF/#ACT/#SAY marker.
                state = "say"
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                state = None
                continue
            if state != "say" or not stripped:
                continue
            toks = lib.tokenize(stripped)
            for tok in toks:
                if tok.kind == "text":
                    continue
                if tok.vis.strip():
                    labels[tok.vis.strip()] += 1
            render, _ = lib.render_placeholders(toks, {})
            if lib.WORD_RE.search(re.sub(r"\[\[\d+[^\]]*\]\]", "", render)):
                renders[render] += 1
                originals.setdefault(render, stripped)

    quoted = collections.Counter()
    for path in list(iter_script_files()) + list(iter_quest_files()):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            for m in re.finditer(r'"([^"]*)"', line):
                quoted[m.group(1)] += 1

    quests = []
    for path in iter_quest_files():
        cur = None
        buf = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            t = line.strip()
            if t.startswith("[@") and t.endswith("]"):
                if cur in ("Description", "TaskDescription", "ReturnDescription", "Completion") and buf:
                    quests.append(make_quest(path, cur, buf))
                cur = t[2:-1]
                buf = []
            elif cur and t and not t.startswith("//"):
                buf.append(t)
        if cur in ("Description", "TaskDescription", "ReturnDescription", "Completion") and buf:
            quests.append(make_quest(path, cur, buf))

    # Only translate lines that actually contain English words outside markup.
    todo = [r for r in renders if lib.WORD_RE.search(re.sub(r"\[\[\d+[^\]]*\]\]", "", r))]
    out = {
        "labels": [{"text": k, "count": v} for k, v in labels.most_common()],
        "lines": [{"render": r, "source": originals[r], "count": renders[r]} for r in sorted(todo)],
        "quests": quests,
        "quoted": [{"text": k, "count": v,
                    "render": lib.render_placeholders(lib.tokenize(k), {})[0]}
                   for k, v in quoted.most_common()],
    }
    (WORK / "units.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("labels", len(labels), "say lines", len(renders), "to translate", len(todo), "quest paragraphs", len(quests))


if __name__ == "__main__":
    main()
