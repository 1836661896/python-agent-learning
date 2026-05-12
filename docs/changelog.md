# 变更记录（详细）

> **用途**：按日期记录**对外行为、架构、文档结构**等变化；篇幅可长于根目录 `readme.md`。  
> **维护**：有变更即追加表格行；根目录 `readme.md` 不再承载完整历史表（仅保留文首索引与当前模块状态）。

---

## 记录格式

建议每条包含：**日期**、**类型**（功能 / API / 数据库 / 文档 / 重构）、**摘要**、必要时 **涉及路径或 PR**。

---

## 变更表

| 日期 | 类型 | 摘要 |
|------|------|------|
| **2026-05-13** | 文档 | **`readme.md` §7**：明确下一步为 **MCP**（本库 **`mcp_dev`/HTTP 服务、`mcp_client` 与 `chat_stream` 的 `mcp` 分支**、同步 **`docs/chat-stream-api.md`**）与 **前端**（会话列表/历史、**SSE `done`** 等）对接；**`changelog`** 本条与提交计划对齐。 |
| **2026-05-12** | API / 测试 / 文档 | **`GET /conversation/list`**、**`GET /conversation/{id}/messages`**（分页、**`kind`/`role`** 筛选、异常 **`fail` + `rollback`**）；**`tests/test_conversations_api.py`**（**`requires_postgres`**）；新增 **`docs/conversations-api.md`**；**`readme.md`** 功能表、API 备忘、**下一次起点**与 **`documentation-index.md`** 同步。 |
| **2026-05-11** | 规则 / 文档 | **`.py` 授权口令**：仅当用户消息含**完全一致**的 **`本次允许修改`** 六字时助手可直接改 **`*.py`**；更新 **`python-learning-agent.mdc`**、**`user-profile.mdc`**、**`collaboration-and-coding-rules.md`**、**`backend-refactor-plan.md`** §9。 |
| **2026-05-11** | 测试 / 文档 | **`conversation_rows_to_messages`** 传入 **`memory_summary`** 并前置 **`system`**；新增 **`tests/test_messages.py`**；**`test_chat_stream`** 断言传给 Ollama 的 **`messages`**（含精炼失败无 **`system`** 分支）；**`docs/chat-stream-api.md`**、**`readme.md`** §3/§7 同步。 |
| **2026-05-11** | 重构 / 测试 / 文档 | **全项目以 `src/` 为准**：删除 **`src_backup/`**；删除依赖旧模块的 **`tests/test_*.py`**，新增 **`test_llm_completion`**、**`test_conversation_refine`**、**`test_chat_stream`**（含 **`requires_postgres`** 可选集成）；**`conftest.py`** 增加 **`requires_postgres`**。**`readme.md`**、**`docs/chat-stream-api.md`**、**`documentation-index.md`** 去掉 **`src_backup`** 表述并同步精炼与测试说明。 |
| **2026-05-10** | 文档 | **`readme.md` §7**：将**聊天记录精炼**列为下一步优先项（每次用户消息触发精炼；历史展示全文、**`messages` 拼装用精炼结果**；输入为**上轮精炼 + 本次原文**）；便于次日开工与提交前对齐计划。 |
| **2026-05-10** | 文档 | **`docs/chat-stream-api.md`**：重写版 **`POST /chat/stream`**（请求体、**`routing`**、SSE **`delta`/`error`/`done`**、**`chat`** 落库与最近 40 条历史、**`plan`/`mcp`** 占位、与 **`src_backup`** 差异）；**`readme.md`** §2～§3、§5、§7 与当前精简 **`src/`** 对齐；**`documentation-index.md`** 增加本文件索引。 |
| **2026-05-09** | 文档 | 建立 **`docs/documentation-index.md`**（文档分工）、**`docs/project-goals.md`**（项目目标）、**`docs/changelog.md`**（本文件）、**`docs/collaboration-and-coding-rules.md`**；**`readme.md`** 改为以架构与模块实现度为主并引用上述文档；**`docs/product-and-refactor-vision.md`** 收缩为以重构与工程对齐为主并指向 `project-goals.md`。 |
| **2026-05-10** | 后端 | 抽出 **`mcp_outcomes.py`**：非流式 MCP 用 **`finalize_mcp_non_stream_*`**；流式 MCP 收尾 **`finalize_stream_mcp_turn`**；**`non_stream._handle_mcp_non_stream`** 只负责白名单与 `call_tool`；**`logic.py`** 流式 MCP 传 **`plan_meta`**（勿用 **`manual_meta`**）。 |
| **2026-05-09** | 后端 / 文档 | Alembic **`1078372ccdda`**（`tool_succeeded`）；**`MEMORY_*`** 与 **`maybe_refine_memory`**；精简根目录 **`readme.md`**（功能表 + 变更表），同步 **`.cursor/rules`** 中 **`user-profile` / `python-learning-checklist` / `python-study-plan`**。 |
| **2026-05-08** | 后端 | **`src/routers/chat/`** 再拆：**`pkg` / `events` / `chat_turn` / `sse` / `logic`**，观测与 SSE 分层。 |
| **2026-05-07** | 后端 / 文档 | 文档化会话消息列表与 **`data.records`** 约定；**`conversations`** 与 **`api_response`** 解耦循环 import。 |
| **2026-05-06** | 后端 | 原 **`chat.py`** 拆为 **`chat/`** 包；路由聚合不变。 |
| **2026-05-04** | 后端 | **`conversation` / `conversation_messages`**；**`/chat`、`/chat/stream`** 与会话记忆、落库与测试。 |
| **2026-05-02** | 后端 | **`GET /events`** 筛选与分页。 |
| **2026-05-01** | 后端 | Planner 纯 JSON、**`/agent/nl-run`** 与 **`/chat/stream`** 对齐；流式 MCP 事件测试补强。 |
| *更早* | — | 服务化、阶段 6 落库、阶段 8 pytest、Ollama **`/chat`**、Docker compose 等 — 详见 **git 历史**。 |

---

*若在迁移本文件前有更老的 `readme` §6 行，可从 git 恢复拷贝至「更早」小节。*
