"""Continuous follow-up dialogue for one completed reading.

The scene never changes: on every turn the backend rebuilds the SAME three-part
feed (original question / drawn cards / interpretation references) from the
database and puts it in the system message. The conversation history carries
only question-answer pairs, so a long thread cannot drift away from the cards.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime
from typing import Any

from . import llm, verdict

MAX_HISTORY = 16          # last 8 exchanges
MAX_QUESTION = 300

FOLLOWUP_SYSTEM_PROMPT = """你是 VELUM｜帷间的驻场占卜师。问卜者刚刚完成一次占卜，读过你写的最终评定，现在就同一件事继续向你追问。

【最重要的一条：背景不变】
下方【本次占卜 · 固定背景】是这一次对话唯一的事实范围，每一轮都相同。你不得重新抽牌、不得引入背景之外的新牌、不得改动已经给出的牌面与位置，也不得推翻已经给出的最终评定。问卜者追问的是「同一副牌、同一个问题」的更多侧面。

【怎样回答】
1. 直接回答问卜者这一问，先用一两句接住他／她的话；若与前几轮有关，自然地接上（例如「你刚才问到……，其实和这一张牌是同一件事」），不要每轮都从开头重讲一遍整副牌。
2. 把回答落回具体牌或具体位置：说到某个判断时，点明它来自哪张牌、落在哪个位置，以及为什么在这个位置上这样读。不要凭空发挥。
3. 追问可能是在问某张牌的含义、某个位置的读法、牌与牌的关系、逆位在此刻怎么理解、或「那我具体可以做点什么」。无论哪一种，都顺着背景里的解读方法与逐牌详解来答，允许在给定牌义之间做关联推理。
4. 回答写成 2–4 段舒展的中文短文，用「你」称呼问卜者。不要写小标题、编号清单、项目符号，不要输出 JSON，不要复述系统流程、文档编号或免责声明全文。
5. 若这一问其实可以由已给出的最终评定回答，就换一个更贴近的角度重新说清，而不是简单重复原句。
6. 结尾把决定权留在问卜者手里，可顺带留一个可以接着聊的具体方向，但不要诱导再抽一次牌、不要诱导重复占卜。

【语言与边界】
- **允许明确措辞、确定性判断与吉凶占断**，不强制可能性措辞。寻物、时间、事件走向、第三方动向，以及健康／法律／财务类问题均可作答。
- 每一条占断须回指具体牌、位置或 RULE-12 对应表条目；牌面不足时说明「牌面未指向明确……」，不硬凑答案。
- 方位、时间、人物对应是传统象征约定，流派间不一致，表述为「依本体系对应，牌面指向……」，不作事实保证。
- 涉及健康、法律、财务等现实后果的领域，附一句知情提示（占断不替代相应专业人士的判断）；不拒绝、不生硬改框。
- 逆位按「能量层级说」理解：能量仍在，只是表达受阻、延迟、内化或尚未成形，不是反义也不是凶兆；本次若未启用逆位，不要提逆位。
- 语气克制、温和、有古典的分寸感；不用感叹号，不用营销腔，不用空洞安慰，不用「加油」「一切都会好起来」这类套话。
- 只输出回答正文，不要任何前后缀、说明或 Markdown 标记。"""

# v2.0：不再对敏感话题追加改框指令，也不再因确定性措辞改写回答。
# 保留正则常量仅为兼容历史引用，answer() 不再使用。
SENSITIVE_RE = re.compile(r"__NEVER_MATCH__")
REDIRECT_NOTE = ""


def _clean(text: str) -> str:
    """Strip the Markdown/prose wrappers a chat model may add to plain text."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t).removesuffix("```").strip()
    t = t.replace("**", "").replace("`", "")
    t = re.sub(r"^\s{0,3}#{1,4}\s+", "", t, flags=re.M)
    t = re.sub(r"^\s*[-*]\s+", "· ", t, flags=re.M)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _history(conn: sqlite3.Connection, session_id: str) -> list[dict[str, str]]:
    rows = conn.execute(
        "SELECT role, content FROM followup_turns WHERE session_id = ? "
        "ORDER BY id DESC LIMIT ?", (session_id, MAX_HISTORY),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _save(conn: sqlite3.Connection, session_id: str, role: str, content: str) -> None:
    conn.execute(
        "INSERT INTO followup_turns (session_id, turn, role, content, created_at) "
        "VALUES (?,?,?,?,?)",
        (
            session_id,
            conn.execute(
                "SELECT COUNT(*) AS c FROM followup_turns WHERE session_id = ?",
                (session_id,),
            ).fetchone()["c"] + 1,
            role, content, datetime.now().isoformat(timespec="seconds"),
        ),
    )


def _background(feed: dict[str, Any]) -> str:
    return (
        "【本次占卜 · 固定背景】（每一轮都相同，不得改动）\n\n"
        f"一、问卜者的原始问题\n{feed['question']}\n\n"
        f"二、本次抽牌状况\n{feed['draw']}\n\n"
        f"三、解读参考资料\n{feed['reference']}\n\n"
        f"【已经写给问卜者的最终评定 · 摘要】\n{feed['verdict_digest']}"
    )


def _fallback_answer(feed: dict[str, Any], question: str) -> str:
    """Rule-driven answer so a model outage never leaves the thread dead."""
    meta = feed["meta"]
    cards = "、".join(meta["card_names"][:6]) or "本次牌面"
    return (
        f"就「{question}」这一问，我们仍回到「{meta['question']}」这个原始问题，"
        f"以及 {meta['spread']} 里抽到的 {cards}。\n\n"
        "牌面能给出的是同一副牌的更多侧面：可以先看这一问落在哪个位置上，"
        "再看该位置的牌在正位或逆位时，能量是顺畅表达还是尚需成形；"
        "若问方位、时点或人物，可回到 RULE-12 对应表，看花色、数字与宫廷牌指向什么，"
        "把逐位释义连起来读，往往比单独取一张牌更贴近这一问。\n\n"
        "若愿意，可以把问题再收窄一点，例如某张牌落在某个位置该怎么理解、"
        "或某一处阻力可以先从哪个小动作着手。对应体系存在流派差异，占断供你自行取舍。"
    )


def _sources(reading: dict[str, Any]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for s in (reading.get("sources") or []) + (reading.get("always_sources") or []):
        doc_id = s.get("doc_id") if isinstance(s, dict) else None
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            out.append({"doc_id": doc_id})
    return out[:8]


def answer(conn: sqlite3.Connection, session_id: str, question: str) -> dict[str, Any]:
    q = (question or "").strip()
    if len(q) < 2:
        raise ValueError("请写下你想追问的内容")
    if len(q) > MAX_QUESTION:
        q = q[:MAX_QUESTION]

    row = conn.execute(
        "SELECT payload FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if not row:
        raise ValueError("会话不存在")
    reading = json.loads(row["payload"]).get("reading")
    if not reading:
        raise ValueError("请先完成本次占卜")

    feed = verdict.build_feed(conn, session_id)
    if not feed:
        raise ValueError("本次占卜记录尚未就绪")

    started = time.time()
    history = _history(conn, session_id)
    user_message = q
    messages: list[dict[str, str]] = [
        {"role": "system", "content": FOLLOWUP_SYSTEM_PROMPT + "\n\n" + _background(feed)},
        *history,
        {"role": "user", "content": user_message},
    ]

    degraded = False
    failure = ""
    reply = ""
    try:
        raw = llm.chat(messages, json_mode=False, max_tokens=1300, temperature=0.6)
        reply = _clean(raw)
        if len(reply) < 20:
            raise RuntimeError("回答过短")
        reply = reply[:1400]
    except Exception as exc:
        degraded = True
        failure = str(exc)[:200]
        reply = _fallback_answer(feed, q)

    _save(conn, session_id, "user", q)
    _save(conn, session_id, "assistant", reply)
    conn.commit()
    turn = conn.execute(
        "SELECT COUNT(*) AS c FROM followup_turns "
        "WHERE session_id = ? AND role = 'assistant'", (session_id,),
    ).fetchone()["c"]
    return {
        "answer": reply,
        "question": q,
        "degraded": degraded,
        "failure": failure,
        "turn": turn,
        "sources": _sources(reading),
        "latency_ms": round((time.time() - started) * 1000),
    }


def history(conn: sqlite3.Connection, session_id: str) -> list[dict[str, str]]:
    rows = conn.execute(
        "SELECT role, content, created_at FROM followup_turns "
        "WHERE session_id = ? ORDER BY id", (session_id,),
    ).fetchall()
    return [
        {"role": r["role"], "content": r["content"], "created_at": r["created_at"]}
        for r in rows
    ]


def clear(conn: sqlite3.Connection, session_id: str) -> None:
    conn.execute("DELETE FROM followup_turns WHERE session_id = ?", (session_id,))
    conn.commit()
