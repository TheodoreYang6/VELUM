"""Build the material handed to the model for the final verdict and follow-ups.

The feed is deliberately organised as three human-readable blocks, not a nested
JSON record:

  一、问卜者的原始问题   the untouched question the querent wrote down
  二、本次抽牌状况       spread, positions, cards, orientations, structure
  三、解读参考资料       interpretation method, position definitions, and the
                         full documented meaning of every card that was drawn

Rule documents (docs/rules/*.md) remain the single source of truth. This module
only reads them; it never invents card meanings.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

SUITS = {
    "wands": ("权杖", "火", "行动、创造与推进"),
    "cups": ("圣杯", "水", "情感、关系与内在感受"),
    "swords": ("宝剑", "风", "思维、沟通与判断"),
    "pentacles": ("星币", "土", "资源、工作与现实落地"),
}
NUMEROLOGY = {
    1: "Ace · 元素纯粹潜能、新开端，能量刚到场尚需载体",
    2: "2 · 选择、二元与结盟，常指尚未落定的决定",
    3: "3 · 成长、协作与初步成果",
    4: "4 · 稳定、结构与暂歇，也可能过早停下",
    5: "5 · 冲突、失落与变动，是周期中点的调整",
    6: "6 · 和谐、修复与交换，从失衡回升",
    7: "7 · 检验、评估与内在功课，外显进展不明显",
    8: "8 · 推进、熟练与秩序，节奏加快",
    9: "9 · 顶点、临近完成与自省",
    10: "10 · 圆满、极致与转向，常同时含完成与过载",
    11: "侍者 · 学习者、消息、新端倪",
    12: "骑士 · 行动、追求与变动",
    13: "王后 · 内在掌控、滋养与共情",
    14: "国王 · 外在掌控、权威与结构化",
}

# Kept as a safety net for installations whose rule index is incomplete.
METHOD_FALLBACK = (
    "单张牌按四层法读：第一印象 → 图像细节 → 所在位置 → 花色与数字阶段，"
    "之后再结合问题与相邻牌。逆位采用能量层级说：能量仍在，只是表达受阻、延迟、"
    "内化或尚未成形，不是反义也不是凶兆。叙事综合须把各位置串成时间线或因果链，"
    "找出核心张力与重复符号，用一句话概括，再落回原问题给出可参考的行动方向。"
    "结构观察（大牌占比、主导花色、重复数字、逆位比例）只作线索，不单独构成结论。"
)
ETHICS_FALLBACK = (
    "本系统依 Rider-Waite-Smith 牌义与 RULE-12 传统对应表作出占断，属占卜性质的解释，"
    "不是事实保证，也不替代医疗、法律、财务等专业人士的判断。对应体系存在流派差异，"
    "结论由问卜者自行取舍。允许明确措辞与吉凶判断；寻物、时间、第三方动向、"
    "健康／法律／财务类问题均可作答。每条占断须回指具体牌、位置或对应表条目，"
    "牌面不足时说明「牌面未指向明确……」。逆位按能量层级说，负面牌不恐吓。"
)
CORRESPONDENCE_FALLBACK = (
    "古典占问对应表（摘要）：方位按四花色元素对应（权杖火／南或东、圣杯水／西、"
    "宝剑风／东或北、星币土／北）；时间按花色速度（权杖最快、星币最慢）与数字阶段推导，"
    "数字不直接等于日历单位；人物按宫廷牌角色与大阿卡纳原型。均为传统象征约定，流派间不一致。"
)


def _load(conn: sqlite3.Connection, session_id: str) -> dict[str, Any] | None:
    """Load everything needed to describe one reading, in a single pass."""
    row = conn.execute(
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if not row:
        return None
    payload = json.loads(row["payload"])
    reading = payload.get("reading")
    if not reading:
        return None
    scene = conn.execute(
        "SELECT * FROM scenes WHERE scene_id = ?", (row["scene_id"],)
    ).fetchone()
    return {
        "row": row,
        "payload": payload,
        "reading": reading,
        "scene": scene,
        "positions": {
            p["seq"]: dict(p) for p in conn.execute(
                "SELECT * FROM positions WHERE spread_id = ? ORDER BY seq",
                (row["spread_id"],),
            ).fetchall()
        },
        "cards": {
            r["card_id"]: dict(r)
            for r in conn.execute("SELECT * FROM cards").fetchall()
        },
        "profiles": {
            r["card_id"]: dict(r)
            for r in conn.execute("SELECT * FROM card_profiles").fetchall()
        },
        # 逐牌详解只有姻缘 / 工作 / 升学三列专属提示（RULE-10/11 的 13 字段契约）。
        # 新增场景没有专属列，绝不能借「姻缘」列冒充，否则会把关系解读混进
        # 自我、创作等场景——这是事实层污染。缺失时置 None，由通用牌义 +
        # 场景侧重承担，并在喂料中显式标注。
        "scene_field": {"love": "love", "career": "career", "study": "study"}.get(
            row["scene_id"]
        ),
    }


def _doc_text(conn: sqlite3.Connection, doc_id: str, limit: int) -> str:
    """Join every chunk of a rule doc, in document order."""
    rows = conn.execute(
        "SELECT text FROM chunks WHERE doc_id = ? ORDER BY chunk_id", (doc_id,)
    ).fetchall()
    text = "\n".join(r["text"].strip() for r in rows if r["text"].strip())
    return text[:limit]


def _table_rows(conn: sqlite3.Connection, card_name: str, card_label: str) -> list[str]:
    """Exact recall of the concise meaning rows for one card."""
    rows = conn.execute(
        "SELECT doc_id, section, text FROM chunks "
        "WHERE doc_id IN ('RULE-01','RULE-02','RULE-09')"
    ).fetchall()
    found: list[str] = []
    for row in rows:
        for line in row["text"].splitlines():
            line = line.strip()
            if not line.startswith("|") or "---" in line:
                continue
            if card_name in line or (card_label and card_label in line):
                if any(k in line for k in ("牌名", "编号", "花色", "数字", "组合")):
                    continue
                tag = f"[{row['doc_id']} § {row['section']}] {line}"
                if tag not in found:
                    found.append(tag)
    return found[:4]


def _question_block(base: dict[str, Any]) -> str:
    row = base["row"]
    scene = base["scene"]
    lines = [row["question"].strip()]
    if scene:
        lines.append(f"择定的场景：{scene['name']}")
        if scene["focus"]:
            lines.append(f"该场景的侧重：{scene['focus']}")
    issues = base["payload"].get("question_issues") or []
    if issues:
        lines.append("提问时系统提示过的措辞留意点：" + "；".join(issues[:2]))
    lines.append(
        "这是问卜者亲手写下的原话，请保留其原意，不要替他／她改写问题，"
        "整段解读最终要落回这里。"
    )
    return "\n".join(lines)


def _draw_block(base: dict[str, Any]) -> str:
    row, reading = base["row"], base["reading"]
    lines = [
        f"牌阵：{reading['record']['spread']}（共 {reading['structure']['total']} 张牌）",
        f"逆位设置：{'启用' if row['use_reversed'] else '不启用（所有牌按正位理解）'}",
        f"牌面来源：{'线上抽卡' if base['payload'].get('draw_source') == 'online' else '现实仪式，由问卜者亲手抽出并录入'}",
        "",
    ]
    for entry in reading["positions"]:
        card = base["cards"].get(entry["card_id"], {})
        pos = base["positions"].get(entry["seq"], {})
        suit_zh, element, domain = SUITS.get(card.get("suit"), ("", "", ""))
        lines.append(
            f"位置 {entry['seq']} · {entry['position']}｜该位置关注："
            f"{pos.get('meaning') or entry.get('position_meaning') or '—'}"
        )
        lines.append(
            f"  抽到：{entry['label']}（{entry['name']}）· "
            f"{'逆位' if entry['reversed'] else '正位'}"
        )
        if card.get("arcana") == "major":
            lines.append("  类别：大阿卡纳 · 原型性议题")
        elif suit_zh:
            lines.append(f"  类别：小阿卡纳 · {suit_zh}（{element}）｜领域：{domain}")
        stage = NUMEROLOGY.get(card.get("number"), "")
        if stage:
            lines.append(f"  数字阶段：{stage}")
        lines.append(f"  关键词：{entry['keywords']}")
        lines.append(f"  逐位初读：{entry['reading']}")
        if entry.get("note"):
            lines.append(f"  占卜师现场记录：{entry['note']}")
        lines.append("")
    observations = reading["structure"].get("observations") or []
    if observations:
        lines.append("全牌阵结构观察（仅作线索，不单独构成结论）：")
        lines.extend(f"  - {o}" for o in observations)
    return "\n".join(lines).rstrip()


def _card_reference(
    conn: sqlite3.Connection, base: dict[str, Any], per_card_limit: int
) -> str:
    """Full documented meaning of each card actually drawn, including the
    detailed 13-field profile from RULE-10 / RULE-11."""
    blocks: list[str] = []
    profile_fields = [
        ("对应", "correspondence"), ("关键词", "keywords"), ("图像", "imagery"),
        ("正位", "upright"), ("逆位", "reversed"), ("象征", "symbolism"),
    ]
    if base["scene_field"]:
        profile_fields.append(("本场景提示", base["scene_field"]))
    for entry in base["reading"]["positions"]:
        card = base["cards"].get(entry["card_id"])
        if not card:
            continue
        lines = [
            f"── {entry['label']}（{entry['name']} / {entry['card_id']}）· "
            f"位置 {entry['seq']} {entry['position']} · "
            f"{'逆位' if entry['reversed'] else '正位'} ──"
        ]
        concise = _table_rows(conn, entry["name"], entry["label"])
        if concise:
            lines.append("简明牌义（牌义表原文行）：")
            lines.extend(f"  {r}" for r in concise)
        profile = base["profiles"].get(entry["card_id"])
        if profile:
            lines.append("逐牌详解（本体系牌义详解文档）：")
            for label, key in profile_fields:
                value = (profile.get(key) or "").strip()
                if value:
                    lines.append(f"  {label}：{value}")
        if not concise and not profile:
            lines.append(f"  简明牌义：{card.get('upright', '')}")
            if card.get("reversed"):
                lines.append(f"  逆位：{card['reversed']}")
        block = "\n".join(lines)
        blocks.append(block[:per_card_limit])
    return "\n\n".join(blocks)


def _reference_text(conn: sqlite3.Connection, base: dict[str, Any], budget: int = 15000) -> str:
    """解读参考资料：解读方法 + 牌位定义 + 每张牌的含义 + 结构口径 + 伦理边界."""
    reading = base["reading"]
    spread_id = reading["record"].get("spread_id", "")

    method = _doc_text(conn, "RULE-06", 4200) or METHOD_FALLBACK
    ethics = _doc_text(conn, "RULE-07", 2600) or ETHICS_FALLBACK
    # 古典占问范式的事实层：寻物 / 时间 / 人物对应表，占断须回指此表
    correspondence = _doc_text(conn, "RULE-12", 5200) or CORRESPONDENCE_FALLBACK

    pos_rows = conn.execute(
        "SELECT section, text FROM chunks WHERE doc_id = 'RULE-03' "
        "AND section LIKE ? ORDER BY chunk_id LIMIT 2",
        (f"%{spread_id}%",),
    ).fetchall() if spread_id else []
    position_lines = [
        f"位置 {seq} · {p['name']}｜{p['meaning']}"
        for seq, p in sorted(base["positions"].items())
    ]
    position_text = "本次牌阵的位置定义：\n" + "\n".join(position_lines)
    if pos_rows:
        position_text += "\n\n牌阵文档中的位置表原文：\n" + "\n".join(
            r["text"].strip()[:1400] for r in pos_rows
        )

    dignity_parts: list[str] = []
    for doc_id in ("RULE-09", "RULE-02"):
        for r in conn.execute(
            "SELECT text FROM chunks WHERE doc_id = ? AND section LIKE '%元素尊严%' "
            "ORDER BY chunk_id LIMIT 2", (doc_id,),
        ).fetchall():
            dignity_parts.append(r["text"].strip()[:1400])
    structure = "\n\n".join(dignity_parts)
    scene = base["scene"]
    scene_text = ""
    if scene:
        scene_text = "\n\n".join(
            x for x in (
                f"场景名称：{scene['name']}",
                f"场景侧重：{scene['focus'] or '—'}",
                f"常见议题：{scene['topics'] or '—'}",
                "（本场景无专属逐牌场景提示字段，请以通用牌义与上述场景侧重为准，"
                "不得借用姻缘／工作／升学任一场景的提示。）" if not base["scene_field"] else "",
            ) if x
        )

    fixed = [
        "§ A · 解读方法（本体系标准，写解读时务必遵循）\n" + method,
        "§ B · 本次牌阵与位置定义\n" + position_text,
    ]
    if structure:
        fixed.append("§ D · 元素尊严与牌组关系（原文）\n" + structure)
    fixed.append("§ D2 · 古典占问对应表（寻物方位 / 时间速度 / 人物原型，占断事实依据）\n" + correspondence)
    if scene_text:
        fixed.append("§ E · 本次场景侧重\n" + scene_text)
    fixed.append("§ F · 知情说明与作答规范（常驻，不可省略）\n" + ethics)

    card_count = max(1, len(reading["positions"]))
    used = sum(len(x) for x in fixed)
    remaining = max(3600, budget - used - 400)
    per_card = max(520, remaining // card_count)
    cards_text = _card_reference(conn, base, per_card)
    fixed.insert(2, "§ C · 本次抽到的每一张牌 · 牌义与逐牌详解\n" + cards_text)
    return "\n\n".join(fixed)[:budget]


def build_feed(conn: sqlite3.Connection, session_id: str) -> dict[str, Any] | None:
    """三段式喂料。最终评定与追问共用同一份，确保背景恒定不漂移。"""
    base = _load(conn, session_id)
    if not base:
        return None
    reading = base["reading"]
    verdict_out = (reading.get("verdict") or {}).get("output") or {}
    digest_parts = [
        str(verdict_out.get("verdict") or ""),
        str(verdict_out.get("theme") or verdict_out.get("core_theme") or ""),
        " ".join(str(p) for p in (verdict_out.get("paragraphs") or [])[:2]),
        str(verdict_out.get("summary") or ""),
    ]
    digest = " ".join(p for p in digest_parts if p).strip()[:900]
    if not digest:
        digest = " ".join(reading.get("synthesis") or [])[:900]
    return {
        "question": _question_block(base),
        "draw": _draw_block(base),
        "reference": _reference_text(conn, base),
        "verdict_digest": digest,
        "meta": {
            "scene": base["scene"]["name"] if base["scene"] else base["row"]["scene_id"],
            "scene_id": base["row"]["scene_id"],
            "question": base["row"]["question"],
            "spread": reading["record"]["spread"],
            "spread_id": reading["record"].get("spread_id", ""),
            "use_reversed": bool(base["row"]["use_reversed"]),
            "boundary": reading.get("boundary", ""),
            "card_names": [p["label"] for p in reading["positions"]],
            "position_names": [p["position"] for p in reading["positions"]],
        },
    }


# ---------------------------------------------------------------------------
# Legacy helpers kept for other callers / older sessions.
# ---------------------------------------------------------------------------
def grounded_excerpts(conn: sqlite3.Connection, session_id: str) -> str:
    """Backward-compatible alias: the reference block of the three-part feed."""
    base = _load(conn, session_id)
    if not base:
        return ""
    return _reference_text(conn, base)


def build_context(conn: sqlite3.Connection, session_id: str) -> dict[str, Any]:
    """Structured record, still used by rule-driven fallbacks and diagnostics."""
    base = _load(conn, session_id)
    if not base:
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return {"error": "会话不存在" if not row else "尚未生成结构化解读"}
    row, reading = base["row"], base["reading"]
    scene = base["scene"]
    profiles: list[dict[str, Any]] = []
    for entry in reading["positions"]:
        card = base["cards"].get(entry["card_id"])
        pos = base["positions"].get(entry["seq"], {})
        if not card:
            continue
        suit_zh, element, domain = SUITS.get(card["suit"], ("—", "原型", "人生重大议题"))
        profile = base["profiles"].get(entry["card_id"], {})
        profiles.append({
            "位置": f"{entry['seq']} · {pos.get('name', '')}｜{pos.get('meaning', '')}",
            "牌": f"{card['label']}（{card['name']}）· {'逆位' if entry['reversed'] else '正位'}",
            "类别": "大阿卡纳 · 原型性议题" if card["arcana"] == "major"
                    else f"小阿卡纳 · {suit_zh}（{element}）｜领域：{domain}",
            "数字阶段": NUMEROLOGY.get(card["number"], ""),
            "正位关键词": card["upright"],
            "逆位说明": card["reversed"] or "能量仍在，但表达可能受阻、延迟或内化（RULE-06 能量层级说）",
            "牌面详解": {
                "图像": profile.get("imagery", ""),
                "正位": profile.get("upright", ""),
                "逆位": profile.get("reversed", ""),
                "象征": profile.get("symbolism", ""),
                "对应": profile.get("correspondence", ""),
                **({"本场景提示": profile.get(base["scene_field"], "")}
                   if base["scene_field"] else {}),
            },
            "逐位初读": entry["reading"],
        })
    return {
        "场景": scene["name"] if scene else row["scene_id"],
        "场景侧重": scene["focus"] if scene else "",
        "书面问题": row["question"],
        "牌阵": reading["record"]["spread"],
        "逆位设置": "启用" if row["use_reversed"] else "不启用",
        "抽卡来源": "线上抽卡（数字模拟）" if base["payload"].get("draw_source") == "online" else "现实仪式录入",
        "逐牌档案": profiles,
        "结构观察": reading["structure"]["observations"],
        "已有综合线索": reading["synthesis"],
        "已有行动参考": reading["actions"],
        "边界提示": reading["boundary"],
    }
