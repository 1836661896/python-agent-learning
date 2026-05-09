# Python Agent 学习项目 — 进度与说明

> 换设备 / 新对话：先读本文件 + `.cursor/rules/python-study-plan.mdc` + `.cursor/rules/python-learning-checklist.mdc` + `.cursor/rules/user-profile.mdc`。  
> **后端重构（去 tasks / builtin / agent.run，Planner 仅 mcp+chat）**：进度与执行清单见 **`docs/backend-refactor-plan.md`**。

---

## 1. 项目是做什么的

- **定位**：以 **FastAPI 后端 + Agent/LLM 联调** 为主线的 **Python 学习仓库**；与 **React 前端**（见 `frontend/readme.md` 或 `myproject/frontend`）联调。
- **长期方向**（自动化、视觉、高级编排）：见 `.cursor/rules/project-goal-advanced-agent.mdc`。

---

## 2. 要实现的功能（目标分层）

### 2.1 当前代码已具备（验收以路由与测试为准）

| 领域 | 能力摘要 |
|------|----------|
| **健康与任务** | `GET /health`；`GET/POST/DELETE /tasks`（PostgreSQL + SQLAlchemy + Alembic） |
| **Agent 工具** | `POST /agent/run`（命令 → `run_tool`）；`POST /agent/nl-run`（自然语言 → planner → 白名单工具）；`POST /agent/mcp-run`；`GET /agent/last-step`、`GET /agent/steps` |
| **聊天** | `POST /chat`（非流式）、`POST /chat/stream`（SSE：`delta` / `done` / `error`）；planner 分支：`mcp` / `builtin` / `chat`；多 LLM 提供商与 fallback（`src/llm/`） |
| **会话与记忆** | `conversation` / `conversation_messages`；`ChatRequest` 可选 `conversation_id`；`GET /conversations/{id}/messages`（分页 `data.records`）；`conversation_memory`（含 `maybe_refine_memory`、`MEMORY_*`） |
| **可观测** | `GET /events`（分页 + `type` / `command` / `status`）；chat/agent 侧事件落库与结构化日志（`obs_log`） |
| **MCP** | `GET /mcp/health`、`GET /mcp/tools`、`POST /mcp/call`（与聊天侧 MCP 流式/非流式配合） |
| **文档支线** | `POST/GET /doc-sessions`、消息、生成、`GET .../download`（多轮 + docx，见 `src/routers/doc_sessions.py`） |
| **工程** | `pytest` 覆盖核心 API；根目录 `Dockerfile` + `docker compose`（`db` + `api`）；UTC 时间格式化工具模块 |

### 2.2 主线待完善（与产品共识一致）

- **非流式 `POST /chat`**：planner → **MCP** 成功/失败收口后，响应 **`data` 与事件** 与 chat/fallback 分支对齐，补齐 **`conversation_id` / `turn_id`**（实现入口：`src/routers/chat/mcp_outcomes.py` 与调用链）。
- **左栏时间线**：与 **`GET /events`**、`conversation_id` / `turn_id` 前端联调稳定。
- **流式体验**：右侧聊天消费 SSE 结构化事件（含工具起止等）与前端阶段 3+ 衔接。
- **`doc_sessions` 与通用会话**：绑定 **`conversation_id`**，复用 **`build_augmented_user_text`**（规划中）。
- **分级路由、鉴权（阶段 9）、Redis/异步**：按需渐进；对外暴露工具/流式前先评估鉴权。

### 2.3 合规边界（共识）

不以「外网搬运视频到 B 站/抖音」等为学习目标；自动化与采集类能力需合规、白名单与二次确认。

---

## 3. 环境与启动（摘要）

- **Python**：虚拟环境 `.venv`；依赖见 `requirements.txt`。
- **激活**：Windows：`.venv\Scripts\activate`；Unix：`source .venv/bin/activate`。
- **本地 API**：`uvicorn src.api:app --reload`（默认 `http://127.0.0.1:8000`）。
- **数据库**：`.env` 中 `DATABASE_URL`；迁移 `alembic upgrade head`。列名 **`tool_succeeded`** 等与迁移 `1078372ccdda` 及 ORM 一致。
- **Ollama**：`.env` 中 `OLLAMA_*`；若本机 `curl` 正常而接口 502，对 `httpx` 使用 **`trust_env=False`** 避免代理误伤 `127.0.0.1`。
- **Docker**：`docker compose up -d api`；容器内迁移 `docker compose run --rm api alembic upgrade head`；容器访问宿主机 Ollama 可用 `OLLAMA_BASE_URL=http://host.docker.internal:11434`（Docker Desktop）。

---

## 4. API 约定备忘

- **统一响应**：业务层多为 `{ "code", "data", "msg" }`（校验错误亦尽量统一为 `code != 0` 风格）。
- **分页列表**：`GET /events`、`GET /conversations/{id}/messages` 成功时列表在 **`data.records`**，并含 **`page` / `limit` / `total`**。
- **`POST /chat`**：可选 **`conversation_id`**；多数路径会在 **`data`** 中返回 **`conversation_id`**；**planner→MCP 非流式**路径仍以代码为准核对是否含 **`turn_id`**。

---

## 5. 前端与规则

- 前端目录、阶段与规则：**`frontend/readme.md`**、**`frontend/.cursor/rules/`**。
- 教学与「助手能否直接改 `.py`」等：**`.cursor/rules/python-learning-agent.mdc`**。

---

## 6. 变更记录（按日期，只记对外行为或架构变化）

| 日期 | 摘要 |
|------|------|
| **2026-05-10** | 抽出 **`mcp_outcomes.py`**：非流式 MCP 用 **`finalize_mcp_non_stream_*`**；流式 MCP 收尾 **`finalize_stream_mcp_turn`**；**`non_stream._handle_mcp_non_stream`** 只负责白名单与 `call_tool`；**`logic.py`** 流式 MCP 传 **`plan_meta`**（勿用 **`manual_meta`**）。 |
| **2026-05-09** | Alembic **`1078372ccdda`**（`tool_succeeded`）；**`MEMORY_*`** 与 **`maybe_refine_memory`**；同日 **文档**：精简根目录 **`readme.md`**（§2 功能表 + §6 变更表），同步 **`.cursor/rules`** 中 **`user-profile` / `python-learning-checklist` / `python-study-plan`**。 |
| **2026-05-08** | **`src/routers/chat/`** 再拆：**`pkg` / `events` / `chat_turn` / `sse` / `logic`**，观测与 SSE 分层。 |
| **2026-05-07** | 文档化会话消息列表与 **`data.records`** 约定；**`conversations`** 与 **`api_response`** 解耦循环 import。 |
| **2026-05-06** | 原 **`chat.py`** 拆为 **`chat/`** 包；路由聚合不变。 |
| **2026-05-04** | **`conversation` / `conversation_messages`**；**`/chat`、`/chat/stream`** 与会话记忆、落库与测试。 |
| **2026-05-02** | **`GET /events`** 筛选与分页。 |
| **2026-05-01** | Planner 纯 JSON、**`/agent/nl-run`** 与 **`/chat/stream`** 对齐；流式 MCP 事件测试补强。 |
| *更早* | 服务化（**`agent_service` + `routers` + `schemas` + `api_response`**）、阶段 6 落库、阶段 8 pytest、Ollama **`/chat`**、Docker compose 等 — 详见 **git 历史**与本表之前版本的备份（若需要）。 |

---

## 7. 下一次学习的起点

1. **后端优先**：非流式 **`POST /chat` → MCP** 的 **`data`（及必要时的 events）** 补齐 **`conversation_id` / `turn_id`**；自测后更新本节与上表。
2. **前端**：阶段 3 请求层与错误态；为 **SSE** 预留/接入 **`ChatPanel`**。
3. **支线**：`doc_sessions` ↔ **`conversation_id`** + **`build_augmented_user_text`**；提交前 **`python -m pytest -q`**。

---

## 8. 提交前约定

1. 更新本文件 **§6 变更记录**（日期 + 一行摘要）及 **§7**（若起点变化）。
2. 保存后 `git add` / `commit` / `push`。

---

## 9. 学习日志（可选，长叙事可写个人笔记）

早期命令行阶段与 2026-01～03 的逐日细节已从主文档拆出；若需长叙事可在本节后追加小节，或单独笔记文件以免本文件再次膨胀。
