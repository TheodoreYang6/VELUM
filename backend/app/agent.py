"""Agent workflow orchestration.

Design rule: the LLM is an EXPRESSION layer, never a FACT layer.
Card meanings, spread positions, ritual steps, reversal rules and ethics
stay in docs/rules/*.md. Every LLM call is grounded in retrieved chunks,
guardrailed, traceable, and degradable to a rule-driven fallback.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from datetime import datetime
from typing import Any

from . import llm, verdict
from .retriever import retrieve

# Generic expression-layer prompt, used by all short helper nodes.
SYSTEM_PROMPT = """你是「VELUM｜帷间」占卜仪式辅助系统的语言助手。你的唯一职责是把已给定的规则片段与结构化记录，改写成自然、克制、温和的中文表达。

严格约束（对应 RULE-07 与 RULE-06，v2.0 古典占问范式）：
1. 只能使用【规则片段】与【结构化记录】中已有的信息，以及 RULE-12 对应表条目。不得引入文档之外的新牌义或凭空断言；占断须回指具体牌与位置。
2. **允许明确措辞与吉凶判断**，不强制可能性措辞；结论须与所引牌义、位置含义一致，不得凭空加重。
3. 寻物、时间、事件走向、第三方动向、健康／法律／财务类问题均可作答；涉及现实后果的领域附一句 RULE-07 §2 知情提示。
4. 方位、时间、人物对应属传统象征约定，表述为「依本体系对应，牌面指向……」，不作事实保证；牌面不足时说明「牌面未指向明确……」。
5. 死神、高塔、恶魔、宝剑十等牌按转化、结构松动或周期结束解读，不用恐吓式表述。
6. 语气为欧式古典、克制、不煽情；不要使用感叹号，不要营销腔，不要安慰式空话。
7. 只输出要求的 JSON 对象，不要输出任何解释、前后缀或 Markdown 代码块。
8. 不要写出文档编号、字段名、系统状态等内部痕迹。"""

# The final verdict is the one node written FOR the querent, not for the system.
# It gets its own prompt: a letter from the reader, not a filled-in report form.
VERDICT_SYSTEM_PROMPT = """你是 VELUM｜帷间的驻场占卜师。此刻你要做的，不是填写一份分析表格，而是为坐在对面的问卜者写下一段他／她愿意读完、读完之后更清醒一点的解读。

【你在为谁写】
问卜者带着一个具体的问题坐下来，亲手抽出了几张牌。他／她不关心系统内部怎样组织资料，只想听见：这些牌合在一起，在说我这件事的什么？我又可以从哪里着手？
始终用「你」称呼问卜者，用完整、舒展的中文句子来写，像一位克制而有阅历的占卜师在桌边慢慢说完的一段话。不要写成报告、条目清单或字段说明；不要罗列小标题式的标签，不要把同一层意思拆成许多互不相干的短句。

【你手上的三份材料】
一、问卜者的原始问题——整段解读要回到的地方，收尾时必须落回它。
二、本次抽牌状况——牌阵、每个位置的名称与含义、每个位置抽到的牌与正逆位、全牌阵的结构观察。
三、解读参考资料——本体系采用的解读方法、本次牌阵的位置定义、本次每一张牌的简明牌义与逐牌详解（图像、正位、逆位、象征、对应、该场景下的提示）、元素与结构口径、场景侧重、RULE-12 古典占问对应表（寻物方位／时间速度／人物原型），以及 RULE-07 知情说明与作答规范。

【怎样写】
1. 先接住问题：开场一两句，让问卜者知道你确实听见了他／她问的是什么。不要寒暄，不要复述流程，不要说「根据你的牌面显示」这类套话。
2. 用一句话给出核心看见：它不是结论，而是这次牌面最值得留意的那一个点。
3. 把牌写成一条脉络，而不是一张张说明书。按牌阵的逻辑串起来：哪张在说现状，哪张在说卡住的地方，哪张在说可以往哪走；牌与牌之间如何呼应、如何拉扯。每一处判断都要能指回具体某张牌或某个位置，用「落在……位的……牌」「因为这张牌」这样的方式自然带出，不要堆砌牌名，也不要一段里塞进所有牌。
4. 逐牌札记只补一句最贴合该位置的提醒，简短、具体，不要重复正文里已经说过的话。
5. 谈可依凭之处与阻力时，说的是「可以借上什么力」「哪里需要多留一步」；允许做吉凶与走向判断，但须回指具体牌或位置，不凭空加重、不打分、不排名。
6. 行动方向必须是问卜者自己就能做的小事，具体、可落地，两到三条即可，不替他／她做决定，不写「应该」「必须」。正文段落只负责把牌讲成脉络，不要重复这些行动建议。
7. 收束把决定权轻轻交还：牌面只是此刻的一面镜子，走向仍由问卜者自己写。不要在此处重复免责声明全文。

【语言与边界】
- **允许明确措辞、确定性判断与吉凶占断**，不强制可能性措辞。寻物、时间、事件走向、第三方动向，以及健康／法律／财务类问题均可作答。
- 每一条占断须能回指到具体牌、位置或 RULE-12 对应表条目；牌面不足以支持结论时，说明「牌面未指向明确……」，不硬凑答案。
- 方位、时间、人物对应是传统象征约定，流派间不一致：表述为「依本体系对应，牌面指向……」，不作事实保证；数字不直接等于日历单位，落时点须给出推导。
- 涉及健康、法律、财务等现实后果的领域，附一句知情提示（占断不替代相应专业人士的判断）；不拒绝、不生硬改框。
- 逆位按「能量层级说」理解：能量仍在，只是表达受阻、延迟、内化或尚未成形；不是反义，也不是凶兆。本次若未启用逆位，全篇不提逆位。
- 结构观察（大牌占比、主导花色、重复数字等）只作为线索，不单独构成结论。
- 只使用三份材料里已有的牌义与信息，以及 RULE-12 对应表条目；不引入资料之外的新牌义或凭空断言。允许在给定牌义之间做关联推理，但每个判断都要回指到牌或位置。
- 语气克制、温和、带一点古典的分寸感；不用感叹号，不用营销腔，不用空洞安慰，不用「加油」「一切都会好起来」这类套话。
- 不出现文档编号、字段名、模型名称、系统状态等内部痕迹；参考资料是给你看的，不是写给问卜者看的。

【输出】
只输出一个合法的 JSON 对象，不要任何解释、前后缀或 Markdown 代码块。字段见本次要求；所有面向问卜者的文字写在字段值里，正文段落用数组元素表示，字符串内不要使用 Markdown 标记或换行符。"""

# v2.0：不再因确定性措辞拒绝或降级。保留常量仅为兼容历史引用，
# 现仅用于统计（不影响 _validate 结果），见 RULE-07 §6。
BANNED_RE = re.compile(r"__NEVER_MATCH__")

NODES: dict[str, dict[str, Any]] = {
    "refine_question": {
        "stage": "question",
        "task": "把问卜者的原始提问润色得更清楚、更聚焦（可选，不强制改写）。保留原意与提问类型，不得添加新信息；若是寻物、时间、吉凶或第三方动向类问题，保持其问法不要改成开放式反思。另给 2 条理由和 2 条可选的替代表述。",
        "schema": '{"refined":"改写后的问题","reasons":["理由1","理由2"],"alternatives":["备选1","备选2"]}',
        "fields": ["refined"],
    },
    "ritual_script": {
        "stage": "ritual-prep",
        "task": "为本次占卜写四段可由占卜师朗读的简短引导语：开场、洗牌前、抽牌前、收尾。每段 1–2 句，只复述规则片段中的动作与约定，不得发明任何新仪式。",
        "schema": '{"opening":"...","shuffle":"...","draw":"...","closing":"..."}',
        "fields": ["opening", "shuffle", "draw", "closing"],
    },
    "narrative": {
        "stage": "interpret",
        "task": "把下方【结构化记录】改写为一段连贯、可读的解读叙述：先一句概括，再 3 段正文（分别处理牌位脉络、结构观察、场景化综合）。可依 RULE-12 对应表作占断，但每个判断须回指具体牌或位置，不得凭空断言。",
        "schema": '{"summary":"一句话概括","paragraphs":["第1段","第2段","第3段"],"tone_note":"一句话说明语气处理"}',
        "fields": ["summary", "paragraphs"],
    },
    "followups": {
        "stage": "close",
        "task": "基于本次问题与牌面，生成 2 个追问，帮助问卜者就同一副牌看得更细（可含方位、时点、吉凶、第三方动向等方向）。不诱导重复占卜。",
        "schema": '{"questions":["追问1","追问2"],"note":"一句使用提示"}',
        "fields": ["questions"],
    },
    "final_verdict": {
        "stage": "interpret",
        "task": "依据下面三份材料，为问卜者写下这次占卜的最终评定：一段能读完、能落回其原始问题的解读。",
        "schema": (
            '{"opening":"开场一两句，接住问卜者的问题",'
            '"verdict":"一句话核心看见",'
            '"theme":"核心课题，60–110字的一段话",'
            '"paragraphs":["正文第1段","正文第2段","正文第3段"],'
            '"card_notes":[{"position":"位置名","card":"牌名（含正/逆位）","orientation":"正位","note":"该牌在此位置的一句提醒"}],'
            '"strengths":["可以依凭之处1","可以依凭之处2"],'
            '"challenges":["需要多留一步之处1","需要多留一步之处2"],'
            '"guidance":["具体可做的小事1","具体可做的小事2"],'
            '"cautions":["需要留意的一点"],'
            '"closing":"收束一段，把决定权交还问卜者"}'
        ),
        "fields": ["opening", "verdict", "paragraphs", "card_notes", "guidance", "closing"],
    },
}


def _reading(conn: sqlite3.Connection, session_id: str | None) -> dict[str, Any] | None:
    if not session_id:
        return None
    row = conn.execute("SELECT payload FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
    if not row:
        return None
    return json.loads(row["payload"]).get("reading")


def _structured_record(conn: sqlite3.Connection, node: str, payload: dict[str, Any]) -> dict[str, Any]:
    reading = _reading(conn, payload.get("session_id"))
    scene = payload.get("scene_name") or payload.get("scene_id") or "通用指引"
    if node == "narrative" and reading:
        return {
            "scene": scene,
            "question": reading["record"]["question"],
            "spread": reading["record"]["spread"],
            "positions": [
                {"position": p["position"], "card": p["label"], "reversed": p["reversed"], "keywords": p["keywords"]}
                for p in reading["positions"]
            ],
            "observations": reading["structure"]["observations"],
            "synthesis": reading["synthesis"],
            "actions": reading["actions"],
            "boundary": reading["boundary"],
        }
    if node == "followups" and reading:
        return {
            "scene": scene, "question": reading["record"]["question"],
            "cards": [p["label"] for p in reading["positions"]],
            "synthesis": reading["synthesis"][:2],
        }
    if node == "ritual_script":
        steps = [r["name"] for r in conn.execute("SELECT name FROM ritual_steps ORDER BY seq").fetchall()]
        return {
            "scene": scene, "question": payload.get("question", ""),
            "spread": payload.get("spread_name", ""),
            "use_reversed": payload.get("use_reversed", False),
            "step_names": steps,
        }
    templates = [
        r["text"] for r in conn.execute(
            "SELECT text FROM templates WHERE scene_id = ? ORDER BY seq LIMIT 3",
            (payload.get("scene_id", "general"),),
        ).fetchall()
    ]
    return {
        "scene": scene,
        "original_question": payload.get("question", ""),
        "scene_templates": templates,
    }


def _verdict_fallback(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Rule-driven, still readable fallback for the final verdict."""
    reading = _reading(conn, payload.get("session_id"))
    if not reading:
        return None
    syn = reading.get("synthesis") or []
    obs = reading["structure"].get("observations") or []
    positions = reading["positions"]
    question = reading["record"]["question"]
    first = positions[0] if positions else None
    return {
        "opening": f"你把「{question}」写下来，说明这件事已经在心里放了有一段时候。让我们把这次抽到的牌，按它们各自落的位置慢慢看一遍。",
        "verdict": syn[0] if syn else "牌面提供了几个可以参照的观察角度。",
        "theme": " ".join(obs[:2]) if obs else "把逐位释义连起来看，会比单独取一张牌更贴近这件事的全貌。",
        "paragraphs": [
            " ".join(syn[:2]) if syn else "牌面尚无足够信息可展开。",
            (
                f"位置之间并非彼此独立：{first['position']}位的「{first['label']}」"
                f"给出了一个起点，后续的牌则在这个起点上展开不同的侧面。"
                if first else "逐位释义见下方札记。"
            ) + (" " + syn[2] if len(syn) > 2 else ""),
            " ".join(reading.get("actions") or []) or "可以先记下最有共鸣的一句，由你自己决定下一步。",
        ],
        "card_notes": [
            {
                "position": p["position"],
                "card": f"{p['label']}（{'逆位' if p['reversed'] else '正位'}）",
                "orientation": "逆位" if p["reversed"] else "正位",
                "note": p["reading"],
            }
            for p in positions
        ],
        "strengths": [syn[1]] if len(syn) > 1 else ["牌面提供了可参照的线索"],
        "challenges": ["逆位与阻碍位值得优先留意"] if reading["structure"]["reversed_count"] else ["部分能量尚需落实为行动"],
        "guidance": reading.get("actions") or [],
        "cautions": [reading.get("boundary", "")],
        "closing": "牌面停在这里，它照见的是此刻的倾向，不是写好的结局。接下来怎么走，仍由你来决定。",
        "kept_original": True,
    }


def _fallback(conn: sqlite3.Connection, node: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Rule-driven output used whenever the model is unavailable or rejected."""
    if node == "final_verdict":
        result = _verdict_fallback(conn, payload)
        if result:
            return result
    reading = _reading(conn, payload.get("session_id"))
    if node == "refine_question":
        templates = [
            r["text"] for r in conn.execute(
                "SELECT text FROM templates WHERE scene_id = ? ORDER BY seq LIMIT 2",
                (payload.get("scene_id", "general"),),
            ).fetchall()
        ]
        return {
            "refined": payload.get("question", ""),
            "reasons": ["大模型不可用，已保留原问题；请依 RULE-05 自行校验措辞"],
            "alternatives": templates or ["关于这件事，我最需要看清的是什么？"],
            "kept_original": True,
        }
    if node == "ritual_script":
        return {
            "opening": "请安静下来，我们把注意力放回这次的问题上。",
            "shuffle": "由问卜者本人洗牌，边洗边想着写好的问题，洗到自然想停即停。",
            "draw": "按牌阵位置顺序逐张抽取，全部就位后再翻牌，并保留原有朝向。",
            "closing": "记录牌面与一句话总结，收拢牌叠并归位；决定权始终在问卜者。",
            "kept_original": True,
        }
    if node == "narrative" and reading:
        syn = reading["synthesis"]
        return {
            "summary": syn[0],
            "paragraphs": syn[1:3] + ["行动参考：" + " ".join(reading["actions"])],
            "tone_note": "大模型不可用，以下为规则驱动的原始参考稿。",
            "kept_original": True,
        }
    if node == "followups":
        return {
            "questions": [
                "刚才这段解读里，哪一部分与你此刻的真实处境最有共鸣？",
                "如果只做一个很小的调整，你愿意先从哪里开始？",
            ],
            "note": "大模型不可用，以上为固定开放式追问。",
            "kept_original": True,
        }
    return {"note": "暂无可用的规则驱动输出", "kept_original": True}


# 模型偶发把数组字段写成单个字符串（如 cautions: "……"），若直接落库，
# 前端 .map() 会抛 TypeError 并导致 React 卸载整棵树（整页黑屏）。
# 因此在校验/落库前统一把「应为数组」的字段强制归一化。
_LIST_FIELDS: dict[str, tuple[str, ...]] = {
    "final_verdict": (
        "paragraphs", "card_notes", "strengths", "challenges",
        "guidance", "cautions",
    ),
    "refine_text": ("paragraphs",),
}

_TEXT_FIELDS = ("opening", "verdict", "theme", "closing", "tone", "core_theme", "dynamics", "summary")


def _as_text(value: Any) -> str:
    """Turn a stray object/number into a printable string, never crash React."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        for key in ("text", "content", "note", "value", "summary"):
            if isinstance(value.get(key), str):
                return value[key]
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _normalize_output(node: str, output: Any) -> dict[str, Any]:
    """Coerce LLM output into the shape the frontend renders, defensively."""
    if not isinstance(output, dict):
        return {}
    fixed = dict(output)
    for field in _LIST_FIELDS.get(node, ()):
        # 只归一化模型实际输出的字段；不新增缺失字段，否则旧版会话会被
        # 前端误判为新版文章式（空 paragraphs 也会让 Array.isArray 为真）
        if field not in fixed:
            continue
        value = fixed.get(field)
        if isinstance(value, list):
            fixed[field] = [
                (x if isinstance(x, (str, dict)) else _as_text(x))
                for x in value if x not in (None, "")
            ]
        elif isinstance(value, str) and value.strip():
            fixed[field] = [value.strip()]
        elif value not in (None, "", []):
            fixed[field] = [_as_text(value)]
        else:
            fixed[field] = []
    for field in _TEXT_FIELDS:
        if field in fixed and not isinstance(fixed[field], str):
            fixed[field] = _as_text(fixed[field])
    return fixed


def _validate(node: str, output: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(output, dict) or not output:
        return False, "输出为空或格式错误"
    for field in NODES[node]["fields"]:
        if field not in output or not output[field]:
            return False, f"缺少字段 {field}"
    joined = json.dumps(output, ensure_ascii=False)
    limit = 10000 if node == "final_verdict" else 4000
    if len(joined) > limit:
        return False, "输出过长"
    return True, ""


def _rule_text(results: list[dict[str, Any]]) -> str:
    parts = []
    for r in results[:4]:
        parts.append(f"[{r['doc_id']} § {r['section']}]\n{r['text'][:650]}")
    return "\n\n".join(parts)


def _verdict_prompt(spec: dict[str, Any], feed: dict[str, Any]) -> str:
    """Three clearly labelled blocks, in the order the writer needs them."""
    return (
        f"【一 · 问卜者的原始问题】\n{feed['question']}\n\n"
        f"【二 · 本次抽牌状况】\n{feed['draw']}\n\n"
        f"【三 · 解读参考资料】\n{feed['reference']}\n\n"
        f"【本次输出 JSON 结构】\n{spec['schema']}\n\n"
        "【长度与体例】opening 40–80 字；verdict 30–60 字；theme 60–110 字；"
        "paragraphs 恰好 3 段、每段 90–170 字，正文只讲牌与脉络，不写行动建议；"
        "card_notes 每项 note 30–70 字；"
        "strengths / challenges 各 2 条、guidance 2–3 条、每条 20–50 字；"
        "cautions 1 条；closing 40–80 字。\n"
        "请只输出符合上述结构的 JSON 对象，所有文字都写给问卜者本人。"
    )


def run_agent(conn: sqlite3.Connection, node: str, payload: dict[str, Any]) -> dict[str, Any]:
    if node not in NODES:
        raise ValueError(f"未知 agent 节点：{node}")
    spec = NODES[node]
    started = time.time()
    trace: list[dict[str, Any]] = []
    degraded = False
    failure = ""
    sources: list[dict[str, Any]] = []
    output: dict[str, Any] = {}

    reading = _reading(conn, payload.get("session_id"))
    card_names: list[str] = []
    position_names: list[str] = []
    if reading:
        for p in reading["positions"]:
            card_names.extend([p["label"], p["name"]])
            position_names.append(p["position"])

    try:
        bundle = retrieve(
            conn, spec["stage"], payload.get("scene_id", "general"),
            payload.get("question", ""), card_names, position_names, top_k=5,
        )
        trace.append({
            "step": "1 · retrieve_rules",
            "tool": "sqlite-fts5 + 路由矩阵",
            "candidates": bundle["candidate_count"],
            "required": bundle["route"]["required"],
            "docs": [r["doc_id"] for r in bundle["results"]],
        })
        if not bundle["results"]:
            raise RuntimeError("未检索到规则片段，拒绝无依据生成")

        if node == "final_verdict":
            feed = verdict.build_feed(conn, payload.get("session_id", ""))
            if not feed:
                raise RuntimeError("缺少本次占卜记录，拒绝无依据生成")
            system_prompt = VERDICT_SYSTEM_PROMPT
            user_prompt = _verdict_prompt(spec, feed)
            max_tokens, repair_words = 3400, 1400
            trace.append({
                "step": "1b · build_feed",
                "tool": "三段喂料 · 原始问题 / 抽牌状况 / 解读参考资料",
                "chars": len(feed["question"]) + len(feed["draw"]) + len(feed["reference"]),
            })
        else:
            system_prompt = SYSTEM_PROMPT
            record = _structured_record(conn, node, payload)
            rules_block = _rule_text(bundle["results"])
            user_prompt = (
                f"【节点任务】{spec['task']}\n\n"
                f"【输出 JSON 结构】{spec['schema']}\n\n"
                f"【规则片段 · 唯一可用事实来源】\n{rules_block}\n\n"
                f"【常驻知情说明 · RULE-07】\n"
                "本系统依 RWS 牌义与 RULE-12 传统对应表作占断，属占卜性质的解释，不替代专业人士判断；"
                "对应体系存在流派差异，结论由问卜者自行取舍。允许明确措辞与吉凶判断。\n\n"
                f"【结构化记录】\n{json.dumps(record, ensure_ascii=False)[:2600]}\n\n"
                "【长度】所有文本字段合计不超过 450 字，单段不超过 150 字。\n"
                "请只输出符合上述结构的 JSON 对象。"
            )
            max_tokens, repair_words = 2200, 500

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        raw = llm.chat(messages, json_mode=True, max_tokens=max_tokens, temperature=0.5 if node == "final_verdict" else 0.35)
        trace.append({
            "step": "2 · llm_call",
            "tool": "deepseek chat/completions",
            "model": llm.status()["active_model"],
            "response_chars": len(raw),
        })
        output = _normalize_output(node, llm.extract_json(raw))
        if not output:
            repair = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt +
                 f"\n\n注意：上一次输出不是完整合法的 JSON。请重新输出完整 JSON 对象，字段不变，总字数控制在 {repair_words} 字以内，不要输出任何其他内容。"},
            ]
            raw = llm.chat(repair, json_mode=True, max_tokens=min(max_tokens, 2000), temperature=0.2)
            output = _normalize_output(node, llm.extract_json(raw))
            trace.append({
                "step": "2b · json_repair",
                "tool": "deepseek chat/completions",
                "result": "recovered" if output else "failed",
            })
        ok, reason = _validate(node, output)
        if not ok:
            raise RuntimeError(f"输出护栏未通过：{reason}")
        trace.append({"step": "3 · guardrail", "tool": "结构与事实回指校验", "result": "passed"})
        sources = [
            {"doc_id": r["doc_id"], "section": r["section"], "score": r["score"]}
            for r in bundle["results"]
        ]
    except Exception as exc:
        degraded = True
        failure = str(exc)[:220]
        output = _fallback(conn, node, payload)
        trace.append({"step": "fallback", "tool": "规则驱动降级", "reason": failure})

    # 统一收口：无论正常 / 修复 / 降级分支，落库与返回前都保证字段类型安全
    output = _normalize_output(node, output)

    latency = round((time.time() - started) * 1000)
    result = {
        "node": node,
        "output": output,
        "degraded": degraded,
        "failure": failure,
        "model": llm.status()["active_model"],
        "latency_ms": latency,
        "sources": sources,
        "trace": trace,
    }
    trace_id = uuid.uuid4().hex[:12]
    conn.execute(
        "INSERT INTO agent_traces "
        "(trace_id,session_id,node,degraded,model,latency_ms,created_at,payload) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            trace_id, payload.get("session_id"), node, int(degraded),
            llm.status()["active_model"], latency,
            datetime.now().isoformat(timespec="seconds"),
            json.dumps({"trace": trace, "sources": sources, "failure": failure}, ensure_ascii=False),
        ),
    )
    conn.commit()
    result["trace_id"] = trace_id
    return result


def agent_status() -> dict[str, Any]:
    return {**llm.status(), "nodes": list(NODES)}
