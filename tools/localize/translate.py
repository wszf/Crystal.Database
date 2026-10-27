# -*- coding: utf-8 -*-
"""Fill data/tm.json with Simplified Chinese using a local Ollama model.

Usage:
    python3 translate.py labels
    python3 translate.py lines [--limit N]
    python3 translate.py quests
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

WORK = Path("/tmp/task357/work")
URL = "http://127.0.0.1:11434/api/generate"
MODEL = "gemma4:e4b"
BATCH = 20
LOCK = threading.Lock()

SYSTEM = """你是《热血传奇》(Legend of Mir 2) 简体中文专业本地化译者。
把英文翻译成中国大陆传奇玩家熟悉的自然简体中文。
规则：
- 保留 [[数字:文字]] 占位符原样，只允许把冒号后的文字替换成对应中文；必须保留每个占位符和编号。
- 使用传奇术语：金币、等级、经验、修理、商店、仓库、公会、沙巴克、比奇省、祖玛、魔法值(MP)、生命值(HP)、攻击、防御。
- 不解释，不加引号，不加注释。
- 只输出 JSON。"""


def store_path():
    return lib.DATA / "tm.json"


def load_store():
    p = store_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"label": {}, "line": {}, "quest": {}}


def save_store(store):
    tmp = store_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(store_path())


def ask(prompt, num_predict=4000):
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "system": SYSTEM,
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": 0.15, "num_predict": num_predict, "repeat_penalty": 1.05},
    }).encode()
    last = None
    for attempt in range(4):
        try:
            r = requests.post(URL, data=body, headers={"Content-Type": "application/json"}, timeout=300)
            r.raise_for_status()
            return json.loads(r.json()["response"])
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 + attempt * 3)
    raise RuntimeError(f"ollama failed: {last}")


def translate_batch(kind, sources):
    if kind == "label":
        prompt = (
            "把下面的传奇游戏界面按钮/标签文字翻译成简体中文。"
            "每项一个字符串，输出 {\"out\": [...]}，长度和顺序必须一致。\n"
            + json.dumps(sources, ensure_ascii=False)
        )
    elif kind == "line":
        prompt = (
            "把下面的传奇NPC对话逐条翻译成简体中文，保留换行(\\n)与占位符。"
            "输出 {\"out\": [...]}，长度和顺序必须一致。\n"
            + json.dumps(sources, ensure_ascii=False)
        )
    else:
        prompt = (
            "把下面每段传奇任务描述翻译成简体中文，保留 {文字/颜色} 标记和 \\n 换行。"
            "输出 {\"out\": [...]}，长度和顺序必须一致。\n"
            + json.dumps(sources, ensure_ascii=False)
        )
    data = ask(prompt)
    out = data.get("out")
    if not isinstance(out, list) or len(out) != len(sources):
        raise RuntimeError(f"bad batch shape: {type(out)} {len(out) if isinstance(out, list) else '?'}")
    return [str(x) for x in out]


PH = re.compile(r"\[\[\s*(\d+)\s*(?::(.*?))?\]\]")


def check(kind, source, out):
    if not isinstance(out, str) or not out.strip():
        return "empty"
    if not lib.has_cjk(out):
        return "no-cjk"
    if kind in ("line", "quest"):
        want = [m.group(1) for m in PH.finditer(source)]
        got = [m.group(1) for m in PH.finditer(out)]
        if sorted(want) != sorted(got):
            return f"placeholder {want} -> {got}"
        for m in re.finditer(r"\{\s*([^{}]*?)/([^{}]*?)\}", out):
            if m.group(2).strip() and not re.fullmatch(r"[A-Za-z0-9#]+", m.group(2).strip()):
                return f"colour {m.group(2)!r}"
    return None


def run(kind, items, batch_size=BATCH):
    store = load_store()
    done = store[kind]
    todo = [s for s in items if s not in done]
    print(f"{kind}: {len(items)} total, {len(done)} cached, {len(todo)} to do", flush=True)
    errors = []
    for start in range(0, len(todo), batch_size):
        chunk = todo[start:start + batch_size]
        try:
            outs = translate_batch(kind, chunk)
        except Exception as exc:  # noqa: BLE001
            print(f"  batch {start}: {exc}", flush=True)
            errors.extend(chunk)
            continue
        for src, out in zip(chunk, outs):
            problem = check(kind, src, out)
            if problem:
                errors.append(src)
                print(f"  REJECT {problem}: {src!r} -> {out!r}", flush=True)
            else:
                done[src] = out
        with LOCK:
            save_store(store)
        print(f"  {min(start + batch_size, len(todo))}/{len(todo)}", flush=True)
    if errors:
        # retry one-by-one
        print(f"  retrying {len(errors)} individually", flush=True)
        for src in list(errors):
            try:
                outs = translate_batch(kind, [src])
                out = outs[0]
                if check(kind, src, out):
                    raise RuntimeError(check(kind, src, out))
                done[src] = out
                errors.remove(src)
            except Exception as exc:  # noqa: BLE001
                print(f"  FAILED {src!r}: {exc}", flush=True)
        save_store(store)
    print(f"{kind}: translated {len(done)}/{len(items)}, {len(errors)} failures", flush=True)
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["labels", "lines", "quests", "quoted"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=BATCH)
    args = ap.parse_args()
    units = json.loads((WORK / "units.json").read_text(encoding="utf-8"))
    if args.kind == "labels":
        pending = json.loads((WORK / "labels_pending.json").read_text(encoding="utf-8"))
        items = [r["text"] for r in pending
                 if lib.has_words(r["text"]) and lib.has_words(lib.VAR_RE.sub("", r["text"]))
                 and not r["text"].strip().startswith("$")]
        kind = "label"
    elif args.kind == "lines":
        items = [r["render"] for r in units["lines"]]
        kind = "line"
    elif args.kind == "quests":
        items = [r["render"] for r in units["quests"]]
        kind = "quest"
    else:
        items = [r["render"] for r in units["quoted"] if lib.has_words(r["render"])]
        kind = "line"
    if args.limit:
        items = items[:args.limit]
    run(kind, items, args.batch)


if __name__ == "__main__":
    main()
