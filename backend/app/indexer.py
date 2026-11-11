"""Rebuild the SQLite index from the Markdown rule documents."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .db import as_csv, connect, init_schema
from .parser import dump_summary, parse_all

TABLES_TO_CLEAR = [
    "chunks_fts", "chunks", "positions", "spreads", "cards", "card_profiles", "scenes",
    "templates", "routes", "ritual_steps", "documents",
]


def rebuild(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    if conn is None:
        conn = connect()
    try:
        init_schema(conn)
        data = parse_all()

        for table in TABLES_TO_CLEAR:
            conn.execute(f"DELETE FROM {table}")

        for doc in data["documents"]:
            conn.execute(
                "INSERT INTO documents "
                "(doc_id,title,file_path,stages,scenes,tags,version,updated,source) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    doc["id"], doc["title"], doc["file_path"],
                    as_csv(doc["stages"]), as_csv(doc["scenes"]), as_csv(doc["tags"]),
                    doc["version"], doc["updated"], json.dumps(doc["source"], ensure_ascii=False),
                ),
            )

        for chunk in data["chunks"]:
            cur = conn.execute(
                "INSERT INTO chunks (doc_id,section,stages,scenes,tags,text,version) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    chunk["doc_id"], chunk["section"], as_csv(chunk["stages"]),
                    as_csv(chunk["scenes"]), as_csv(chunk["tags"]),
                    chunk["text"], chunk["version"],
                ),
            )
            chunk_id = cur.lastrowid
            conn.execute(
                "INSERT INTO chunks_fts (rowid,section,tags,text) VALUES (?,?,?,?)",
                (chunk_id, chunk["section"], ", ".join(chunk["tags"]), chunk["text"]),
            )

        conn.executemany(
            "INSERT INTO cards (card_id,name,label,arcana,suit,rank,number,upright,reversed,doc_id) "
            "VALUES (:card_id,:name,:label,:arcana,:suit,:rank,:number,:upright,:reversed,:doc_id)",
            data["cards"],
        )
        conn.executemany(
            "INSERT INTO card_profiles "
            "(card_id,name,english,number,arcana,correspondence,keywords,imagery,"
            "upright,reversed,symbolism,love,career,study,source) "
            "VALUES (:card_id,:name,:english,:number,:arcana,:correspondence,:keywords,:imagery,"
            ":upright,:reversed,:symbolism,:love,:career,:study,:source)",
            data["card_profiles"],
        )
        conn.executemany(
            "INSERT INTO spreads (spread_id,name,card_count,difficulty,suitable,doc_id) "
            "VALUES (:spread_id,:name,:card_count,:difficulty,:suitable,:doc_id)",
            data["spreads"],
        )
        conn.executemany(
            "INSERT INTO positions (spread_id,seq,name,meaning) "
            "VALUES (:spread_id,:seq,:name,:meaning)",
            data["positions"],
        )
        conn.executemany(
            "INSERT INTO scenes (scene_id,name,topics,recommended,focus,tags) "
            "VALUES (:scene_id,:name,:topics,:recommended,:focus,:tags)",
            data["scenes"],
        )
        conn.executemany(
            "INSERT INTO templates (scene_id,seq,text) VALUES (:scene_id,:seq,:text)",
            data["templates"],
        )
        conn.executemany(
            "INSERT INTO routes (stage,required,optional,always) "
            "VALUES (:stage,:required,:optional,:always)",
            data["routes"],
        )
        conn.executemany(
            "INSERT INTO ritual_steps (seq,name,stage,text) VALUES (:seq,:name,:stage,:text)",
            data["ritual_steps"],
        )
        conn.commit()
        return json.loads(dump_summary(data))
    except Exception:
        conn.rollback()
        raise
    finally:
        if own:
            conn.close()
