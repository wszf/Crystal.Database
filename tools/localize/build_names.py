# -*- coding: utf-8 -*-
"""Build the Jev -> Simplified Chinese name tables.

Inputs : /tmp/task357/{Jev,cjlaaa}.json  (produced by the legacyworld dumper)
Output : item_names.json, monster_names.json, map_titles.json, npc_names.json
"""
import json, re, sys, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from item_overrides import OVER

BASE = "/tmp/task357"
cjk = lambda s: bool(re.search(r"[\u4e00-\u9fff]", s))
jev = json.load(open(f"{BASE}/Jev.json"))
cj = json.load(open(f"{BASE}/cjlaaa.json"))
ci = {x["index"]: x for x in cj["items"]}

dup = collections.Counter(x["name"] for x in cj["items"])


def bad(n):
    return (not cjk(n)) or bool(re.search(r"[A-Za-z]", n)) or dup[n] > 1 or bool(re.search(r"\s", n))


names = {}
problems = []
for x in jev["items"]:
    i = x["index"]
    if i in OVER:
        names[i] = OVER[i]
    elif i in ci and not bad(ci[i]["name"]):
        names[i] = ci[i]["name"]
    else:
        problems.append((i, x["name"], ci.get(i, {}).get("name", "")))

print("unresolved:", len(problems))
for p in problems:
    print("  ", p)

seen = collections.defaultdict(list)
for i, n in names.items():
    if re.search(r"\s", n):
        print("WHITESPACE", i, repr(n))
    if re.search(r"[A-Za-z]", n):
        print("LATIN", i, repr(n))
    seen[n].append(i)
for n, idx in seen.items():
    if len(idx) > 1:
        print("DUPLICATE", n, idx)
print("total names", len(names), "unique", len(seen))
json.dump({str(k): names[k] for k in sorted(names)}, open("item_names.json", "w"), ensure_ascii=False, indent=0)
