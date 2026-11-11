"""Database-driven retrieval: hard filter, route matrix, FTS5, explainable rerank.

No embeddings and no vector store. Every score component is recorded as a
human-readable reason so the UI can explain why a rule document was chosen.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Any

CJK = r"\u4e00-\u9fff"


def extract_terms(query: str, card_names: list[str], position_names: list[str]) -> list[str]:
    text = " ".join([query or ""] + list(card_names or []) + list(position_names or []))
    terms: set[str] = set()
    for piece in re.findall(rf"[{CJK}]+|[A-Za-z]{{3,}}|\d+", text):
        if re.fullmatch(rf"[{CJK}]+", piece):
            for n in (3, 4):
                for i in range(len(piece) - n + 1):
                    terms.add(piece[i:i + n])
        else:
            terms.add(piece.lower())
    return sorted(terms, key=lambda w: (-len(w), w))


def get_route(conn: sqlite3.Connection, stage: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM routes WHERE stage = ?", (stage,)).fetchone()
    if not row:
        return {"stage": stage, "required": [], "optional": [], "always": ["RULE-07"]}
    return {
        "stage": stage,
        "required": [x for x in row["required"].split(",") if x],
        "optional": [x for x in row["optional"].split(",") if x],
        "always": [x for x in row["always"].split(",") if x] or ["RULE-07"],
    }


def _fts_scores(conn: sqlite3.Connection, terms: list[str]) -> dict[int, float]:
    if not terms:
        return {}
    match = " OR ".join(f'"{t}"' for t in terms[:8])
    try:
        rows = conn.execute(
            "SELECT rowid, bm25(chunks_fts) AS score FROM chunks_fts "
            "WHERE chunks_fts MATCH ? LIMIT 200",
            (match,),
        ).fetchall()
    except sqlite3.Error:
        return {}
    raw = {int(r["rowid"]): -float(r["score"]) for r in rows}
    if not raw:
        return {}
    high = max(raw.values()) or 1.0
    return {k: v / high for k, v in raw.items()}


def get_always_chunks(conn: sqlite3.Connection, doc_ids: list[str]) -> list[dict[str, Any]]:
    if not doc_ids:
        return []
    marks = ",".join("?" for _ in doc_ids)
    rows = conn.execute(
        f"SELECT * FROM chunks WHERE doc_id IN ({marks}) AND section LIKE '%免责%'",
        doc_ids,
    ).fetchall()
    if not rows:
        rows = conn.execute(
            f"SELECT * FROM chunks WHERE doc_id IN ({marks}) ORDER BY chunk_id LIMIT 1",
            doc_ids,
        ).fetchall()
    return [dict(r) for r in rows]


def retrieve(
    conn: sqlite3.Connection,
    stage: str,
    scene_id: str,
    question: str = "",
    card_names: list[str] | None = None,
    position_names: list[str] | None = None,
    top_k: int = 6,
) -> dict[str, Any]:
    card_names = [c for c in (card_names or []) if c]
    position_names = [p for p in (position_names or []) if p]
    terms = extract_terms(question, card_names, position_names)
    route = get_route(conn, stage)
    required = set(route["required"]) | set(route["optional"])

    rows = conn.execute(
        "SELECT * FROM chunks "
        "WHERE (instr(stages, ?) > 0 OR instr(stages, ',all,') > 0) "
        "AND (instr(scenes, ?) > 0 OR instr(scenes, ',all,') > 0)",
        (f",{stage},", f",{scene_id},"),
    ).fetchall()

    fts = _fts_scores(conn, terms)
    scored: list[dict[str, Any]] = []
    for row in rows:
        text = row["text"]
        tags = [t for t in row["tags"].split(",") if t]
        stages = row["stages"]
        scenes = row["scenes"]
        score = 0.0
        reasons: list[str] = []

        if f",{stage}," in stages:
            score += 3
            reasons.append(f"环节精确匹配 {stage}")
        elif ",all," in stages:
            score += 1
            reasons.append("全环节文档")
        if f",{scene_id}," in scenes:
            score += 2
            reasons.append(f"场景匹配 {scene_id}")
        if row["doc_id"] in required:
            score += 4
            reasons.append("路由矩阵指定必检文档")
        card_hit_weight = 6 if row["doc_id"] in ("RULE-01", "RULE-02") else 1.2
        for name in card_names:
            if name and name in text:
                score += card_hit_weight
                reasons.append(f"牌名命中 {name}")
        for pos in position_names:
            if pos and pos in text:
                score += 2
                reasons.append(f"位置命中 {pos}")
        for tag in tags:
            if any(tag in t for t in terms):
                score += 2
                reasons.append(f"标签命中 {tag}")
        hits = sum(1 for t in terms if t in text)
        if hits:
            score += min(hits * 0.15, 2.0)
            reasons.append(f"关键词命中 {hits} 项")
        if row["chunk_id"] in fts:
            score += 2 * fts[row["chunk_id"]]
            reasons.append("全文检索相关")

        if score > 0:
            scored.append({
                "chunk_id": row["chunk_id"],
                "doc_id": row["doc_id"],
                "section": row["section"],
                "text": text,
                "tags": tags,
                "score": round(score, 2),
                "reasons": reasons[:6],
            })

    scored.sort(key=lambda x: (-x["score"], x["doc_id"], x["section"]))
    top = list(scored[:top_k])

    # Route guarantee: every document marked as required by RULE-08 must
    # contribute at least one chunk, even if pure relevance ranking misses it.
    required_docs = route["required"]
    for doc_id in required_docs:
        if any(r["doc_id"] == doc_id for r in top):
            continue
        candidate = next((r for r in scored if r["doc_id"] == doc_id), None)
        if not candidate:
            continue
        if len(top) < top_k:
            top.append(candidate)
        else:
            replaceable = [i for i, r in enumerate(top) if r["doc_id"] not in required_docs]
            if not replaceable:
                continue
            top[min(replaceable, key=lambda i: top[i]["score"])] = candidate
    top.sort(key=lambda x: (-x["score"], x["doc_id"], x["section"]))

    return {
        "stage": stage,
        "scene_id": scene_id,
        "route": route,
        "candidate_count": len(rows),
        "results": top,
        "always": [
            {"doc_id": r["doc_id"], "section": r["section"], "text": r["text"]}
            for r in get_always_chunks(conn, route["always"])
        ],
    }
