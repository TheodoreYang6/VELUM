"""Online draw: a digital simulation, NOT a substitute for the physical ritual.

See RULE-04 「线上抽卡模式」. Results pass through exactly the same validation
and interpretation pipeline as manually recorded cards.
"""
from __future__ import annotations

import random
import sqlite3
from typing import Any

MODES: list[dict[str, Any]] = [
    {
        "id": "single", "name": "单张 · 命运之牌", "animation": "halo",
        "spreads": ["SP-01"], "card_range": "1 张",
        "description": "牌背悬停旋转，金色光环扩散后翻转揭晓",
        "caption": "适合当日指引与单一焦点",
    },
    {
        "id": "timeline", "name": "三张 · 时间之流", "animation": "timeline",
        "spreads": ["SP-02", "SP-06"], "card_range": "3 张",
        "description": "三张牌沿时间光带依次滑入，逐张翻转",
        "caption": "过去 · 现在 · 未来，或选项权衡",
    },
    {
        "id": "cross", "name": "五张 · 十字展开", "animation": "cross",
        "spreads": ["SP-03", "SP-05"], "card_range": "5–7 张",
        "description": "中心先落位，四翼沿十字方向展开，连线依次点亮",
        "caption": "兼顾表层困境与深层成因",
    },
    {
        "id": "celtic", "name": "十张 · 凯尔特十字", "animation": "celtic",
        "spreads": ["SP-04", "SP-07"], "card_range": "10–12 张",
        "description": "左侧圆环旋转落位，右侧权杖自下而上依次升起",
        "caption": "复杂议题的全景式解读",
    },
]


def mode_for_spread(spread_id: str) -> dict[str, Any]:
    for mode in MODES:
        if spread_id in mode["spreads"]:
            return mode
    return MODES[1]


def draw(conn: sqlite3.Connection, spread_id: str, mode_id: str, use_reversed: bool) -> dict[str, Any]:
    positions = conn.execute(
        "SELECT * FROM positions WHERE spread_id = ? ORDER BY seq", (spread_id,)
    ).fetchall()
    if not positions:
        raise ValueError("牌阵不存在或没有位置定义")
    pool = [r["card_id"] for r in conn.execute("SELECT card_id FROM cards").fetchall()]
    if len(positions) > len(pool):
        raise ValueError("牌位数量超过 78 张")

    rng = random.SystemRandom()
    cards_by_id = {
        r["card_id"]: dict(r) for r in conn.execute("SELECT * FROM cards").fetchall()
    }
    # Full shuffled deck: the querent's choice of a fan position really decides
    # which card is drawn, instead of the server pre-picking the result.
    shuffled = rng.sample(pool, len(pool))
    deck = [
        {
            "card_id": card_id,
            "reversed": bool(use_reversed and rng.random() < 0.3),
        }
        for card_id in shuffled
    ]
    entries = [
        {
            "seq": pos["seq"],
            "card_id": deck[i]["card_id"],
            "reversed": deck[i]["reversed"],
            "note": "",
        }
        for i, pos in enumerate(positions)
    ]
    mode = next((m for m in MODES if m["id"] == mode_id), None) or mode_for_spread(spread_id)
    return {
        "mode": mode["id"],
        "mode_name": mode["name"],
        "animation": mode["animation"],
        "spread_id": spread_id,
        "draw_source": "online",
        "use_reversed": use_reversed,
        "positions": [dict(p) for p in positions],
        "deck": deck,
        "deck_size": len(deck),
        "deck_details": [cards_by_id[d["card_id"]] for d in deck],
        "cards": entries,
        "card_details": [cards_by_id[e["card_id"]] for e in entries],
    }
