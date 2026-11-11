"""Parse the Markdown rule documents into structured records.

The Markdown files under docs/rules/ are the single source of truth.
Nothing in this module hardcodes card meanings, spread positions or scenes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = ROOT / "docs" / "rules"

STAGES = {
    "scene-select", "question", "ritual-prep", "shuffle-cut", "draw",
    "record", "interpret", "close", "all",
}

SUITS = {"权杖": "wands", "圣杯": "cups", "宝剑": "swords", "星币": "pentacles"}
RANKS = {
    "Ace": "ace", "2": "02", "3": "03", "4": "04", "5": "05",
    "6": "06", "7": "07", "8": "08", "9": "09", "10": "10",
    "侍者": "page", "骑士": "knight", "王后": "queen", "国王": "king",
}
CN_NUM = {
    "Ace": "王牌", "2": "二", "3": "三", "4": "四", "5": "五",
    "6": "六", "7": "七", "8": "八", "9": "九", "10": "十",
}
COURT_NUM = {"侍者": 11, "骑士": 12, "王后": 13, "国王": 14}

SUIT_RE = re.compile(r"^(权杖|圣杯|宝剑|星币)\s*(Ace|[2-9]|10|侍者|骑士|王后|国王)$")


def _cells(line: str) -> list[str] | None:
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [c.strip() for c in s.strip("|").split("|")]


def _inline_list(value: str) -> list[str]:
    v = value.strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip("'\"") for x in v[1:-1].split(",") if x.strip()]
    return [v] if v else []


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, text
    fm: dict[str, Any] = {}
    block = lines[1:end]
    i = 0
    while i < len(block):
        line = block[i]
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if key in ("stage", "scenes", "tags"):
            fm[key] = _inline_list(val)
        elif key == "source":
            if val == "[]":
                fm[key] = []
            else:
                urls: list[str] = []
                j = i + 1
                while j < len(block) and (
                    block[j].lstrip().startswith("- ") or not block[j].strip()
                ):
                    item = block[j].strip()
                    if item.startswith("- "):
                        urls.append(item[2:].strip())
                    j += 1
                fm[key] = urls
                i = j - 1
        else:
            fm[key] = val
        i += 1
    return fm, "\n".join(lines[end + 1:]).strip()


def split_chunks(body: str, title: str) -> list[tuple[str, str]]:
    """Split on level-2 headings; tables are never broken apart."""
    blocks: list[tuple[str, str]] = []
    current_title = title
    buffer: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if buffer and "\n".join(buffer).strip():
                blocks.append((current_title, "\n".join(buffer).strip()))
            current_title = line[3:].strip()
            buffer = [line]
        else:
            buffer.append(line)
    if buffer and "\n".join(buffer).strip():
        blocks.append((current_title, "\n".join(buffer).strip()))
    return blocks


def load_documents() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for path in sorted(RULES_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(raw)
        docs.append({
            "id": fm.get("id") or path.stem,
            "title": fm.get("title") or path.stem,
            "file_path": str(path),
            "stages": fm.get("stage", ["all"]),
            "scenes": fm.get("scenes", ["all"]),
            "tags": fm.get("tags", []),
            "version": str(fm.get("version", "1.0")),
            "updated": fm.get("updated", ""),
            "source": fm.get("source", []),
            "raw": raw,
            "body": body,
        })
    return docs


def parse_cards(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {d["id"]: d for d in docs}
    cards: list[dict[str, Any]] = []

    for line in by_id["RULE-01"]["body"].splitlines():
        cells = _cells(line)
        if not cells or len(cells) < 7:
            continue
        if not re.fullmatch(r"(?:0|[IVX]+)", cells[0]):
            continue
        number = len([c for c in cards if c["arcana"] == "major"])
        cards.append({
            "card_id": f"major-{number:02d}",
            "name": cells[1],
            "label": cells[1],
            "arcana": "major",
            "suit": None,
            "rank": None,
            "number": number,
            "upright": cells[3],
            "reversed": cells[4],
            "doc_id": "RULE-01",
        })

    for line in by_id["RULE-02"]["body"].splitlines():
        cells = _cells(line)
        if not cells or len(cells) < 2:
            continue
        m = SUIT_RE.fullmatch(cells[0])
        if not m:
            continue
        suit_zh, rank_zh = m.groups()
        suit = SUITS[suit_zh]
        rank = RANKS[rank_zh]
        label = f"{suit_zh}{CN_NUM.get(rank_zh, rank_zh)}"
        upright = cells[1]
        if rank == "knight" and len(cells) >= 3:
            upright = f"{cells[1]} / 阴影：{cells[2]}"
        if rank_zh in COURT_NUM:
            number = COURT_NUM[rank_zh]
        else:
            number = 1 if rank_zh == "Ace" else int(rank_zh)
        cards.append({
            "card_id": f"{suit}-{rank}",
            "name": f"{suit_zh} {rank_zh}" if rank_zh not in COURT_NUM else cells[0],
            "label": label,
            "arcana": "minor",
            "suit": suit,
            "rank": rank,
            "number": number,
            "upright": upright,
            "reversed": "",
            "doc_id": "RULE-02",
        })

    if len(cards) != 78:
        raise ValueError(f"规则文档解析出 {len(cards)} 张牌，应为 78 张；请检查 RULE-01/02 表格格式")
    ids = [c["card_id"] for c in cards]
    if len(set(ids)) != 78:
        raise ValueError("牌 ID 存在重复，请检查 RULE-01/02 表格")
    return cards


PROFILE_FIELDS = {
    "名称": "name", "英文": "english", "编号": "number", "组别": "arcana",
    "对应": "correspondence", "关键词": "keywords", "图像": "imagery",
    "正位": "upright", "逆位": "reversed", "象征": "symbolism",
    "姻缘": "love", "工作": "career", "升学": "study",
}


def parse_card_profiles(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse RULE-10 / RULE-11 card compendium into one record per card."""
    profiles: list[dict[str, Any]] = []
    for doc in docs:
        if doc["id"] not in ("RULE-10", "RULE-11"):
            continue
        for section in re.split(r"(?=^## [a-z]+-)", doc["body"], flags=re.M):
            lines = section.splitlines()
            if not lines:
                continue
            head = re.match(
                r"^## ([a-z]+-(\d{2}|ace|page|knight|queen|king))\s*$", lines[0]
            )
            if not head:
                continue
            item: dict[str, Any] = {"card_id": head.group(1), "source": doc["id"]}
            for line in lines[1:]:
                m = re.match(r"^- ([^:：]+)[:：]\s*(.+)$", line.strip())
                if m and m.group(1) in PROFILE_FIELDS:
                    item[PROFILE_FIELDS[m.group(1)]] = m.group(2).strip()
            profiles.append(item)
    if len(profiles) != 78:
        raise ValueError(f"牌义详解解析出 {len(profiles)} 张，应为 78 张；请检查 RULE-10/11 格式")
    ids = [p["card_id"] for p in profiles]
    if len(set(ids)) != 78:
        raise ValueError("牌义详解存在重复 card_id")
    for p in profiles:
        missing = [k for k in PROFILE_FIELDS.values() if not p.get(k)]
        if missing:
            raise ValueError(f"{p['card_id']} 缺少字段：{missing}")
    return profiles


def parse_spreads(docs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    body = {d["id"]: d["body"] for d in docs}["RULE-03"]
    spreads: list[dict[str, Any]] = []
    positions: list[dict[str, Any]] = []
    for section in re.split(r"(?=^## SP-)", body, flags=re.M):
        lines = section.splitlines()
        if not lines:
            continue
        head = re.match(r"^## (SP-\d+)\s+(.+)$", lines[0])
        if not head:
            continue
        spread_id, name = head.group(1), head.group(2).strip()
        meta = next((l for l in lines if l.strip().startswith("- 牌数")), "")
        diff = re.search(r"难度\s+([^\s·]+)", meta)
        suitable = re.search(r"适用[:：]\s*(.+)", meta)
        pos_rows: list[dict[str, Any]] = []
        for line in lines:
            cells = _cells(line)
            if not cells or len(cells) < 3:
                continue
            if not re.fullmatch(r"\d+", cells[0]):
                continue
            pos_rows.append({
                "spread_id": spread_id,
                "seq": int(cells[0]),
                "name": cells[1],
                "meaning": cells[2],
            })
        pos_rows.sort(key=lambda p: p["seq"])
        if not pos_rows:
            continue
        spreads.append({
            "spread_id": spread_id,
            "name": name,
            "card_count": len(pos_rows),
            "difficulty": diff.group(1) if diff else "",
            "suitable": suitable.group(1).strip() if suitable else "",
            "doc_id": "RULE-03",
        })
        positions.extend(pos_rows)
    return spreads, positions


def parse_scenes(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    body = {d["id"]: d["body"] for d in docs}["RULE-08"]
    scenes: list[dict[str, Any]] = []
    for line in body.splitlines():
        cells = _cells(line)
        if not cells or len(cells) < 6:
            continue
        m = re.fullmatch(r"`([a-z]+)`", cells[0])
        if not m:
            continue
        scenes.append({
            "scene_id": m.group(1),
            "name": cells[1],
            "topics": cells[2],
            "recommended": cells[3],
            "focus": cells[4],
            "tags": cells[5],
        })
    return scenes


def parse_templates(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    body = {d["id"]: d["body"] for d in docs}["RULE-05"]
    templates: list[dict[str, Any]] = []
    scene_id: str | None = None
    for line in body.splitlines():
        if line.startswith("## "):
            scene_id = None
        elif line.startswith("### "):
            m = re.search(r"scene:\s*([a-z]+)", line)
            scene_id = m.group(1) if m else None
        elif scene_id:
            m = re.match(r"^\d+\.\s*(.+)$", line.strip())
            if m:
                templates.append({"scene_id": scene_id, "seq": len(templates) + 1, "text": m.group(1).strip()})
    return templates


def parse_routes(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    body = {d["id"]: d["body"] for d in docs}["RULE-08"]
    routes: list[dict[str, Any]] = []
    for line in body.splitlines():
        cells = _cells(line)
        if not cells or len(cells) < 4 or cells[0] not in STAGES:
            continue
        routes.append({
            "stage": cells[0],
            "required": ",".join(re.findall(r"RULE-\d+", cells[1])),
            "optional": ",".join(re.findall(r"RULE-\d+", cells[2])),
            "always": ",".join(re.findall(r"RULE-\d+", cells[3])),
        })
    return routes


def parse_ritual_steps(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    body = {d["id"]: d["body"] for d in docs}["RULE-04"]
    steps: list[dict[str, Any]] = []
    for section in re.split(r"(?=^## 阶段 )", body, flags=re.M):
        lines = section.splitlines()
        if not lines:
            continue
        head = re.match(r"^## 阶段\s*(\d+)\s*·\s*(.+)$", lines[0])
        if not head:
            continue
        seq = int(head.group(1))
        name = head.group(2).strip()
        sm = re.search(r"（([a-z-]+)）\s*$", name)
        stage = sm.group(1) if sm else "ritual-prep"
        if sm:
            name = name[:sm.start()].strip()
        text = "\n".join(lines[1:]).strip()
        steps.append({"seq": seq, "name": name, "stage": stage, "text": text})
    return steps


def parse_all() -> dict[str, Any]:
    docs = load_documents()
    if not docs:
        raise FileNotFoundError(f"未在 {RULES_DIR} 找到规则文档")
    chunks: list[dict[str, Any]] = []
    for doc in docs:
        for section, text in split_chunks(doc["body"], doc["title"]):
            chunks.append({
                "doc_id": doc["id"], "section": section, "text": text,
                "stages": doc["stages"], "scenes": doc["scenes"],
                "tags": doc["tags"], "version": doc["version"],
            })
    spreads, positions = parse_spreads(docs)
    return {
        "documents": docs,
        "chunks": chunks,
        "cards": parse_cards(docs),
        "card_profiles": parse_card_profiles(docs),
        "spreads": spreads,
        "positions": positions,
        "scenes": parse_scenes(docs),
        "templates": parse_templates(docs),
        "routes": parse_routes(docs),
        "ritual_steps": parse_ritual_steps(docs),
    }


def dump_summary(data: dict[str, Any]) -> str:
    return json.dumps({
        "documents": len(data["documents"]),
        "chunks": len(data["chunks"]),
        "cards": len(data["cards"]),
        "card_profiles": len(data["card_profiles"]),
        "spreads": len(data["spreads"]),
        "positions": len(data["positions"]),
        "scenes": len(data["scenes"]),
        "templates": len(data["templates"]),
        "routes": len(data["routes"]),
        "ritual_steps": len(data["ritual_steps"]),
    }, ensure_ascii=False)
