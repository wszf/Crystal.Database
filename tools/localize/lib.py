# -*- coding: utf-8 -*-
"""Shared helpers for the Jev -> Simplified Chinese localization.

Mir2 script markup (as parsed by the Crystal client):
  <<visible/@Target>>   large link button
  <visible/@Target>     inline link button / colour tag
  {visible/Colour}      coloured text
  <$VARIABLE>           server-side variable (never translate)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
JEV = HERE.parents[1] / "Jev"

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")
WORD_RE = re.compile(r"[A-Za-z]{2,}")
WS_RE = re.compile(r"\s")


def has_cjk(s: str) -> bool:
    return bool(CJK_RE.search(s))


def has_latin(s: str) -> bool:
    return bool(LATIN_RE.search(s))


def has_words(s: str) -> bool:
    return bool(WORD_RE.search(s))


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def save(name: str, value) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
        encoding="utf-8",
    )


class Token:
    __slots__ = ("kind", "raw", "vis", "rest", "fixed")

    def __init__(self, kind, raw, vis, rest, fixed=False):
        self.kind = kind      # text | tag | link | brace
        self.raw = raw
        self.vis = vis
        self.rest = rest
        self.fixed = fixed    # malformed "<Text@Target>" repaired to "<Text/@Target>"

    def __repr__(self):
        return f"Token({self.kind!r},{self.raw!r})"


def _split_vis_rest(inner: str, first: bool = True):
    """Split markup payload.

    Links/tags target syntax is "<visible/@Target>" and may be followed by a
    colour: "<<Create Hero/@CreateHero/Green>>", so the FIRST slash separates
    the visible text.  Braces are "{visible/Colour}", where the visible text may
    itself contain slashes, so the LAST slash separates the colour.
    """
    if "/" in inner:
        if first:
            vis, rest = inner.split("/", 1)
        else:
            vis, rest = inner.rsplit("/", 1)
        return vis, rest
    return inner, None


def tokenize(line: str) -> list[Token]:
    """Split one script line into text and markup tokens."""
    out: list[Token] = []
    i = 0
    buf: list[str] = []
    n = len(line)

    def flush():
        if buf:
            out.append(Token("text", "".join(buf), "".join(buf), None))
            buf.clear()

    while i < n:
        ch = line[i]
        if ch == "<":
            if line.startswith("<<", i):
                end = line.find(">>", i + 2)
                if end != -1:
                    flush()
                    inner = line[i + 2:end]
                    vis, rest = _split_vis_rest(inner, True)
                    fixed = False
                    if rest is None and re.fullmatch(r"[^@/]+@[^@/]+", inner):
                        vis, target = inner.split("@", 1)
                        rest, fixed = "@" + target, True
                    out.append(Token("link", line[i:end + 2], vis, rest, fixed))
                    i = end + 2
                    continue
            end = line.find(">", i + 1)
            if end != -1:
                flush()
                inner = line[i + 1:end]
                vis, rest = _split_vis_rest(inner, True)
                fixed = False
                if rest is None and re.fullmatch(r"[^@/]+@[^@/]+", inner):
                    vis, target = inner.split("@", 1)
                    rest, fixed = "@" + target, True
                out.append(Token("tag", line[i:end + 1], vis, rest, fixed))
                i = end + 1
                continue
        elif ch == "{":
            end = line.find("}", i + 1)
            if end != -1:
                flush()
                inner = line[i + 1:end]
                vis, rest = _split_vis_rest(inner)
                out.append(Token("brace", line[i:end + 1], vis, rest))
                i = end + 1
                continue
        buf.append(ch)
        i += 1
    flush()
    return out


VAR_RE = re.compile(r"<\$[^<>]*>")


def vis_is_variable(vis: str) -> bool:
    stripped = VAR_RE.sub("", vis)
    return not WORD_RE.search(stripped)


def render_placeholders(tokens: list[Token], labels: dict[str, str]):
    """Return (render_text, mapping) where every markup token becomes [[i:label]]."""
    mapping = {}
    parts = []
    for idx, tok in enumerate(tokens):
        if tok.kind == "text":
            parts.append(tok.vis)
            continue
        key = tok.vis.strip()
        label = labels.get(key, key)
        if not WORD_RE.search(VAR_RE.sub("", tok.vis)):
            label = ""
        mapping[idx] = (tok, label)
        parts.append(f"[[{idx}:{label}]]" if label else f"[[{idx}]]")
    return "".join(parts), mapping


PLACEHOLDER_RE = re.compile(r"\[\[\s*(\d+)\s*(?::(.*?))?\]\]", re.S)


def restore_placeholders(translated: str, mapping: dict[int, tuple[Token, str]]) -> str:
    out = []
    last = 0
    for m in PLACEHOLDER_RE.finditer(translated):
        out.append(translated[last:m.start()])
        idx = int(m.group(1))
        tok, orig_label = mapping.get(idx, (None, None))
        if tok is None:
            out.append(m.group(0))
            last = m.end()
            continue
        if tok.kind == "text":
            out.append(tok.raw)
            last = m.end()
            continue
        # Always use the reviewed label translation; never trust the model's copy.
        # Tokens whose visible part is a server variable (e.g. {<$WEAPON>/CORAL})
        # carry an empty label, so the original text must be restored.
        new_label = orig_label or tok.vis
        sep = "" if tok.fixed else "/"
        if tok.kind == "link":
            inner = new_label if tok.rest is None else f"{new_label}{sep}{tok.rest}"
            out.append(f"<<{inner}>>")
        elif tok.kind == "tag":
            inner = new_label if tok.rest is None else f"{new_label}{sep}{tok.rest}"
            out.append(f"<{inner}>")
        else:
            inner = new_label if tok.rest is None else f"{new_label}{sep}{tok.rest}"
            out.append(f"{{{inner}}}")
        last = m.end()
    out.append(translated[last:])
    return "".join(out)


def all_markup_tokens(text: str) -> list[Token]:
    return [t for t in tokenize(text) if t.kind != "text"]
