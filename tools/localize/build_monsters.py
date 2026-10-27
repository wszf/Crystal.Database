# -*- coding: utf-8 -*-
import json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monster_overrides import OVER
BASE = "/tmp/task357"
cjk = lambda s: bool(re.search(r"[\u4e00-\u9fff]", s))
jev = json.load(open(f"{BASE}/Jev.json"))
cj = json.load(open(f"{BASE}/cjlaaa.json"))
cm = {x["index"]: x for x in cj["monsters"]}
names = {}
unres = []
for x in jev["monsters"]:
    i = x["index"]
    if i in OVER:
        names[i] = OVER[i]
        continue
    c = cm.get(i)
    if c and cjk(c["name"]) and not re.search(r"[A-Za-z]", c["name"]) and \
            (c["image"] == x["image"] or c["name"] == c["gameName"] or True):
        names[i] = c["name"]
    else:
        unres.append((i, x["name"], c["name"] if c else ""))
print("unresolved", len(unres))
for u in unres:
    print("  ", u)
seen = {}
dups = []
for i, n in names.items():
    if re.search(r"\s", n) or re.search(r"[A-Za-z]", n):
        print("BADNAME", i, repr(n))
    if n in seen:
        dups.append((n, seen[n], i))
    seen[n] = i
print("dups", dups)
print("total", len(names), "unique", len(seen))
json.dump({str(k): names[k] for k in sorted(names)}, open("monster_names.json", "w"), ensure_ascii=False, indent=0)
