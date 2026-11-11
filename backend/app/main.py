"""FastAPI entry point for The Tarot ritual assistant."""
from __future__ import annotations

import json
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, dialogue, draw, llm
from .agent import agent_status, run_agent
from .db import connect, init_schema
from .indexer import rebuild
from .interpreter import build_reading
from .retriever import retrieve

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"

# v2.0 古典占问范式（RULE-00 §0 / RULE-07）：不再拦截任何问法。
# 提问校验只做长度提示，BAD_RULES 保留为空以兼容既有引用与历史调用。
BAD_RULES: list[tuple[str, str]] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    init_schema(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"]
    if count == 0:
        rebuild(conn)
    conn.close()
    yield


app = FastAPI(title="The Tarot · 占卜仪式辅助", version="1.0", lifespan=lifespan)

_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# BYOK：每个请求可携带自己的模型凭据（仅存在于该请求的 contextvar 中）。
# 请求结束立即清空，绝不写库、不进日志、不回显给其他请求。
_CRED_HEADERS = (
    "X-Velum-Api-Key",
    "X-Velum-Base-Url",
    "X-Velum-Model",
)


@app.middleware("http")
async def bind_model_credentials(request, call_next):
    llm.bind_request_credentials(
        request.headers.get("X-Velum-Api-Key", "")[:512],
        request.headers.get("X-Velum-Base-Url", "")[:512],
        request.headers.get("X-Velum-Model", "")[:128],
    )
    try:
        return await call_next(request)
    finally:
        llm.clear_request_credentials()


def get_conn() -> Iterator[Any]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def require_auth(
    token: str = Cookie(None, alias=auth.COOKIE_NAME),
    conn=Depends(get_conn),
) -> dict:
    """Gate for write operations on the canonical rule library."""
    user = auth.user_from_token(conn, token)
    if not user:
        raise HTTPException(status_code=401, detail="需要登录后才能维护规范")
    return user


def _set_session_cookie(response: Response, token: str) -> None:
    secure = os.getenv("SESSION_SECURE", "false").lower() == "true"
    response.set_cookie(
        key=auth.COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
        max_age=auth.SESSION_MAX_AGE,
    )


class QuestionCheck(BaseModel):
    scene_id: str = "general"
    question: str


class SessionCreate(BaseModel):
    scene_id: str
    spread_id: str
    question: str
    use_reversed: bool = False


class CardIn(BaseModel):
    seq: int
    card_id: str
    reversed: bool = False
    note: str = ""


class CardsIn(BaseModel):
    cards: list[CardIn]


class RetrieveIn(BaseModel):
    stage: str
    scene_id: str = "general"
    question: str = ""
    card_names: list[str] = []
    position_names: list[str] = []
    top_k: int = 6


class RuleSave(BaseModel):
    content: str


class AgentRun(BaseModel):
    node: str
    session_id: str = ""
    scene_id: str = "general"
    scene_name: str = ""
    question: str = ""
    spread_name: str = ""
    use_reversed: bool = False


class DrawIn(BaseModel):
    spread_id: str
    mode: str = ""
    use_reversed: bool = False
    session_id: str = ""


class FollowupIn(BaseModel):
    question: str


class AuthRegister(BaseModel):
    username: str
    password: str
    display: str = ""


class AuthLogin(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register")
def auth_register(body: AuthRegister, response: Response, conn=Depends(get_conn)):
    try:
        user = auth.register_user(conn, body.username, body.password, body.display)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _set_session_cookie(response, auth.create_session(conn, user["user_id"]))
    return {"user": user}


@app.post("/api/auth/login")
def auth_login(body: AuthLogin, response: Response, conn=Depends(get_conn)):
    user = auth.authenticate(conn, body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码不正确")
    _set_session_cookie(response, auth.create_session(conn, user["user_id"]))
    return {"user": user}


@app.post("/api/auth/logout")
def auth_logout(
    response: Response,
    token: str = Cookie(None, alias=auth.COOKIE_NAME),
    conn=Depends(get_conn),
):
    auth.delete_session(conn, token)
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def auth_me(
    token: str = Cookie(None, alias=auth.COOKIE_NAME),
    conn=Depends(get_conn),
):
    return {"user": auth.user_from_token(conn, token)}


@app.get("/api/draw/modes")
def get_draw_modes():
    return draw.MODES


@app.post("/api/draw")
def online_draw(body: DrawIn, conn=Depends(get_conn)):
    try:
        result = draw.draw(conn, body.spread_id, body.mode, body.use_reversed)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if body.session_id:
        row = conn.execute(
            "SELECT spread_id, use_reversed, payload FROM sessions WHERE session_id = ?",
            (body.session_id,),
        ).fetchone()
        if row:
            payload = json.loads(row["payload"])
            changed = (
                row["spread_id"] != body.spread_id
                or bool(row["use_reversed"]) != bool(body.use_reversed)
            )
            if changed:
                # The querent switched spread / reversal option after the
                # session was created; invalidate any stale card entries.
                payload["cards"] = []
                payload["reading"] = None
            payload["draw_source"] = "online"
            conn.execute(
                "UPDATE sessions SET spread_id = ?, use_reversed = ?, payload = ? "
                "WHERE session_id = ?",
                (
                    body.spread_id, int(body.use_reversed),
                    json.dumps(payload, ensure_ascii=False), body.session_id,
                ),
            )
            conn.commit()
            result["session_id"] = body.session_id
            result["session_synced"] = changed
    return result


@app.get("/api/agent/status")
def get_agent_status():
    return agent_status()


@app.post("/api/agent/probe")
def probe_agent():
    return llm.probe()


@app.post("/api/agent/run")
def run_agent_node(body: AgentRun, conn=Depends(get_conn)):
    try:
        return run_agent(conn, body.node, body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/agent/traces")
def agent_traces(conn=Depends(get_conn)):
    return [
        dict(r) for r in conn.execute(
            "SELECT trace_id,session_id,node,degraded,model,latency_ms,created_at "
            "FROM agent_traces ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
    ]


def _session(conn, session_id: str):
    row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(404, "会话不存在")
    return row


def _positions(conn, spread_id: str):
    return conn.execute(
        "SELECT * FROM positions WHERE spread_id = ? ORDER BY seq", (spread_id,)
    ).fetchall()


@app.get("/api/health")
def health(conn=Depends(get_conn)):
    return {
        "ok": True,
        "documents": conn.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"],
        "chunks": conn.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()["c"],
        "cards": conn.execute("SELECT COUNT(*) AS c FROM cards").fetchone()["c"],
        "profiles": conn.execute("SELECT COUNT(*) AS c FROM card_profiles").fetchone()["c"],
        "storage": "sqlite-fts5",
        "vector_store": False,
    }


@app.get("/api/scenes")
def list_scenes(conn=Depends(get_conn)):
    rows = conn.execute("SELECT * FROM scenes WHERE scene_id <> 'all'").fetchall()
    result = []
    for r in rows:
        item = dict(r)
        item["recommended_ids"] = re.findall(r"SP-\d+", r["recommended"] or "")
        item["templates"] = [
            t["text"] for t in conn.execute(
                "SELECT text FROM templates WHERE scene_id = ? ORDER BY seq", (r["scene_id"],)
            ).fetchall()
        ]
        result.append(item)
    return result


@app.get("/api/spreads")
def list_spreads(conn=Depends(get_conn)):
    result = []
    for r in conn.execute("SELECT * FROM spreads ORDER BY spread_id").fetchall():
        item = dict(r)
        item["positions"] = [
            dict(p) for p in _positions(conn, r["spread_id"])
        ]
        result.append(item)
    return result


@app.get("/api/cards")
def list_cards(conn=Depends(get_conn)):
    rows = conn.execute("SELECT * FROM cards ORDER BY arcana ASC, suit, number").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/card-library")
def card_library(conn=Depends(get_conn)):
    rows = conn.execute(
        "SELECT p.* FROM card_profiles p LEFT JOIN cards c ON c.card_id = p.card_id "
        "ORDER BY CASE "
        "WHEN p.card_id LIKE 'major-%' THEN 0 "
        "WHEN p.card_id LIKE 'wands-%' THEN 1 "
        "WHEN p.card_id LIKE 'cups-%' THEN 2 "
        "WHEN p.card_id LIKE 'swords-%' THEN 3 ELSE 4 END, "
        "c.number, p.card_id"
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/card-library/{card_id}")
def card_detail(card_id: str, conn=Depends(get_conn)):
    row = conn.execute("SELECT * FROM card_profiles WHERE card_id = ?", (card_id,)).fetchone()
    if not row:
        raise HTTPException(404, "未找到该牌")
    return dict(row)


@app.get("/api/ritual")
def ritual_steps(conn=Depends(get_conn)):
    return [dict(r) for r in conn.execute("SELECT * FROM ritual_steps ORDER BY seq").fetchall()]


@app.get("/api/routes")
def routes(conn=Depends(get_conn)):
    return [dict(r) for r in conn.execute("SELECT * FROM routes").fetchall()]


@app.post("/api/question/check")
def check_question(body: QuestionCheck, conn=Depends(get_conn)):
    q = body.question.strip()
    # 只提示长度，不再判定无效：valid 恒为真，任何问法都可提交（RULE-05 §5）
    issues = []
    if len(q) < 8:
        issues.append("问题较短，可补上具体情境以便牌面更聚焦")
    templates = [
        t["text"] for t in conn.execute(
            "SELECT text FROM templates WHERE scene_id = ? ORDER BY seq LIMIT 3", (body.scene_id,)
        ).fetchall()
    ]
    if not templates:
        templates = [
            t["text"] for t in conn.execute(
                "SELECT text FROM templates WHERE scene_id = 'general' ORDER BY seq LIMIT 3"
            ).fetchall()
        ]
    return {"valid": True, "issues": issues, "suggestions": templates}


@app.post("/api/retrieve")
def retrieve_rules(body: RetrieveIn, conn=Depends(get_conn)):
    return retrieve(
        conn, body.stage, body.scene_id, body.question,
        body.card_names, body.position_names, body.top_k,
    )


@app.post("/api/sessions")
def create_session(body: SessionCreate, conn=Depends(get_conn)):
    if not conn.execute("SELECT 1 FROM scenes WHERE scene_id = ?", (body.scene_id,)).fetchone():
        raise HTTPException(400, "场景不存在")
    if not conn.execute("SELECT 1 FROM spreads WHERE spread_id = ?", (body.spread_id,)).fetchone():
        raise HTTPException(400, "牌阵不存在")
    check = check_question(QuestionCheck(scene_id=body.scene_id, question=body.question), conn)
    session_id = uuid.uuid4().hex[:12]
    payload = {"cards": [], "reading": None, "question_issues": check["issues"]}
    conn.execute(
        "INSERT INTO sessions "
        "(session_id,scene_id,spread_id,question,use_reversed,created_at,payload) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            session_id, body.scene_id, body.spread_id, body.question.strip(),
            int(body.use_reversed), datetime.now().isoformat(timespec="seconds"),
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    conn.commit()
    return {"session_id": session_id, "question_check": check}


@app.post("/api/sessions/{session_id}/cards")
def save_cards(session_id: str, body: CardsIn, conn=Depends(get_conn)):
    session = _session(conn, session_id)
    positions = _positions(conn, session["spread_id"])
    expected = {p["seq"] for p in positions}
    got = [c.seq for c in body.cards]
    if set(got) != expected or len(got) != len(expected):
        raise HTTPException(
            400,
            f"牌位数量不符：会话牌阵 {session['spread_id']} 需要 {len(expected)} 张，"
            f"实际收到 {len(got)} 张（位置 {sorted(got)}）。若在抽卡页切换了牌阵，请重新进入仪式。",
        )
    ids = [c.card_id for c in body.cards]
    if len(set(ids)) != len(ids):
        raise HTTPException(400, "同一副实体牌不可能出现重复牌")
    valid = {r["card_id"] for r in conn.execute("SELECT card_id FROM cards").fetchall()}
    if any(i not in valid for i in ids):
        raise HTTPException(400, "存在非法牌名")
    if not session["use_reversed"] and any(c.reversed for c in body.cards):
        raise HTTPException(400, "本次会话未启用逆位，但收到逆位牌；请返回场景启用逆位后重新抽卡")
    payload = json.loads(session["payload"])
    payload["cards"] = [c.model_dump() for c in body.cards]
    payload["reading"] = None
    conn.execute("UPDATE sessions SET payload = ? WHERE session_id = ?",
                 (json.dumps(payload, ensure_ascii=False), session_id))
    conn.commit()
    return {"ok": True, "count": len(body.cards)}


@app.post("/api/sessions/{session_id}/reading")
def make_reading(session_id: str, with_verdict: bool = True, conn=Depends(get_conn)):
    session = _session(conn, session_id)
    payload = json.loads(session["payload"])
    cards = payload.get("cards", [])
    if not cards:
        raise HTTPException(400, "请先录入牌面")
    positions = _positions(conn, session["spread_id"])
    card_names: list[str] = []
    by_id = {r["card_id"]: dict(r) for r in conn.execute("SELECT * FROM cards").fetchall()}
    for c in cards:
        card = by_id.get(c["card_id"])
        if card:
            card_names.extend([card["name"], card["label"]])
    bundle = retrieve(
        conn, "interpret", session["scene_id"], session["question"],
        card_names, [p["name"] for p in positions], top_k=6,
    )
    reading = build_reading(conn, session, bundle)
    reading["record"]["draw_source"] = payload.get("draw_source", "manual")
    payload["reading"] = reading
    conn.execute("UPDATE sessions SET payload = ? WHERE session_id = ?",
                 (json.dumps(payload, ensure_ascii=False), session_id))
    conn.commit()
    if with_verdict:
        verdict = run_agent(conn, "final_verdict", {
            "session_id": session_id,
            "scene_id": session["scene_id"],
            "question": session["question"],
        })
        reading["verdict"] = {
            "output": verdict["output"],
            "degraded": verdict["degraded"],
            "model": verdict["model"],
            "latency_ms": verdict["latency_ms"],
            "sources": verdict["sources"],
            "trace": verdict["trace"],
            "failure": verdict["failure"],
        }
        payload["reading"] = reading
        conn.execute("UPDATE sessions SET payload = ? WHERE session_id = ?",
                     (json.dumps(payload, ensure_ascii=False), session_id))
        conn.commit()
    return reading


@app.get("/api/sessions")
def list_sessions(conn=Depends(get_conn)):
    rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC LIMIT 30").fetchall()
    result = []
    for r in rows:
        p = json.loads(r["payload"])
        result.append({
            "session_id": r["session_id"], "scene_id": r["scene_id"],
            "spread_id": r["spread_id"], "question": r["question"],
            "created_at": r["created_at"], "card_count": len(p.get("cards", [])),
            "has_reading": bool(p.get("reading")),
        })
    return result


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str, conn=Depends(get_conn)):
    r = _session(conn, session_id)
    return {"session_id": r["session_id"], "scene_id": r["scene_id"],
            "spread_id": r["spread_id"], "question": r["question"],
            "use_reversed": bool(r["use_reversed"]), "created_at": r["created_at"],
            **json.loads(r["payload"])}


@app.get("/api/sessions/{session_id}/followup")
def followup_history(session_id: str, conn=Depends(get_conn)):
    _session(conn, session_id)
    return {"turns": dialogue.history(conn, session_id)}


@app.post("/api/sessions/{session_id}/followup")
def followup_ask(session_id: str, body: FollowupIn, conn=Depends(get_conn)):
    _session(conn, session_id)
    try:
        return dialogue.answer(conn, session_id, body.question)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.delete("/api/sessions/{session_id}/followup")
def followup_clear(session_id: str, conn=Depends(get_conn)):
    _session(conn, session_id)
    dialogue.clear(conn, session_id)
    return {"ok": True}


@app.get("/api/rules")
def list_rules(conn=Depends(get_conn)):
    return [dict(r) for r in conn.execute("SELECT * FROM documents ORDER BY doc_id").fetchall()]


@app.get("/api/rules/{doc_id}")
def get_rule(doc_id: str, conn=Depends(get_conn)):
    row = conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "文档不存在")
    return {"meta": dict(row), "content": Path(row["file_path"]).read_text(encoding="utf-8")}


@app.put("/api/rules/{doc_id}")
def save_rule(doc_id: str, body: RuleSave, _u=Depends(require_auth), conn=Depends(get_conn)):
    row = conn.execute("SELECT file_path FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(404, "文档不存在")
    path = Path(row["file_path"])
    original = path.read_text(encoding="utf-8")
    path.write_text(body.content, encoding="utf-8")
    try:
        summary = rebuild(conn)
    except Exception as exc:
        path.write_text(original, encoding="utf-8")
        rebuild(conn)
        raise HTTPException(400, f"文档校验失败，已回滚到原内容：{exc}")
    return {"ok": True, "summary": summary}


@app.post("/api/index/rebuild")
def rebuild_index(_u=Depends(require_auth), conn=Depends(get_conn)):
    return {"ok": True, "summary": rebuild(conn)}


if DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="frontend")
