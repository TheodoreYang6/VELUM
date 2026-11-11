---
id: RULE-08
title: 场景配置与 RAG 路由规范
stage: [all]
scenes: [all]
tags: [RAG, 路由, 元数据, 场景, 索引, 维护规范]
source: []
version: 1.5
updated: 2026-11-11
---

# 场景配置与 RAG 路由规范

本文件定义「文档如何被找到」。规则文档是唯一事实源（single source of truth），前端与检索层不得内置第二份牌义。

## 1. 文档元数据规范（YAML frontmatter）

每份 `docs/rules/*.md` 必须含：

```yaml
---
id: RULE-00             # 唯一编号
title: 体系总纲与正统基线
stage: [all]            # 适用环节，见下表
scenes: [all]           # 适用场景 id，见第 2 节
tags: [体系, 历史]       # 自由标签，用于二次重排
source: [URL, ...]      # 溯源
version: 1.0
updated: 2026-11-10
---
```

**stage 取值域**（一次占卜会话的状态机）：

| stage | 含义 | 前端对应 |
| --- | --- | --- |
| `scene-select` | 选择占卜场景 | 环节一：场景选择页 |
| `question` | 确立并校验问题 | 立题页 |
| `ritual-prep` | 环境、道具、事前约定 | 仪式指导页 · 准备 |
| `shuffle-cut` | 洗牌与切牌 | 仪式指导页 · 洗切 |
| `draw` | 抽牌、摆牌、翻牌 | 仪式指导页 · 抽牌 |
| `record` | 录入实际牌面 | 选牌录入页 |
| `interpret` | 生成分析 | 结果页 |
| `close` | 收尾、记录、行动 | 收尾页 |
| `all` | 全环节常驻 | 全局 |

## 2. 场景配置表

| scene id | 显示名 | 典型议题 | 推荐牌阵 | 解读侧重 | 加权标签 |
| --- | --- | --- | --- | --- | --- |
| `love` | 姻缘 | 关系状态、互动模式、亲密课题 | SP-02 关系变体 / SP-05 / SP-03 | 圣杯组、恋人、女皇、星星、月亮 | 情感, 关系, 圣杯, 宫廷牌 |
| `career` | 工作 | 职业阶段、协作、转向、机会 | SP-02 情境变体 / SP-03 / SP-04 | 星币与权杖组、皇帝、战车、魔术师 | 行动, 资源, 星币, 权杖 |
| `study` | 升学 | 去向选择、备考节奏、能力积累 | SP-02 / SP-06 / SP-03 | 宝剑组、星币 3/8/9、隐者、教皇、审判 | 思维, 积累, 抉择, 宝剑 |
| `choice` | 抉择（扩展） | 多选项权衡 | SP-06 | 所有 2 号牌、恋人、正义 | 抉择, 权衡 |
| `general` | 通用指引 | 日常、内在状态 | SP-01 / SP-02 | 按牌面实际分布 | 通用 |
| `cycle` | 周期回望 | 年度、生辰、阶段脉络与实践节奏 | SP-07 / SP-02 | 大阿卡纳、命运之轮、世界、审判、隐者 | 周期, 回望, 节奏, 长程 |
| `self` | 自我与内在 | 反复出现的模式、个人课题、内在基调 | SP-01 / SP-02 / SP-03 | 大阿卡纳、圣杯组、星星、月亮、隐者 | 自我, 内在, 觉察, 模式 |
| `relation` | 人际与家族 | 友谊、家人、协作中的自身角色 | SP-05 / SP-02 | 圣杯组、宫廷牌、女皇、教皇 | 关系, 家族, 协作, 边界 |
| `create` | 创作与项目 | 创作瓶颈、项目推进、表达与产出 | SP-03 / SP-02 | 权杖组、星币组、魔术师、女皇 | 创作, 表达, 行动, 权杖 |
| `place` | 居所与迁徙 | 环境变动、空间、安定感 | SP-03 / SP-06 | 星币组、权杖组、皇帝、战车 | 居所, 变动, 安定, 星币 |
| `wellbeing` | 身心节奏 | 作息、精力、压力下的自我照顾 | SP-02 / SP-01 | 圣杯组、星币组、节制、隐者 | 节奏, 照顾, 平衡, 节制 |
| `all` | 全场景 | — | — | — | — |

**分支规则**：场景决定 ①问题模板集（`RULE-05`）②推荐牌阵（`RULE-03`）③解读时的 tags 加权 ④结果页"场景化综合"的措辞域。场景**不改变**牌义本身，也不预设结论。新增场景只需在此表加一行并补 `RULE-05` 模板，无需改后端代码；前端场景卡字形见 `ScenePage.jsx` 的 `GLYPH` 映射，缺项时回退为「〇」。

**场景说明**（v1.5 起，随 `RULE-00 §0` 转为古典占问范式）：

- `cycle` 周期回望不再限定为「仅作情绪与实践节奏透镜」，可依 `RULE-12 §3` 就阶段时点作占断；`SP-07` 年运十二张沿用同一口径。
- `relation` 不再限定「只读问卜者自身角色」，可依 `RULE-12 §4` 就第三方动向作占断；表述为牌面呈现的角色与状态。
- `wellbeing` 不再排除健康结果类提问，可依 `RULE-12` 与牌义作答，并按 `RULE-07 §2` 附知情提示。
- 上述三类场景与其余场景一样，**不拦截任何问法**；知情提示见 `RULE-07 §3`，不作硬性拒绝。

**场景 id 取值域**（供 frontmatter 与前端使用，全小写）：`love` / `career` / `study` / `choice` / `general` / `cycle` / `self` / `relation` / `create` / `place` / `wellbeing` / `all`。所有规则文档当前均为 `scenes: [all]`，新增场景通过 `tags` 加权命中，无需逐份修改 frontmatter。

**已知局限（诚实标注）**：`RULE-10 / RULE-11` 的逐牌 13 字段详解只包含**姻缘 / 工作 / 升学**三个专属场景提示列。其余场景（含全部新增场景）**没有专属逐牌提示**，解读时以通用牌义 + `scene.focus` 场景侧重 + 加权标签承担。喂料层在缺失专属列时会显式标注「不得借用其他场景提示」，绝不静默回退到姻缘列——否则会造成事实层污染。若要为某场景补专属牌义，需新建独立文档并扩展字段契约，不得就地覆盖 RWS 基线。

## 3. 环节 × 文档 路由矩阵

| 环节 | 必检（hard filter） | 按需检索（semantic top-k） | 常驻 |
| --- | --- | --- | --- |
| scene-select | RULE-03, RULE-05, RULE-08 | RULE-00 | RULE-07 |
| question | RULE-05, RULE-03, RULE-12 | RULE-08（边界判定） | RULE-07 |
| ritual-prep | RULE-04 | RULE-00（逆位与编号约定） | RULE-07 |
| shuffle-cut | RULE-04 | — | RULE-07 |
| draw | RULE-04, RULE-03 | — | RULE-07 |
| record | RULE-01, RULE-02, RULE-03 | — | RULE-07 |
| interpret | RULE-01, RULE-02, RULE-09, RULE-10, RULE-11, RULE-06, RULE-03, RULE-12 | 按抽到的牌名逐张精确召回详解行 + 位置 + 场景 tags + 对应表条目 | RULE-07 |
| close | RULE-06, RULE-04 | — | RULE-07 |

## 4. 检索策略（数据库方案，当前实现）

**明确约束：不使用向量存储、不生成 embedding、不调用外部向量模型。** 全部检索在 SQLite 内完成，文档改动后重建索引即可生效。

1. **硬过滤优先**：`stage ∩ 当前环节 ≠ ∅` 且 `scenes ∩ {当前场景, all} ≠ ∅`。先缩小候选，避免把仪式说明混进牌义解读。字段以逗号分隔字符串存储，用 SQL `instr()` 匹配。
2. **分块**：按 Markdown 二级标题切块，每块 300–600 字，块头继承文档 frontmatter 并附 `section` 标题。表格整表不拆散，避免位置定义被切断。
3. **全文索引**：SQLite **FTS5 + trigram tokenizer**（适配中文子串匹配），索引 `section + tags + text`。
4. **检索 query 组成**：`当前环节 + 场景 + 问题文本 + 已录入牌名列表 + 位置名`。例：`interpret | love | 关于这段关系我最需要看清什么 | 圣杯五/正位 @ 过去, 恋人/逆位 @ 现在`。
5. **打分重排**（可解释，非黑盒）：`牌名精确命中 > stage 精确匹配 > tags/场景加权词命中 > 位置名命中 > FTS5 bm25 > 问题关键词命中`。每个命中项记录 `reasons`，界面可显示「为什么参考了这份文档」。
6. **常驻注入**：`RULE-07` 与免责声明不参与 top-k 淘汰，每次生成都注入。
7. **输出可溯源**：每一段解读参考标注来源 `RULE-xx §小节`，界面上可展开查看原文，便于占卜师核对与手动修订。
8. **降级路径**：FTS5 不可用时自动退回 SQL `LIKE` 关键词匹配，功能不中断。

**已知局限**（诚实标注）：无语义泛化能力，问句用词与文档用词不一致时召回下降。补偿手段是 `tags` 人工标注 + 牌名／位置名精确命中 + 场景模板固定措辞。若日后文档规模超过约 50 份或需跨语言近义召回，再评估引入向量列——届时只需新增一列与一路召回，硬过滤与重排逻辑不变。

## 5. 手动维护流程

1. 直接编辑 `docs/rules/*.md`（Markdown，纯文本，可进 Git）；
2. 递增 `version`、更新 `updated`；若新增 `stage`/`scene` 取值，同步更新本文件第 1、2 节；
3. 触发索引重建：重新分块 → 写入 SQLite `chunks` 表 → 刷新 FTS5 全文索引；
4. 校验清单：
   - frontmatter 可解析且 `id` 唯一；
   - `stage` / `scenes` 取值在枚举内；
   - 牌名属于 78 张合法集合（`RULE-00` + `RULE-01/02`）；
   - 位置定义与 `RULE-03` 牌阵一致；
   - `RULE-07` 保持 `stage: [all]`；
5. 增加新流派（马赛 / 托特 / 自定义牌组）时新建独立文档，**不覆盖** RWS 基线；通过 `scenes` 或新增 `deck` 字段区分。

## 6. 索引 schema（SQLite，当前实现）

```
documents  (doc_id PK, title, file_path, stages, scenes, tags, version, updated, source)
chunks     (chunk_id PK, doc_id FK, section, stages, scenes, tags, text, version)
chunks_fts (FTS5 虚拟表: section, tags, text, tokenize='trigram')
cards      (card_id PK, name, arcana, suit, rank, number, upright, reversed, doc_id)
spreads    (spread_id PK, name, card_count, difficulty, suitable, doc_id)
positions  (spread_id FK, seq, name, meaning)
scenes     (scene_id PK, name, topics, recommended_spreads, focus, tags)
templates  (scene_id FK, seq, text)
routes     (stage PK, required_docs, optional_docs, always_docs)
sessions   (session_id PK, scene_id, spread_id, question, use_reversed, created_at, payload)
```

**无向量列、无外部向量服务。** 前端读取 `scenes` 渲染场景卡，读取 `positions` 渲染牌阵位置槽位，读取 `cards` 渲染 78 张选牌器，读取 `routes` 与 `chunks` 获得当前环节的检索结果——**全部来自同一套文档**，不另建数据仓库。

## 7. 手动维护与前端联动

- 规则文档管理页可在线查看、编辑 Markdown；保存后调用「重建索引」，数据库表即时刷新。
- 新增场景：在 `RULE-08` 第 2 节表格加一行 + 在 `RULE-05` 加一组问题模板，重建索引后前端自动出现新场景卡。
- 新增牌阵：在 `RULE-03` 增加 `## SP-xx` 小节与标准位置表，重建索引后前端自动出现新牌阵。
- 修改牌义：编辑 `RULE-01/02` 表格行，重建索引后选牌器与解读参考同步更新。

## 8. Agent 工作流与大模型边界

**总原则：大模型是表达层，RULE 文档是事实层。** LLM 不得成为牌义、牌阵、仪式或伦理的裁决者。

### 允许接入的五个节点

| 节点 | stage | 作用 | 允许的输出 | 明确禁止 |
| --- | --- | --- | --- | --- |
| `refine_question` | question | 把口语／违规提问改写为更清楚的表述（可选，不强制改写） | 改写句、理由、备选表述 | 改变提问意图、新增信息 |
| `ritual_script` | ritual-prep | 生成可朗读的开场／洗牌／抽牌／收尾引导语 | 四段短句 | 发明任何新仪式、新道具、新禁忌 |
| `narrative` | interpret | 把结构化参考稿改写为连贯叙述 | 概括 + 三段正文 + 语气说明 | 无文档依据的断言 |
| `followups` | close | 生成 2 个追问 | 追问与一句使用提示 | 诱导重复占卜 |
| `final_verdict` | interpret | 综合全部输入产出最终评定，可含寻物／时间／人物／吉凶占断 | 总体评定、基调、核心课题、逐位分析、动态脉络、优势／阻力、行动方向、留意之处 | 引入文档之外的牌义、无依据的空泛断言 |

`final_verdict` 采用**逐牌精确召回**：对每张抽到的牌命中 `RULE-01/02/09` 的对应表格行，再补入位置定义、结构观察、`RULE-12` 对应表条目与 `RULE-07` 知情说明，见 `RULE-06 第 7 节`。

### 不接入大模型、保持规则驱动的环节

- 抽牌与牌面生成——系统永不生成牌；
- 牌义、逆位、牌阵位置、仪式步骤的判定（事实层以 `RULE-01/02/03/12` 为准）；
- 检索本身的硬过滤与路由矩阵（数据库）；
- 知情说明的固定文案（`RULE-07 §3`）。

### 强制约束

1. 每次调用前必须先检索；规则片段为空则**拒绝生成**并降级；
2. 输出经**结构与事实回指校验**（字段完整性、类型安全、占断是否可回指牌面与对应表）；**不再因确定性措辞或问题类型拒绝／降级**；
3. 所有输出附带 `sources` 与运行轨迹，可追溯到 `RULE-xx §小节`；
4. 模型不可用、超时、返回空内容、JSON 解析失败时自动回退规则驱动输出，流程不中断；
5. `LLM_ENABLED=false` 可一键关闭全部节点，退回纯规则模式；
6. 密钥仅存于 `backend/.env`，不进入源码、日志与前端；配置与节点清单见 `/api/agent/status`。

