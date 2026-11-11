"""Assemble a structured, source-traceable reading from rule-document data.

This is deliberately rule-driven rather than LLM-generated: every statement
can be traced back to a rule chunk, and the reader stays the final author.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

SUIT_INFO = {
    "wands": ("权杖", "火", "行动、创造与推进"),
    "cups": ("圣杯", "水", "情感、关系与内在感受"),
    "swords": ("宝剑", "风", "思维、沟通与判断"),
    "pentacles": ("星币", "土", "资源、工作与现实落地"),
}
ADVICE = {
    "wands": "把最想推进的一件事拆成一个本周就能完成的小动作，先验证方向。",
    "cups": "留一段不被打断的时间，诚实地整理自己在这件事里的真实感受。",
    "swords": "把纠结逐条写下来，区分「已确认的事实」与「自己的推测」。",
    "pentacles": "核对时间、精力与实际资源是否足以支撑当前计划，必要时缩小范围。",
    "major": "先不急于行动，留一段观察期，等一个更明确的信号再决定。",
}
COURT_RANKS = {"page", "knight", "queen", "king"}


def _disclaimer(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT text FROM chunks WHERE doc_id = 'RULE-07' "
        "AND (section LIKE '%知情%' OR section LIKE '%免责%') LIMIT 1"
    ).fetchone()
    if row:
        lines = [l.lstrip("> ").strip() for l in row["text"].splitlines() if l.strip().startswith(">")]
        if lines:
            return " ".join(lines)
    return ("本系统依 RWS 牌义与 RULE-12 传统对应表作占断，属占卜性质的解释，"
            "不替代医疗、法律、财务等专业人士的判断；对应体系存在流派差异，结论由问卜者自行取舍。")


def _keywords(card: dict[str, Any], is_reversed: bool) -> str:
    if not is_reversed:
        return card["upright"]
    if card["reversed"]:
        return f"{card['reversed']}（能量仍在，但表达不充分）"
    return f"{card['upright']}（逆位：能量存在但可能受阻、延迟或内化，见 RULE-06）"


def build_reading(
    conn: sqlite3.Connection,
    session: sqlite3.Row,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    payload = json.loads(session["payload"])
    scene = conn.execute("SELECT * FROM scenes WHERE scene_id = ?", (session["scene_id"],)).fetchone()
    spread = conn.execute("SELECT * FROM spreads WHERE spread_id = ?", (session["spread_id"],)).fetchone()
    positions = conn.execute(
        "SELECT * FROM positions WHERE spread_id = ? ORDER BY seq", (session["spread_id"],)
    ).fetchall()
    cards_by_id = {
        r["card_id"]: dict(r)
        for r in conn.execute("SELECT * FROM cards").fetchall()
    }
    recorded = {int(c["seq"]): c for c in payload.get("cards", [])}

    entries: list[dict[str, Any]] = []
    for pos in positions:
        item = recorded.get(pos["seq"])
        if not item:
            continue
        card = cards_by_id.get(item["card_id"])
        if not card:
            continue
        is_reversed = bool(item.get("reversed")) and bool(session["use_reversed"])
        kw = _keywords(card, is_reversed)
        entries.append({
            "seq": pos["seq"],
            "position": pos["name"],
            "position_meaning": pos["meaning"],
            "card_id": card["card_id"],
            "label": card["label"],
            "name": card["name"],
            "reversed": is_reversed,
            "keywords": kw,
            "note": item.get("note", ""),
            "reading": (
                f"{pos['name']}位出现「{card['label']}」"
                f"{'（逆位）' if is_reversed else ''}：{kw}。"
                f"该位置关注：{pos['meaning']}。"
            ),
            "source": card["doc_id"],
        })

    total = len(entries)
    major_count = sum(1 for e in entries if cards_by_id[e["card_id"]]["arcana"] == "major")
    reversed_count = sum(1 for e in entries if e["reversed"])
    suit_counts: dict[str, int] = {}
    number_counts: dict[int, int] = {}
    court_count = 0
    for e in entries:
        card = cards_by_id[e["card_id"]]
        if card["suit"]:
            suit_counts[card["suit"]] = suit_counts.get(card["suit"], 0) + 1
        number_counts[card["number"]] = number_counts.get(card["number"], 0) + 1
        if card["rank"] in COURT_RANKS:
            court_count += 1

    observations: list[str] = []
    ratio = round(major_count / total * 100) if total else 0
    observations.append(
        f"本次共 {total} 张牌，其中大阿卡纳 {major_count} 张（{ratio}%）。"
        + ("原型性议题分量偏重，宜从较长的时间尺度理解。"
           if ratio >= 50 else "议题更多落在日常可调整的层面。")
    )
    dominant = max(suit_counts, key=suit_counts.get) if suit_counts else None
    if dominant:
        zh, element, area = SUIT_INFO[dominant]
        observations.append(
            f"小牌以{zh}（{element}）为主，提示可优先从「{area}」的角度理解这次提问。"
        )
    else:
        observations.append("未出现小牌花色，牌面以原型性讯息为主。")
    repeated = [n for n, c in number_counts.items() if c >= 2]
    if repeated:
        observations.append(f"数字 {', '.join(str(n) for n in sorted(repeated))} 重复出现，可留意该阶段主题的呼应。")
    if reversed_count:
        observations.append(
            f"逆位 {reversed_count} 张。依 RULE-06，逆位表示能量存在但表达不充分，不等同于反义或凶兆。"
        )
    if court_count:
        observations.append(f"出现 {court_count} 张宫廷牌，可同时考虑「人物 / 自身某一面 / 应采取的姿态」三种指涉。")

    focus = scene["focus"] if scene else "按牌面实际分布"
    kw_all = "、".join(dict.fromkeys(e["keywords"].split("（")[0] for e in entries))[:120]
    question = session["question"]
    synthesis = [
        f"围绕「{question}」，牌面较可能指向这些关键词：{kw_all or '（尚未录入牌面）'}。这是一种观察角度，不是结论。",
        f"场景侧重为「{focus}」；同一张牌在不同位置会有不同读法，建议把逐位释义连起来看，而非单独取一张定调。",
        "牌阵描述的是当前能量沿既有路径的倾向，问卜者的选择仍会改变走向，因此以下方向均以「可能」「建议」表述。",
    ]
    if dominant:
        zh, _, area = SUIT_INFO[dominant]
        synthesis.append(f"若只取一个切入点，可先问自己：在「{area}」这一面，此刻我最不愿面对的是什么？")
    if major_count >= 2:
        synthesis.append("多张大阿卡纳同时出现，宜把这件事放进更长的个人脉络里看待，不必急于求得即时答案。")

    action_key = dominant if dominant else "major"
    actions = [
        ADVICE[action_key],
        "把本次的一句话总结交给问卜者本人，由他／她决定下一步；占卜师不代为拍板。",
    ]

    return {
        "session_id": session["session_id"],
        "created_at": session["created_at"],
        "record": {
            "scene": scene["name"] if scene else session["scene_id"],
            "scene_id": session["scene_id"],
            "spread": spread["name"] if spread else session["spread_id"],
            "spread_id": session["spread_id"],
            "question": question,
            "use_reversed": bool(session["use_reversed"]),
        },
        "positions": entries,
        "structure": {
            "total": total,
            "major_count": major_count,
            "reversed_count": reversed_count,
            "court_count": court_count,
            "suit_counts": suit_counts,
            "observations": observations,
        },
        "synthesis": synthesis,
        "actions": actions,
        "boundary": _disclaimer(conn),
        "sources": [
            {"doc_id": r["doc_id"], "section": r["section"], "score": r["score"], "reasons": r["reasons"]}
            for r in bundle["results"]
        ],
        "always_sources": bundle["always"],
        "route": bundle["route"],
        "candidate_count": bundle["candidate_count"],
    }
