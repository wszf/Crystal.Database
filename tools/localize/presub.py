# -*- coding: utf-8 -*-
import json, re
BASE = "/tmp/task357"
names = json.load(open("item_names.json"))
monsters = json.load(open("monster_names.json"))
gloss = json.load(open("glossary.json"))
jev = json.load(open(f"{BASE}/Jev.json"))
table = {}
for x in jev["items"]:
    if re.search(r"[A-Za-z]", x["name"]):
        table.setdefault(x["name"], names[str(x["index"])])
for x in jev["monsters"]:
    table.setdefault(x["name"], monsters[str(x["index"])])
for k, v in gloss.items():
    table.setdefault(k, v)
keys = sorted(table, key=lambda s: -len(s))
pat = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(k) for k in keys) + r")(?![A-Za-z0-9])")

# Tags: <visible/@target> and {visible/Colour}.  Only the visible part may be
# substituted; the target/colour token must stay byte-identical.
SPLIT = re.compile(r"(<[^<>]*>|\{[^{}]*\}|@[A-Za-z0-9_()+\-]+)")

def subst_text(text):
    return pat.sub(lambda m: table[m.group(1)], text)

def subst(line):
    if line.strip().startswith("[") and line.strip().endswith("]"):
        return line
    out = []
    last = 0
    for m in SPLIT.finditer(line):
        out.append(subst_text(line[last:m.start()]))
        tag = m.group(1)
        if tag.startswith("@"):
            out.append(tag)
            last = m.end()
            continue
        inner = tag[1:-1]
        if "/" in inner:
            vis, rest = inner.rsplit("/", 1)
            out.append(tag[0] + subst_text(vis) + "/" + rest + tag[-1])
        else:
            out.append(tag[0] + subst_text(inner) + tag[-1])
        last = m.end()
    out.append(subst_text(line[last:]))
    return "".join(out)

if __name__ == "__main__":
    rows = []
    for raw in open(f"{BASE}/prose_lines.tsv"):
        i, n, s = raw.rstrip("\n").split("\t", 2)
        rows.append((i, n, s, subst(s)))
    with open(f"{BASE}/prose_pre.tsv", "w") as f:
        for i, n, s, p in rows:
            f.write(f"{i}\t{n}\t{p}\t{s}\n")
    print("rows", len(rows))
