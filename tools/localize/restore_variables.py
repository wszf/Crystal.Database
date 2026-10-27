# -*- coding: utf-8 -*-
"""Force every "<$VARIABLE>" markup token back to its original spelling.

The translation passes must never rewrite a server variable, but a model can
still emit localized text in its place ("<$PKPOINT>" -> "<PK点数>"). This pass
aligns the markup tokens of HEAD and the working tree and restores the visible
part of any token whose source was a variable.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

ROOTS = ("NPCs", "SystemScripts", "Events", "Quests")
REPO = lib.JEV.parent


VAR_ONLY = __import__("re").compile(r"\$[A-Za-z0-9_().,]+$")


def is_var(vis: str) -> bool:
    return bool(VAR_ONLY.fullmatch(vis.strip()))


def rebuild(tokens, variables) -> str:
    parts = []
    index = 0
    for tok in tokens:
        if tok.kind == "text":
            parts.append(tok.raw)
            continue
        vis = tok.vis
        replacement = variables.get(index)
        index += 1
        if replacement is not None:
            vis = replacement
        sep = "" if tok.fixed else "/"
        inner = vis if tok.rest is None else f"{vis}{sep}{tok.rest}"
        if tok.kind == "link":
            parts.append(f"<<{inner}>>")
        elif tok.kind == "tag":
            parts.append(f"<{inner}>")
        else:
            parts.append(f"{{{inner}}}")
    return "".join(parts)


def main() -> int:
    changed = []
    skipped = []
    for root in ROOTS:
        for path in sorted((lib.JEV / "Envir" / root).rglob("*.txt")):
            rel = "Jev/Envir/" + str(path.relative_to(lib.JEV / "Envir"))
            old = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{rel}"],
                                 capture_output=True, text=True).stdout
            new = path.read_text(encoding="utf-8")
            old_toks = [t for t in lib.tokenize(old) if t.kind != "text"]
            new_toks = [t for t in lib.tokenize(new) if t.kind != "text"]
            if len(old_toks) != len(new_toks):
                skipped.append(rel)
                continue
            variables = {}
            for i, (o, n) in enumerate(zip(old_toks, new_toks)):
                if is_var(o.vis) and n.vis != o.vis:
                    variables[i] = o.vis
            if not variables:
                continue
            text = rebuild(lib.tokenize(new), variables)
            if text != new:
                path.write_text(text, encoding="utf-8")
                changed.append((rel, len(variables)))
    print("files restored:", len(changed), "variables:", sum(n for _, n in changed))
    for rel, n in changed[:20]:
        print("  ", rel, n)
    print("skipped (token count differs):", len(skipped))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
