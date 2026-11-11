# 贡献指南

感谢你考虑为 **VELUM｜帷间** 做出贡献。在提交 Issue 或 Pull Request 前，请花一分钟阅读本文件。

## 行为准则

- 以善意与专业态度交流；尊重不同占卜传统与学习路径。
- 不引入古埃及起源等已被证伪的塔罗伪史；正统基线为 Rider-Waite-Smith（1909）。

## 问题反馈（Issues）

- 尽量提供复现步骤、浏览器 / 系统信息、以及控制台或后端日志片段。
- 涉及牌义或流程的疑问，请引用对应的 `docs/rules/RULE-xx` 文档章节。

## 代码贡献（Pull Requests）

1. Fork 本仓库并基于 `main` 创建特性分支。
2. 后端开发：在 `backend/` 下工作，`python -m py_compile` 应无错误；新增依赖请写入 `requirements.txt` 并注明用途。
3. 前端开发：`cd frontend && npm install && npm run build` 应通过；新增样式请复用 `styles.css` 中的色彩 / 字体变量，保持神秘学宫廷调性（深色墨蓝 + 古金细线 + 衬线标题）。
4. 规范文档（`docs/rules/*.md`）改动：
   - 保持每份文档的 YAML frontmatter 字段完整（`id / title / stage / scenes / tags / source / version / updated`）。
   - 新增流派请新建文档，不要覆盖 RWS 基线。
   - 改动后请在本地启动后端，确认 `/api/index/rebuild` 成功、前端内容随之更新。
5. 提交信息使用中文或英文清晰描述「做了什么 / 为什么」。

## 架构约定

- **规则文档是唯一事实源**：牌义与流程不得在前端二次硬编码。
- **检索不使用向量库 / embedding**：新增检索逻辑请遵循结构化过滤 + FTS5 + 可解释重排。
- **模型调用必须优雅降级**：任何 LLM 调用都应有规则驱动回退，且不得泄露 API Key。

再次感谢你的参与。
