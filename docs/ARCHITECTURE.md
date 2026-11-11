# The Tarot · 完整设计方案与架构说明

> 文档版本：2026-11-10 · 对应当前工作区代码状态
> 用途：把此前的开发过程从黑盒变成可审阅、可干预的说明书。
> 标注 `[可调]` 的段落是建议人工介入的决策点；第 15、16 节是优先干预队列与操作手册。

---

## 0. 一页速览

| 维度 | 当前方案 |
| --- | --- |
| 产品 | 面向新手占卜师的**仪式辅助与流程规范化工具**；不代抽牌（除可选的线上模式）、不输出确定性预言 |
| 后端 | Python 3.13 + FastAPI 0.162.2 + uvicorn 0.54 |
| 前端 | React 18 + Vite 5，纯 CSS 动效，无 UI 组件库 |
| 存储 | SQLite 3.50/3.53 + **FTS5 trigram**；**无向量存储、无 embedding** |
| 事实源 | `docs/rules/*.md` 共 12 份，YAML frontmatter + Markdown 表格／卡片条目 |
| 索引规模 | 12 文档 → 154 分块、78 张牌、**78 条逐牌详解**、7 牌阵、41 位置、6 场景、20 提问模板、8 条路由、9 个仪式步骤 |
| 大模型 | DeepSeek V4.1 Flash（`deepseek-flash`），5 个 Agent 节点，全部可降级、可关闭 |
| 数据表 | 12 张关系表 + 1 张 FTS5 虚拟表 |
| API | 25 个自定义端点（含牌库列表与详情） |
| 规模 | 约 5,374 行（含规则文档、后端、前端） |

**一句话架构**：Markdown 是唯一事实源 → 解析入库 → 按「环节 + 场景」硬过滤与路由矩阵检索 → 规则驱动生成结构化稿 → 大模型只在表达层做改写与综合评定 → 前端按状态机展示。

### 0.1 品牌标识

| 项 | 内容 |
| --- | --- |
| 名称 | **VELUM｜帷间** |
| 拉丁格言 | ARCANUM SUB VELO（帷幕之下的秘仪） |
| 徽记文件 | `frontend/public/velum-mark.svg`；标签图标 `frontend/public/favicon.svg` |
| 符号构成 | 外环（仪式圆）· 三重菱形（牌背／阿卡纳）· **华盖横杆与两端球饰 · 双层垂弧帷檐 · 左右各三道褶皱的宫廷幕布 · 束带绳结 · 流苏垂珠**，两片主帷向下收拢成 **V**（Velum 首字母，亦是女祭司之帷）· 中央八芒星与虚线光环、八点光尘（星星牌微光）· **对角四枚刻点**（四花色／四元素）· 底部牌桌双线与菱形垂饰 |
| 色 | 底 `#0a0e15`；金 `#c8a45c` / `#e6c987` / `#7c6537` |
| 命名依据 | 工具不替人揭晓答案，只陪问卜者走到帷幕前把仪式做对；与「事实层／表达层分离」的设计一致 |
| 前端呈现 | 侧栏显示徽记 + `VELUM｜帷间` + `ARCANUM SUB VELO / 帷幕之下的秘仪`；抽卡仪式弹窗标题栏带小徽记；页面 title 与 favicon 同步 |

备选名（如需更换）：`SPECULUM｜镜鉴`（塔罗是映照而非预言）、`AULA ARCANA｜秘庭`（宫廷感最强）、`CLAVIS｜密钥`（规则文档是解读之钥）。

---

## 1. 产品定位与不可动摇的原则

1. **事实层 / 表达层分离**：牌义、牌阵位置、仪式步骤、逆位规则、伦理边界永远来自规则文档；大模型只在给定事实范围内组织语言与做关联推理。
2. **单一事实源**：前端场景卡、牌阵槽位、78 张选牌器、问题模板、路由矩阵全部从数据库读取，数据库由文档解析生成；不硬编码第二份牌义。
3. **可解释**：每次检索的命中原因 `reasons`、每段输出的 `RULE-xx §小节` 来源、每次 Agent 运行的轨迹都保留并可在界面查看。
4. **可降级**：模型不可用、超时、空内容、JSON 不完整、护栏未通过，一律回退规则驱动输出，流程不中断。
5. **知情前置**：`RULE-07` 知情说明每次常驻注入；v2.0 古典占问范式下允许明确措辞、吉凶判断与寻物／时间／第三方动向占断，不拦截任何问题类型，但占断须回指 `RULE-12` 对应表条目。
6. **现实仪式优先**：洗牌、切牌、抽牌由问卜者本人完成；系统只指导与记录。线上抽卡是**明确标注的可选分支**。

`[可调]` 第 6 条是后期新增的例外，若你希望工具完全不含随机抽牌，删除 `DrawPage` 入口与 `app/draw.py` 即可，不影响主链路。

---

## 2. 总体架构（四层）

```
┌─ 表现层  React + Vite ────────────────────────────────┐
│  7 步状态机 / 宫廷风 CSS / 4 种抽卡动效 / 结果页        │
│  只通过 /api 与后端交互，不持有任何业务规则              │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP JSON
┌───────────────────────▼──────────────────────────────┐
│  接口层  FastAPI (app/main.py)                         │
│  23 个端点：目录 / 会话 / 检索 / 抽卡 / Agent / 文档管理 │
└──────┬──────────────┬───────────────┬───────────────┘
       │              │               │
┌──────▼─────┐ ┌──────▼──────┐ ┌──────▼────────────────┐
│ 规则驱动层  │ │ 检索层       │ │ Agent 层                │
│ interpreter │ │ retriever    │ │ agent / llm / verdict  │
│ draw        │ │ FTS5+重排    │ │ 5 节点/护栏/降级/轨迹   │
└──────┬──────┘ └──────┬──────┘ └──────┬────────────────┘
       └───────────────┼───────────────┘
               ┌───────▼────────┐        ┌────────────────┐
               │ 数据层 SQLite  │◄───────│ 索引器 indexer │◄── parser
               │ 11 表 + FTS5   │        └────────────────┘     │
               └────────────────┘                              │
                                              ┌───────────────▼───┐
                                              │ 事实源 docs/rules  │
                                              │ 10 份 Markdown     │
                                              └────────────────────┘
```

**关键约束**：表现层与 Agent 层都不直接读 Markdown；只有 `parser.py` 读文档，`indexer.py` 写库，其余模块只读库。

---

## 3. 目录结构与文件职责

```
The Tarot/
├── docs/rules/                 # ★ 唯一事实源，可手动编辑
│   ├── 00-体系总纲.md           RWS 正统基线、78 张结构、数字学、维护约定
│   ├── 01-牌义-大阿卡纳.md      22 张正/逆位关键词表（解析器按表格取列）
│   ├── 02-牌义-小阿卡纳.md      40 数字牌 + 16 宫廷牌 + 元素尊严
│   ├── 03-牌阵.md              7 个牌阵，每个 `## SP-xx` 下必须有三列位置表
│   ├── 04-仪式流程.md          9 个 `## 阶段 N · 名称（stage）` + 线上抽卡边界
│   ├── 05-提问规范.md          六原则、禁忌、按 `### ...（scene: xx）` 分组的模板
│   ├── 06-解读方法.md          四层法、逆位能量层级、输出模板、第 7 节综合评定
│   ├── 07-占卜伦理.md          stage: [all]，常驻注入
│   ├── 08-场景与RAG路由.md      场景表、路由矩阵、stage 枚举、Agent 节点规范
│   ├── 09-牌面详解.md          逐牌图像象征、数字阶段、宫廷角色、元素尊严
│   ├── 10-牌义详解-大阿卡纳.md  ★ 22 张逐牌详解（13 字段，牌库与评定共用）
│   └── 11-牌义详解-小阿卡纳.md  ★ 56 张逐牌详解（13 字段）
├── backend/
│   ├── .venv/                   PyCharm 使用的项目虚拟环境
│   ├── .env                     ★ 密钥（已 gitignore）
│   ├── .env.example             配置模板
│   ├── requirements.txt         fastapi / uvicorn[standard]
│   ├── data/tarot.db            SQLite（运行时生成）
│   ├── app/
│   │   ├── db.py                连接 + 12 张表的 schema + as_csv
│   │   ├── parser.py            ★ 文档解析：frontmatter / 分块 / 牌 / 牌阵 / 场景 / 模板 / 路由 / 仪式步骤
│   │   ├── indexer.py           清表重建 + FTS5 同步
│   │   ├── retriever.py         ★ 硬过滤 + 打分重排 + 路由保底 + 常驻注入
│   │   ├── interpreter.py       结构化解读稿（六区块）组装
│   │   ├── verdict.py           ★ 逐牌精确召回 + 综合评定上下文
│   │   ├── draw.py              4 种模式 + SystemRandom 洗出完整 78 张牌叠
│   │   ├── llm.py               DeepSeek 网关（超时/重试/模型回退/JSON 修复）
│   │   ├── agent.py             ★ 5 节点编排、护栏、降级、轨迹
│   │   └── main.py              FastAPI 路由、会话、文档管理、静态托管
│   ├── build_index.py           命令行重建索引
│   ├── run_dev.py               PyCharm 一键启动
│   ├── verify_env.py            环境自检
│   └── smoke_test.py            端到端回归
├── frontend/src/
│   ├── main.jsx / App.jsx        入口 + 7 步状态机
│   ├── api.js                   全部 /api 调用封装
│   ├── ScenePage / QuestionPage / RitualPage / DrawPage / RecordPage / ResultPage / RulesPage
│   ├── DrawRitualModal.jsx      ★ 全屏抽卡仪式弹窗（洗牌/切牌/逐张抽取/翻牌/确认进度）
│   ├── AgentPanel.jsx           通用 AI 面板（输出 + 轨迹）
│   ├── RetrievalPanel.jsx       各环节检索依据展示
│   ├── Markdown.jsx             轻量 Markdown 渲染
│   └── styles.css / agent.css / draw.css / ritualModal.css / verdict.css
├── .idea/runConfigurations/     PyCharm 运行配置（Backend / Rebuild Index）
└── .gitignore
```

---

## 4. 数据模型（11 张关系表 + 1 张 FTS5 虚拟表）

| 表 | 主键 | 关键字段 | 用途 |
| --- | --- | --- | --- |
| `documents` | doc_id | title, file_path, stages, scenes, tags, version, updated, source | 文档元数据 |
| `chunks` | chunk_id | doc_id, section, stages, scenes, tags, text, version | 按二级标题分块 |
| `chunks_fts` | rowid | section, tags, text（`tokenize='trigram'`） | 中文子串全文检索 |
| `cards` | card_id | name, label, arcana, suit, rank, number, upright, reversed, doc_id | 78 张牌 |
| `card_profiles` | card_id | name, english, number, arcana, correspondence, keywords, imagery, upright, reversed, symbolism, love, career, study, source | **78 条逐牌详解**（牌库与综合评定共用） |
| `spreads` | spread_id | name, card_count, difficulty, suitable | 7 个牌阵 |
| `positions` | (spread_id, seq) | name, meaning | 41 个位置槽位 |
| `scenes` | scene_id | name, topics, recommended, focus, tags | 场景分支配置 |
| `templates` | (scene_id, seq) | text | 20 条提问模板 |
| `routes` | stage | required, optional, always | 环节→文档路由矩阵 |
| `ritual_steps` | seq | name, stage, text | 9 个仪式步骤 |
| `sessions` | session_id | scene_id, spread_id, question, use_reversed, created_at, payload(JSON) | 占卜会话；payload 含 cards / reading / verdict / draw_source |
| `agent_traces` | trace_id | session_id, node, degraded, model, latency_ms, payload | Agent 运行轨迹 |

**元数据编码约定**：`stages` / `scenes` / `tags` 存成 `,a,b,` 形式的逗号分隔字符串，硬过滤用 SQL `instr(stages, ',interpret,') > 0`。这是为了不依赖 JSON1 扩展，代价是无法建多值索引。

`[可调]` 若文档量增大，可改为 `doc_stages(doc_id, stage)` 关联表 + 索引。

---

## 5. 规则文档体系（单一事实源）

### frontmatter 规范

```yaml
id: RULE-09
title: 牌面详解与象征体系
stage: [record, interpret, close]
scenes: [all]
tags: [牌面详解, 象征]
source: [URL, ...]
version: 1.0
updated: 2026-11-10
```

`stage` 枚举：`scene-select / question / ritual-prep / shuffle-cut / draw / record / interpret / close / all`
`scene` 枚举：`love / career / study / choice / general / all`

### 解析器依赖的**格式契约**（改文档时必须遵守）

| 文档 | 契约 | 破坏后果 |
| --- | --- | --- |
| RULE-01 | 7 列表格，首列为 `0` 或罗马数字 | 大牌解析不足 78 张，`build_index` 直接报错 |
| RULE-02 | 表格首列形如 `权杖 Ace` / `权杖侍者` | 小牌缺失 |
| RULE-03 | 每个 `## SP-xx` 下必须有 `\| # \| 位置名 \| 含义 \|` 表 | 牌阵位置丢失 |
| RULE-04 | `## 阶段 N · 名称（stage-id）` | 仪式步骤 stage 归为默认 |
| RULE-05 | `### 标题（scene: id）` + 有序列表 | 场景模板丢失 |
| RULE-10 / RULE-11 | 每节 `## <card_id>`，字段行 `- 名称:` `- 图像:` `- 正位:` `- 逆位:` `- 象征:` `- 姻缘:` 等共 13 项 | 详解缺失或 card_id 重复时 `build_index` 直接报错 |
| RULE-08 | 第 2 节场景表首列为 `` `id` ``；第 3 节路由表首列为 stage | 场景/路由丢失 |
| 任意 | 保持 `RULE-07` 的 `stage: [all]` | 伦理边界不再常驻 |

`indexer.rebuild()` 会自动校验「牌数 = 78」「牌 ID 不重复」，但**不校验** frontmatter 枚举合法性、位置与牌阵一致性——目前靠人工清单（`RULE-08` 第 5 节）。

---

## 6. 索引构建管线

`build_index.py` → `parser.parse_all()` → `indexer.rebuild()`

1. `load_documents()` 读取 10 份 `.md`，拆 frontmatter 与正文；
2. `split_chunks()` 按 `##` 二级标题切块（**表格不拆散**），首块 section = 文档标题；
3. `parse_cards()` 从 RULE-01/02 表格提取 78 张，生成 `major-00`…`pentacles-king`；
4. `parse_spreads()` / `parse_scenes()` / `parse_templates()` / `parse_routes()` / `parse_ritual_steps()` 提取结构化配置；
5. 清表（不清 `sessions` 与 `agent_traces`）→ 写 `documents/chunks/cards/...` → 同步 `chunks_fts`（rowid = chunk_id）；
6. 任一异常回滚，历史会话不受影响。

**触发时机**：服务启动且 `documents` 为空时自动重建；规则页「保存并生效」「重建索引」；命令行 `python build_index.py`。

---

## 7. RAG 检索链（`retriever.py`）

### 7.1 硬过滤

```sql
WHERE (instr(stages, ',interpret,') > 0 OR instr(stages, ',all,') > 0)
  AND (instr(scenes, ',love,')    > 0 OR instr(scenes, ',all,') > 0)
```

先按环节与场景缩小候选，避免把仪式说明混进牌义解读。

### 7.2 路由矩阵（来自 RULE-08 第 3 节，存 `routes` 表）

| stage | 必检 | 常驻 |
| --- | --- | --- |
| scene-select | 03, 05, 08 | 07 |
| question | 05, 03 | 07 |
| ritual-prep / shuffle-cut | 04 | 07 |
| draw | 04, 03 | 07 |
| record | 01, 02, 03 | 07 |
| interpret | 01, 02, 09, **10, 11**, 06, 03 | 07 |
| close | 06, 04 | 07 |

### 7.3 打分重排（可解释）

| 命中项 | 权重 | 说明 |
| --- | --- | --- |
| 路由必检文档 | +4 | 来自 `routes.required` + `optional` |
| stage 精确匹配 | +3 | `all` 文档只 +1 |
| scene 精确匹配 | +2 | |
| 牌名命中 | **+6 / 次**（仅 RULE-01/02）；其他文档 +1.2 / 次 | 防止短牌名在说明性文本里把配置文档抬到顶 |
| 位置名命中 | +2 / 次 | |
| tags 命中 | +2 / 项 | |
| 关键词命中 | min(0.15 × 命中数, 2.0) | 中文按 3–4 字 n-gram 切分 |
| FTS5 bm25 | +2 × 归一化分数 | trigram tokenizer，OR 查询取前 8 个词 |

`[可调]` 所有权重集中在 `retriever.py` 的 `retrieve()` 内，是调召回质量最直接的旋钮。

### 7.4 路由保底召回

排序取 top-k 后，检查 `required` 中每个 doc_id 是否至少出现一次；缺失则从候选中取该文档最高分段，**替换掉 top 中分数最低的非必检段**。这保证 `RULE-06`（解读方法）等必检文档不会被纯相关性排序挤掉。

### 7.5 常驻注入

`get_always_chunks()` 只取 RULE-07 的「免责声明」分块，不参与 top-k 淘汰。

### 7.6 已知局限

无语义泛化：问句用词与文档用词不一致时召回下降，靠 `tags` 人工标注 + 牌名/位置精确命中补偿。文档超过约 50 份时可考虑新增向量列，硬过滤与重排逻辑无需改动。

---

## 8. Agent 工作流（`agent.py` / `llm.py`）

### 8.1 五个节点

| 节点 | stage | 作用 | 输出 |
| --- | --- | --- | --- |
| `refine_question` | question | 口语/违规问题改写为开放式 | refined / reasons / alternatives |
| `ritual_script` | ritual-prep | 可朗读的四段引导语 | opening / shuffle / draw / closing |
| `narrative` | interpret | 结构化稿改写为连贯叙述（**已被 final_verdict 取代，仍保留供单独调用**） | summary / paragraphs |
| `followups` | close | 2 个开放式追问 | questions / note |
| `final_verdict` | interpret | 综合评定 | 见第 9 节 |

### 8.2 单次运行链路

```
retrieve_rules(硬过滤+重排) → [final_verdict 追加] per_card_recall(逐牌精确行)
   → 组装 system(8 条约束) + user(任务/JSON schema/规则片段/结构化记录/长度)
   → DeepSeek chat/completions(json_object, max_tokens 2200/2600, temperature 0.35)
   → extract_json（含代码块剥离、截取、截断补全）
   → 失败则 json_repair 重试一次
   → guardrail：字段完整性 + BANNED_RE 确定性措辞 + 总长 ≤ 4000
   → 通过：附 sources/trace；未通过或异常：_fallback() 规则驱动同字段输出
   → 写 agent_traces
```

`BANNED_RE`：`一定会|必然会|注定会|绝对会|保证会|肯定会|必定会|确诊为|会死|百分百|板上钉钉|必将`

### 8.3 LLM 网关（`llm.py`）

- 配置只从 `backend/.env` 读，密钥不进日志与前端；
- 模型候选顺序：你指定的 `DeepSeek-V4.1-Flash-1017` → `deepseek-flash`（官方别名，实测生效）；
- base_url `https://api.deepseek.com`，端点 `/chat/completions`；
- 超时 40s；429/5xx 退避重试 1 次；空 content 视为失败；
- `LLM_ENABLED=false` 一键关闭全部节点。

### 8.4 降级矩阵

| 故障 | 行为 |
| --- | --- |
| 未配置密钥 / 关闭 | 直接 `_fallback` |
| 网络超时 / HTTP 错误 | 换模型别名 → 仍失败则 `_fallback` |
| JSON 不完整 | 截断补全 → 修复重试 → `_fallback` |
| 护栏命中 | `_fallback` |
| 检索片段为空 | 拒绝无依据生成 → `_fallback` |

前端用 `degraded` 标记显式展示，并把 `failure` 原因显示给用户。

---

## 9. 最终综合评定（`verdict.py`）

**问题背景**：早期 `narrative` 只拿 `synthesis` 摘要与 top-5 泛化片段，prompt 又限制「只能重述」，输出空泛。

**现在的输入**（`build_context()`）：
1. 场景名与侧重、书面问题、牌阵名、逆位设置、牌面来源（线上/手动）；
2. 每张牌的：位置名+位置含义、牌名与朝向、大/小阿卡纳、花色与元素、数字阶段、正位关键词、逆位说明、原型/场景侧重、`RULE-01/02/09` 的**原始表格行**、逐位初读；
3. 结构观察（大牌占比、主导花色、重复数字、逆位比例、元素尊严）；
4. 已有综合线索、行动参考、边界提示。

**逐牌精确召回**：`_table_rows()` 在 RULE-01/02/09 的分块里按牌名定位表格行，每牌最多 4 行；`grounded_excerpts()` 再补牌阵位置定义、RULE-06 方法、RULE-07 边界、RULE-09 结构口径。

**输出 schema**：
`verdict`（一句话）/ `tone` / `core_theme` / `position_analysis[]`（position, card, orientation, reading）/ `dynamics` / `strengths[]` / `challenges[]` / `guidance[]` / `cautions[]` / `summary`

**约束**：允许在给定牌义之间做关联推理，但每个判断须回指具体牌或位置；禁止文档外牌义、吉凶评分、确定性预测；逆位按能量层级说处理。

**生成时机**：`POST /api/sessions/{id}/reading?with_verdict=true` 同步生成，约 5–10 秒，结果写入 `reading.verdict` 并持久化到 session payload。

`[可调]` 这是当前最慢的一环。可改为前端异步轮询 / 流式输出，或把 `max_tokens` 与长度约束收紧。

---

## 10. 线上抽卡：全屏仪式弹窗（`draw.py` / `DrawRitualModal.jsx`）

| 模式 | 牌阵 | 布局与落位 |
| --- | --- | --- |
| `single` | SP-01 | 中央单张，光环扩散 |
| `timeline` | SP-02 / SP-06 | 三张横向时间线 |
| `cross` | SP-03 / SP-05 | 中心 + 四翼十字 |
| `celtic` | SP-04 / SP-07 | 左侧 6 张 2×3 + 右侧 4 张权杖列（**不重叠**） |

**页面分工**：`DrawPage.jsx` 只负责模式与牌阵选择、展示「进入抽卡仪式」入口；真正的仪式在 `DrawRitualModal.jsx` 全屏 `role="dialog"` 弹窗里完成。

**仪式状态机**：
`intro → shuffle → cut → draw(逐张 dealt → flipped) → complete → submitting`

| 阶段 | 交互 | 现实动作对应 |
| --- | --- | --- |
| intro | 点击进入 / Enter | 净手、静置牌盒 |
| shuffle | **按住鼠标在牌桌拖动**（拖动时能量增速翻倍、出现跟随光晕、9 张牌叠交错摆动），或连续按空格；牌叠随鼠标 3D 倾斜 | 桌面搓洗 / 交叠洗牌 |
| cut | 三叠牌，点击任意一叠或按 `C`/空格，累计 3 次合牌 | 分三叠再合起 |
| draw | **整副 78 张牌以扇形展开**（百分比自适应几何，占牌桌下半部）；鼠标滑过牌面抬起高亮、`← →` 移动焦点、点击或空格抽出**你选中的那一张**；牌从扇面位置飞向牌阵槽位（背面朝上）→ 再点击/空格 3D 翻牌；逐张进行 | 摊牌成扇、凭直觉亲手抽一张、逐一翻开 |
| complete | 悬停 / ← → 切换查看每张牌详情 | 通读牌阵 |
| submitting | **点击确认后立即切换为生成进度界面**（三步依次高亮 + 不确定进度条 + 「请勿重复点击」提示），按钮即时禁用 | — |

**键盘**：`Space` 洗牌/抽牌/翻牌、`Enter` 推进、`C` 切牌、`←/→` 查看、`Esc` 退出；`submitting` 期间禁止关闭。
**鼠标感应**：`onMouseMove` 写入 `--mx/--my`，驱动牌叠 3D tilt 与跟随光晕。

**逆位呈现修正**：牌面文字始终正立，仅符号旋转 180° 并标注「逆位」，避免旧版整块文字倒置不可读。
**牌面来源（关键）**：打开弹窗时 `/api/draw` 返回 `deck`——后端用 `SystemRandom` 洗好的**完整 78 张乱序牌叠**（每张带预先确定的正/逆位朝向），以及 `deck_details`。前端把 deck 按索引摊成扇面；**用户在扇面上点哪一张，该索引对应的牌就是本次抽到的牌**。点选结果组装成 `picks[]` 提交给 `save_cards`，走与手动录入完全相同的校验。牌阵槽位在上半部（y 24%–46%），扇面在下半部（y 70%–82%），纯百分比几何保证不同屏幕不重叠。

其余约定不变：结果按位置生成 `{seq, card_id, reversed, note}`，与手动录入共用 `save_cards` 校验；会话写 `draw_source: online`；支持 `prefers-reduced-motion`。

**会话配置同步（修复 400 的关键）**：会话在立题时创建并固定 `spread_id / use_reversed`，但抽卡页允许随后切换牌阵。`/api/draw` 携带 `session_id` 时会把会话的 `spread_id`、`use_reversed` 同步为本次抽卡所用值；若发生变化，同时清空该会话已录入的牌与解读，避免提交时报「牌位数量不符」。响应中的 `session_synced` 标记是否发生同步。`save_cards` 的错误信息现会带出会话牌阵与收到的位置数，便于定位。

**两套槽位布局**：抽牌阶段扇面占据牌桌下半部（y 70%–82%），已抽出的牌按抽取顺序排成上半部 1–2 行缩略槽位（`drawSlotLayout`）；牌阵完成后扇面收起，牌平滑移动到 `LAYOUT_FULL` 的真实牌阵坐标。`ritual-frame` 的 `data-phase` / `data-count` 控制牌尺寸，避免 10 张牌挤在一起。

`[可调]` 扇形弧度、水平张角与倾斜角度集中在 `DrawRitualModal.jsx` 的 `FAN` 常量与 `fanGeom()`；牌背尺寸与悬停抬升在 `ritualModal.css` 的 `.fan-card`。若要改成「每抽一张都独立请求后端」，可拆出逐张接口，前端状态机不变。

---

## 11. 前端状态机与页面

| # | step | 页面 | 主要数据来源 |
| --- | --- | --- | --- |
| I | scene | ScenePage | `/api/scenes`、`/api/spreads` |
| II | question | QuestionPage | `/api/question/check`、场景模板、AgentPanel(refine_question) |
| III | ritual | RitualPage | `/api/ritual`、牌阵位置、AgentPanel(ritual_script) |
| IV | draw | DrawPage（模式选择）+ DrawRitualModal（全屏仪式） | `/api/draw/modes`、`/api/draw` |
| V | record | RecordPage | `/api/cards`、牌阵位置 |
| VI | result | ResultPage | `reading` + `reading.verdict`、AgentPanel(followups) |
| VII | library | CardLibraryPage + CardDetailModal | `/api/card-library` |
| VIII | rules | RulesPage | `/api/rules`、`/api/agent/status`、`/api/agent/traces` |

**视觉系统**（`styles.css`）：深色墨蓝 `#0d1014`、古金 `#c8a45c`、衬线标题、菱形纹章、发丝金线、三层留白节律；克制极简 Skill 只借用明度分层与字号对比，繁复宫廷装饰按用户指定执行。

---

### 11.2 牌库（游戏集卡式）

`CardLibraryPage` 以卡片网格呈现 78 张牌：花色分组筛选、名称／英文／关键词搜索、悬停 3D 抬起、大阿卡纳旋转光环、按花色分色的 `--accent`；「已阅 x/78」进度写入 `localStorage`（键 `velum.viewed`），翻开过的牌带金色「已阅」印记。

`CardDetailModal` 为全局卡牌详情：左侧大卡面 3D 翻开入场，右侧分栏展示牌面图像、正位、逆位、象征与姻缘／工作／升学三场景提示；支持「上一张／下一张」、`← →` 与 `Esc`。**结果页逐位释义与最终评定的牌名均可点击直接打开对应卡牌**，不切换当前步骤。

### 11.1 面向用户文案约定（2026-11-10 清理）

前端界面**不显示任何内部实现细节**：文档编号 `RULE-xx`、牌阵编号 `SP-xx`、分块数／候选数、权重与命中原因、路由与常驻注入、存储方式、模型名与耗时、密钥信息、Agent 节点／工具名、stage 字段、原始异常文本，均不出现在用户可见文案中。

- `src/labels.js` 集中把文档编号映射为中文规范名、把生成轨迹映射为中文阶段名，并提供统一的用户向错误文案；
- `src/Markdown.jsx` 在渲染规则文档正文时，把文档编号与内部字段标记替换为中文表述；
- `src/api.js` 对非 2xx 统一抛出用户向文案，避免异常细节泄漏；
- 仍需展示的信息改为状态提示：规范库「已就绪」、智能解读「已开启／已关闭」、生成「已完成／已按内置规范生成」、参考「已根据当前环节与场景，查阅相关规范」；
- 所有展开／收起、检测连接、编辑保存、刷新规范库等交互与布局保持不变；
- **唯一保留原文**的是「规范维护」页的编辑器文本域——它是显式的维护功能，必须可编辑 Markdown 原文；该页其余技术卡片均已改为用户向状态。

## 12. API 全清单（25 个）

| 分组 | 端点 |
| --- | --- |
| 健康 | `GET /api/health` |
| 目录 | `GET /api/scenes`、`/api/spreads`、`/api/cards`、`/api/ritual`、`/api/routes` |
| 牌库 | `GET /api/card-library`（78 条详解）、`GET /api/card-library/{card_id}` |
| 检索 | `POST /api/retrieve`、`POST /api/question/check` |
| 会话 | `POST /api/sessions`、`POST /api/sessions/{id}/cards`、`POST /api/sessions/{id}/reading`、`GET /api/sessions`、`GET /api/sessions/{id}` |
| 抽卡 | `GET /api/draw/modes`、`POST /api/draw` |
| Agent | `GET /api/agent/status`、`POST /api/agent/probe`、`POST /api/agent/run`、`GET /api/agent/traces` |
| 文档 | `GET /api/rules`、`GET /api/rules/{id}`、`PUT /api/rules/{id}`、`POST /api/index/rebuild` |

`PUT /api/rules/{id}` 会先写文件再 `rebuild()`；解析失败则**回滚文件内容并重建索引**，避免污染文档库。

---

## 13. 配置、环境与端口

| 项 | 值 |
| --- | --- |
| 项目根 | `D:\app_life\The Tarot` |
| PyCharm 解释器 | `backend\.venv\Scripts\python.exe` |
| 后端工作目录 | `backend` |
| 后端入口 | `run_dev.py`（8000）或 `python -m uvicorn app.main:app --port 8000` |
| 当前预览 | `http://127.0.0.1:8001/`（刻意避开 PyCharm 的 8000） |
| 前端开发 | `npm run dev`（5173，Vite 代理 `/api` → 8000） |
| 生产托管 | `npm run build` 生成 `frontend/dist`，由后端单端口托管 |
| 数据库 | `backend/data/tarot.db` |
| LLM 配置 | `backend/.env`（`DEEPSEEK_API_KEY` / `BASE_URL` / `MODEL` / `FALLBACK` / `LLM_ENABLED` / `LLM_TIMEOUT`） |

`.env`、`.venv/`、`data/*.db`、`node_modules/`、`dist/` 已 gitignore。

---

## 14. 关键设计决策（ADR 摘要）

| # | 决策 | 理由 | 代价 / 可调点 |
| --- | --- | --- | --- |
| A1 | 数据库检索，不用向量 | 10 份文档规模下可解释、可手改、无 embedding 成本 | 无语义泛化；`[可调]` 加向量列不影响硬过滤 |
| A2 | Markdown 为单一事实源 | 用户要「手动管理维护」 | 解析器依赖表格格式契约，改格式要同步解析器 |
| A3 | 硬过滤 + 路由保底 + 打分重排 | 纯相关性会漏掉必检文档 | 权重需人工调，集中在 `retriever.py` |
| A4 | 大模型只做表达层 | 避免污染事实与可追溯性 | 输出仍依赖文档质量；`[可调]` 放宽/收紧 system 第 8 条 |
| A5 | 全链路降级 | 模型不稳定时功能不中断 | 降级文案较朴素，存于 `agent._fallback()` |
| A6 | 线上抽卡设为可选分支 | 与「不代抽牌」原则冲突，明确边界而非默认化 | `[可调]` 可整体移除 |
| A7 | 综合评定同步生成 | 结果页一次拿到最终输出 | 5–10 秒等待；`[可调]` 改异步 |
| A8 | 会话 payload 用 JSON | 结构灵活、免迁移 | 无法按 `draw_source` 等字段做 SQL 筛选 |

---

## 15. 已发现的不一致与技术债（**建议优先人工干预**）

| # | 问题 | 位置 | 影响 |
| --- | --- | --- | --- |
| D1 | `RULE-08` 第 6 节 schema 描述的列名与 `db.py` 实际不一致（`recommended_spreads` vs `recommended`、`required_docs` vs `required`），且漏列 `ritual_steps`、`agent_traces`、`label` 字段 | `docs/rules/08` / `backend/app/db.py` | 照文档改库会出错 |
| D2 | `RULE-08` 第 4 节称「FTS5 不可用退回 SQL LIKE」，实现是 `_fts_scores` 捕获异常返回空分数字典（靠关键词命中兜底），并无 LIKE 分支 | `retriever.py` | 文档承诺与实现不符 |
| D3 | `RULE-08` 第 5 节的 frontmatter 枚举/一致性「校验清单」是人工步骤，`indexer` 只自动校验 78 张牌与 ID 唯一 | `indexer.py` | 改错 stage/scene 不会报错 |
| D4 | `agent.NODES`（代码）与 `RULE-08` 第 8 节（文档）是节点定义的**双份来源** | `agent.py` / `RULE-08` | 加节点要改两处，违背单一事实源 |
| D5 | `final_verdict.position_analysis` 未校验数量是否等于牌位数 | `agent._validate()` | 模型可能少给某一位置 |
| D6 | `draw_source` 只在 session payload 里，历史列表接口不返回 | `main.py /api/sessions` | 无法按来源筛选历史 |
| D7 | `narrative` 节点已无页面入口但仍在 NODES 与 smoke test 中 | `agent.py` | 保留可单独调用，也可清理 |
| D8 | 前端 `STEPS` 与 `RULE-08` stage 枚举各自定义，新增环节要改多处 | `App.jsx` / `RULE-08` | 扩展性受限 |
| D9 | `npm audit` 报 2 个依赖漏洞（Vite 5 链路，1 moderate / 1 high），未强制升级 | `frontend/package.json` | 安全债务 |
| D10 | 密钥曾明文出现在对话中，建议轮换 | `backend/.env` | 安全风险 |
| D11 | 旧版舞台样式（`.draw-stage`、`.draw-card`、`@keyframes deal*` 等）仍留在 `draw.css`，新版弹窗已不再使用 | `frontend/src/draw.css` | 约 100 行死代码，CSS 体积偏大 |
| D12 | 已解决：后端返回完整 78 张洗好牌叠，用户在扇面上的点选真实决定结果；剩余差异是牌的正/逆位朝向在洗牌时已确定（与现实一致），而非抽出瞬间决定 | `app/draw.py` + `DrawRitualModal` | 无功能影响 |

---

## 16. 人工干预操作手册

### 改内容（最安全，无需改代码）

| 想改什么 | 改哪里 | 生效方式 |
| --- | --- | --- |
| 牌义、逆位关键词 | `RULE-01/02` 表格行 | 规则页「保存并生效」或 `python build_index.py` |
| 新增/修改牌阵位置 | `RULE-03` 的 `## SP-xx` 三列表格 | 同上，前端自动出现 |
| 仪式步骤 | `RULE-04` 的 `## 阶段 N · 名称（stage）` | 同上 |
| 场景与推荐牌阵 | `RULE-08` 第 2 节表格 + `RULE-05` 模板 | 同上，前端自动出现新场景卡 |
| 环节参考哪些文档 | `RULE-08` 第 3 节路由表 | 同上 |
| 伦理措辞 / 免责声明 | `RULE-07` | 同上，常驻注入立即生效 |
| 牌面详解深度 | `RULE-09` 表格行 | 同上，直接影响综合评定质量 |

### 改策略（需改代码）

| 想改什么 | 文件 / 函数 |
| --- | --- |
| 检索权重、top-k | `retriever.retrieve()` |
| 打分是否保底必检文档 | `retriever.retrieve()` 中 "Route guarantee" 段 |
| 大模型语气、允许/禁止项 | `agent.SYSTEM_PROMPT` |
| 各节点任务与输出 schema | `agent.NODES` |
| 护栏词表与字段校验 | `agent.BANNED_RE` / `_validate()` |
| 降级文案 | `agent._fallback()` |
| 综合评定输入字段 | `verdict.build_context()` / `grounded_excerpts()` |
| 综合评定输出结构 | `agent.NODES['final_verdict']['schema']` + `ResultPage.VerdictBlock` |
| 抽卡模式定义 | `draw.MODES`（后端模式元数据） |
| 抽卡仪式阶段、布局、动效 | `DrawRitualModal.jsx` 的 `LAYOUT` / 阶段状态机 + `ritualModal.css` |
| 扇形弧度、张角、牌背尺寸 | `DrawRitualModal.jsx` 的 `FAN` / `fanGeom()` + `ritualModal.css` 的 `.fan-card` |
| 洗牌拖动灵敏度、切牌次数 | `onStageMove()` 的能量系数、`doCut()` 的 3 次阈值 |
| 确认后的生成进度反馈 | `DrawRitualModal` 的 `confirming` 分支 + `App.submitCards` 的 true/false 返回值 |
| 结果页六区块模板 | `interpreter.build_reading()` |

### 改完必须跑

```
backend/.venv/Scripts/python.exe backend/verify_env.py     # 环境自检
backend/.venv/Scripts/python.exe backend/build_index.py    # 重建索引
cd frontend && npm run build                               # 前端构建
backend/.venv/Scripts/python.exe backend/smoke_test.py     # 全链路回归（需后端在 8000）
```

---

## 17. 已知限制

1. 无向量检索，语义泛化弱；靠 tags 与牌名精确命中补偿。
2. 综合评定 5–10 秒同步等待；模型含 `reasoning_content` 会额外消耗 token。
3. 无登录与用户体系，占卜记录存在本地 SQLite，前端暂无历史记录页。
4. 解读是规则组装 + 大模型组织语言的结构化参考稿，不是自由对话式咨询。
5. 线上抽卡为数字模拟，不具备现实仪式意义。
6. 规则文档编辑页保存后会重建整库索引（当前规模下 < 1 秒），文档量大时需改增量索引。
