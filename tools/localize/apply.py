# -*- coding: utf-8 -*-
"""Apply the Chinese localization to Jev/Envir and emit the MirDB payload.

Names are resolved by INDEX using the original English catalog, so a translated
token always points at exactly the record the English token pointed at.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

WORK = lib.WORK
JEV = lib.JEV
ENVIR = JEV / "Envir"
CONFIGS = JEV / "Configs"
OUT = lib.OUT

ITEM_CMDS = {"GIVEITEM", "TAKEITEM", "CHECKITEM", "CHECKHEROITEM"}
MON_CMDS = {"MONGEN", "MONGEN2", "GIVEPET", "REMOVEPET", "CHECKPET", "PETLEVEL",
            "CHECKMON", "CHECKEXACTMON"}

# The English source spells a few monster names wrong.  Those references point
# at a real record, so they are mapped to it instead of staying English (the
# surrounding quest prose already names the same monster in Chinese).
MON_ALIASES = {
    "darkdevouer": "darkdevourer",       # WasteLand/Red Cave/2: 怨恶
    "elecminotaur": "electricminotaur",  # PrajnaIsland/PranjaTemple/2: 电光牛魔
}


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


class Names:
    def __init__(self):
        jev = json.loads(((lib.DATA / "english_catalog.json")).read_text(encoding="utf-8"))
        self.items = jev["items"]
        self.monsters = jev["monsters"]
        self.maps = jev["maps"]
        self.npcs = jev["npcs"]
        self.quests = jev["quests"]
        self.item_zh = {int(k): v for k, v in lib.load("item_names.json").items()}
        self.mon_zh = {int(k): v for k, v in lib.load("monster_names.json").items()}
        self.map_zh = {int(k): v for k, v in lib.load("map_titles.json").items()}
        self.npc_zh = {int(k): v for k, v in lib.load("npc_names.json").items()}
        self.skill_zh = {int(k): v for k, v in lib.load("skill_names.json").items()}
        self.item_by = {}
        for x in self.items:
            self.item_by[norm(x["name"])] = x["index"]
        self.mon_by = {}
        for x in self.monsters:
            self.mon_by[norm(x["name"])] = x["index"]

    def item(self, token):
        idx = self.item_by.get(norm(token))
        return self.item_zh.get(idx) if idx is not None else None

    def mon(self, token):
        idx = self.mon_by.get(MON_ALIASES.get(norm(token), norm(token)))
        return self.mon_zh.get(idx) if idx is not None else None

    def reward_items(self, token):
        one = self.item(token)
        if one:
            return [one]
        out = []
        for suffix in ("(M)", "(F)"):
            idx = self.item_by.get(norm(token + suffix))
            if idx is not None:
                out.append(self.item_zh[idx])
        return out


TM = None


def tm():
    global TM
    if TM is None:
        TM = json.loads((lib.DATA / "tm.json").read_text(encoding="utf-8"))
    return TM


LABELS = None


def labels():
    global LABELS
    if LABELS is None:
        LABELS = dict(lib.load("name_lookup.json"))
    return LABELS


LINE_TM = None


def one_line(value: str) -> str:
    """A translation of one source line must stay one script line.

    The model sometimes answers with soft line breaks (trailing newline, or
    splitting a two-column menu row); NPC script line counts are part of the
    dialog layout and of the [TRADE] line-derived ids, so collapse them.
    """
    if "\n" not in value:
        return value
    parts = [part.strip() for part in value.split("\n") if part.strip()]
    return "  ".join(parts)


def line_tm():
    global LINE_TM
    if LINE_TM is None:
        LINE_TM = {key: one_line(value) for key, value in tm()["line"].items()}
    return LINE_TM


def translate_labels_only(line: str) -> str:
    toks = lib.tokenize(line)
    parts = []
    for tok in toks:
        if tok.kind == "text":
            parts.append(tok.raw)
            continue
        vis = tok.vis.strip()
        new = labels().get(vis, vis) if lib.has_words(lib.VAR_RE.sub("", tok.vis)) else vis
        sep = "" if tok.fixed else "/"
        if tok.kind == "link":
            parts.append(f"<<{new}{sep}{tok.rest}>>" if tok.rest is not None else f"<<{new}>>")
        elif tok.kind == "tag":
            parts.append(f"<{new}{sep}{tok.rest}>" if tok.rest is not None else f"<{new}>")
        else:
            parts.append(f"{{{new}{sep}{tok.rest}}}" if tok.rest is not None else f"{{{new}}}")
    return "".join(parts)


def translate_quoted(text: str) -> str:
    def repl(m):
        inner = m.group(1)
        if not inner.strip():
            return m.group(0)
        toks = lib.tokenize(inner)
        render, mapping = lib.render_placeholders(toks, labels())
        key = lib.render_placeholders(toks, {})[0]
        translated = line_tm().get(key)
        if translated:
            return '"' + lib.restore_placeholders(translated, mapping) + '"'
        return '"' + translate_labels_only(inner) + '"'
    return re.sub(r'"([^"]*)"', repl, text)


def translate_say(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return line
    lead = line[:len(line) - len(line.lstrip())]
    trail = line[len(line.rstrip()):]
    toks = lib.tokenize(stripped)
    mapping = lib.render_placeholders(toks, labels())[1]
    key = lib.render_placeholders(toks, {})[0]
    translated = line_tm().get(key)
    if translated:
        body = lib.restore_placeholders(translated, mapping)
    else:
        body = translate_labels_only(stripped)
    return lead + body + trail


def split_command(line: str):
    return re.split(r"(\s+)", line)


def translate_command(line: str, names: Names) -> str:
    line = translate_quoted(line)
    parts = line.split()
    if not parts:
        return line
    cmd = parts[0].upper()
    if cmd in ITEM_CMDS and len(parts) >= 2:
        new = names.item(parts[1])
        if new:
            parts[1] = new
            return _replace_field(line, 1, new)
    if cmd in MON_CMDS and len(parts) >= 2:
        new = names.mon(parts[1])
        if new:
            return _replace_field(line, 1, new)
    if cmd == "MONCLEAR" and len(parts) >= 4:
        new = names.mon(parts[3])
        if new:
            return _replace_field(line, 3, new)
    return line


def _replace_field(line: str, index: int, value: str) -> str:
    """Replace the index-th whitespace-separated field, preserving spacing."""
    spans = list(re.finditer(r"\S+", line))
    if index >= len(spans):
        return line
    m = spans[index]
    return line[:m.start()] + value + line[m.end():]


def rewrite_collection(root: Path, names: Names, stats):
    for path in sorted(root.rglob("*.txt")):
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines()
        out = []
        section = None
        state = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                upper = stripped.upper()
                out.append(line)
                if upper.startswith(("#SAY", "#ELSESAY")):
                    state = "say"
                elif upper.startswith(("#ACT", "#ELSEACT", "#IF")):
                    state = "cmd"
                continue
            if stripped.startswith("["):
                if stripped.startswith("[@"):
                    # A page header implicitly opens a SAY block.
                    section = None
                    state = "say"
                else:
                    section = stripped.upper()
                    state = None
                out.append(line)
                continue
            if state == "say" and stripped:
                stats["say"] += 1
                out.append(translate_say(line))
                continue
            if state == "cmd" and stripped:
                stats["cmd"] += 1
                out.append(translate_command(line, names))
                continue
            if section in ("[TRADE]", "[RECIPE]", "[TYPES]") and stripped and not stripped.startswith("//"):
                if section == "[TYPES]":
                    out.append(line)
                    continue
                token = stripped.split()[0]
                new = names.item(token)
                if new:
                    stats["shop"] += 1
                    out.append(_replace_field(line, 0, new))
                    continue
                out.append(line)
                continue
            out.append(line)
        text = "\n".join(out)
        if original.endswith("\n"):
            text += "\n"
        if text != original:
            path.write_text(text, encoding="utf-8")
            stats["files"] += 1


def rewrite_drops(names: Names, stats):
    drop_root = ENVIR / "Drops"
    for path in sorted(drop_root.rglob("*.txt")):
        original = path.read_text(encoding="utf-8")
        changed = False
        out = []
        for line in original.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith((";", "#", "{")) or stripped == "}":
                out.append(line)
                continue
            parts = stripped.split()
            if len(parts) < 2:
                out.append(line)
                continue
            if parts[1].upper().startswith("GROUP"):
                out.append(line)
                continue
            if parts[1].lower() == "gold":
                out.append(line)
                continue
            new = names.item(parts[1])
            if new and new != parts[1]:
                stats["drops"] += 1
                out.append(_replace_field(line, 1, new))
                changed = True
            else:
                if new is None:
                    stats["drop_missing"].add(parts[1])
                out.append(line)
        text = "\n".join(out)
        if original.endswith("\n"):
            text += "\n"
        if changed:
            path.write_text(text, encoding="utf-8")


def rename_monster_drops(names: Names, stats):
    drop_root = ENVIR / "Drops"
    for monster in names.monsters:
        if monster.get("dropPath"):
            continue
        old = drop_root / (monster["name"] + ".txt")
        new = drop_root / (names.mon_zh[monster["index"]] + ".txt")
        if old.exists():
            if new.exists() and new != old:
                raise SystemExit(f"drop rename collision: {old} -> {new}")
            old.rename(new)
            stats["renamed"] += 1


def rewrite_recipes(names: Names, stats):
    root = ENVIR / "Recipe"
    for path in sorted(root.glob("*.txt")):
        old_name = path.stem
        idx = names.item_by.get(norm(old_name))
        new_name = names.item_zh[idx] if idx is not None else None
        original = path.read_text(encoding="utf-8")
        out = []
        mode = "ingredients"
        for line in original.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                mode = stripped[1:-1].lower()
                out.append(line)
                continue
            if stripped and not stripped.startswith("//") and mode in ("tools", "ingredients"):
                token = stripped.split()[0]
                if token.lower() not in ("amount", "chance", "gold"):
                    new = names.item(token)
                    if new:
                        stats["recipe_items"] += 1
                        out.append(_replace_field(line, 0, new))
                        continue
            out.append(line)
        text = "\n".join(out)
        if original.endswith("\n"):
            text += "\n"
        target = path
        if new_name and new_name != old_name:
            target = root / (new_name + ".txt")
            if target.exists() and target != path:
                raise SystemExit(f"recipe rename collision: {path} -> {target}")
            stats["recipe_files"] += 1
        if text != original or target != path:
            target.write_text(text, encoding="utf-8")
            if target != path:
                path.unlink()


QUEST_PROSE = {"Description", "TaskDescription", "ReturnDescription", "Completion"}
QUEST_ITEMS = {"ItemTasks", "CarryItems"}
QUEST_REWARDS = {"FixedRewards", "SelectRewards"}


def rewrite_quests(names: Names, stats):
    translated = tm()["quest"]
    for path in sorted((ENVIR / "Quests").rglob("*.txt")):
        original = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(ENVIR))
        out = []
        section = None
        buf = []

        def flush():
            # Prose sections are translated as a whole block: the TM key joins
            # the non-empty source lines with "\n", so a blank line inside the
            # section must not split the lookup.
            if section in QUEST_PROSE and buf:
                body = [x for x in buf if x.strip()]
                text = "\n".join(x.strip() for x in body)
                toks = lib.tokenize(text)
                render, mapping = lib.render_placeholders(toks, labels())
                key, _ = lib.render_placeholders(toks, {})
                zh = translated.get(key)
                if zh:
                    stats["quest_prose"] += 1
                    out.extend(lib.restore_placeholders(zh, mapping).split("\n"))
                else:
                    stats["quest_prose_missing"].append((rel, section))
                    out.extend(buf)
                if buf and not buf[-1].strip():
                    out.append("")
                buf.clear()
            elif buf:
                out.extend(buf)
                buf.clear()

        for line in original.splitlines():
            stripped = line.strip()
            if stripped.startswith("[@") and stripped.endswith("]"):
                flush()
                section = stripped[2:-1]
                out.append(line)
                continue
            if stripped.startswith("["):
                flush()
                section = None
                out.append(line)
                continue
            if section in QUEST_PROSE:
                if stripped.startswith("//"):
                    flush()
                    out.append(line)
                    continue
                buf.append(line)
                continue
            if not stripped or stripped.startswith("//"):
                flush()
                out.append(line)
                continue
            if section == "KillTasks":
                token = stripped.split()[0]
                new = names.mon(token)
                if new:
                    stats["quest_kill"] += 1
                    out.append(translate_quoted(_replace_field(line, 0, new)))
                else:
                    stats["quest_kill_missing"].add(token)
                    out.append(translate_quoted(line))
                continue
            if section in QUEST_ITEMS:
                token = stripped.split()[0]
                new = names.item(token)
                if new:
                    stats["quest_item"] += 1
                    out.append(translate_quoted(_replace_field(line, 0, new)))
                else:
                    stats["quest_item_missing"].add(token)
                    out.append(translate_quoted(line))
                continue
            if section in QUEST_REWARDS:
                token = stripped.split()[0]
                new = names.reward_items(token)
                if new:
                    stats["quest_reward"] += 1
                    if len(new) == 1:
                        out.append(translate_quoted(_replace_field(line, 0, new[0])))
                    else:
                        # Preserve the legacy (M)/(F) fallback: emit one line per gender.
                        for name in new:
                            out.append(translate_quoted(_replace_field(line, 0, name)))
                else:
                    stats["quest_reward_missing"].add(token)
                    out.append(translate_quoted(line))
                continue
            out.append(translate_quoted(line))
        flush()
        text = "\n".join(out)
        if original.endswith("\n"):
            text += "\n"
        if text != original:
            path.write_text(text, encoding="utf-8")
            stats["quest_files"] += 1


def main():
    names = Names()
    stats = {
        "say": 0, "cmd": 0, "shop": 0, "files": 0, "drops": 0,
        "drop_missing": set(), "renamed": 0, "recipe_items": 0, "recipe_files": 0,
        "quest_prose": 0, "quest_prose_missing": [], "quest_kill": 0,
        "quest_kill_missing": set(), "quest_item": 0, "quest_item_missing": set(),
        "quest_reward": 0, "quest_reward_missing": set(), "quest_files": 0,
    }
    rewrite_collection(ENVIR / "NPCs", names, stats)
    rewrite_collection(ENVIR / "SystemScripts", names, stats)
    rewrite_collection(ENVIR / "Events", names, stats)
    rewrite_drops(names, stats)
    rename_monster_drops(names, stats)
    rewrite_recipes(names, stats)
    rewrite_quests(names, stats)
    report = {k: (sorted(v) if isinstance(v, set) else v) for k, v in stats.items()}
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "apply_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    for key, value in report.items():
        if isinstance(value, list) and value:
            print(f"{key}: {len(value)} {value[:10]}")
        else:
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
