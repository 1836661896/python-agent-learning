# Python Agent 学习项目 — 后端仓库说明

> **换设备 / 新对话**：根目录本文件 + **`docs/documentation-index.md`**（各文档职责）+ **`.cursor/rules/python-study-plan.mdc`** + **`python-learning-checklist.mdc`** + **`user-profile.mdc`**。  
> **详细变更历史**：**`docs/changelog.md`**。  
> **流式聊天接口约定**：**`docs/chat-stream-api.md`**（`POST /chat/stream`、SSE、`routing`、与旧版差异）。  
> **中长期目标（排期与学习方向）**：**`docs/project-goals.md`**。  
> **重构工程共识**：**`docs/product-and-refactor-vision.md`**；**执行清单**：**`docs/backend-refactor-plan.md`**。

---

## 1. 项目是做什么的

- **定位**：以 **FastAPI 后端 + Agent/LLM 联调** 为主线的 **Python 学习仓库**；与 **React 前端**（`frontend/readme.md` 或 `myproject/frontend`）联调。  
- **长期方向**：**`.cursor/rules/project-goal-advanced-agent.mdc`**。  
- **协作与编码约定（摘要）**：**`docs/collaboration-and-coding-rules.md`**（权威规则在 **`.cursor/rules/`**）。

---

## 2. 后端目录与架构（摘要）

仓库以当前 **`src/`** 为唯一后端实现；历史代码若需对照请查 **git 历史**（**`src_backup` 已移除**）。

```
src/
├── api.py                 # FastAPI 入口：CORS、校验/HTTP 异常、/health、挂载 chat router
├── api_response.py        # 统一 JSON：{ code, data, msg }
├── db/                    # DATABASE_URL、SessionLocal、Base、get_db
├── models/                # Conversation、ConversationMessage（MessageRole 等）
├── schemas/               # ChatRequest、RoutingMode 等
├── types.py               # MessageMode 等与请求/落库对齐的类型
├── llm/                   # config、Ollama 流式/非流式（/api/chat）、messages 拼装
├── routers/
│   └── chat/              # POST /chat/stream（StreamingResponse + SSE）
├── services/
│   ├── chat_stream.py     # 路由解析、会话与消息落库、流式、精炼落库
│   └── conversation_refine.py  # memory_summary 精炼（非流式 LLM）
└── utils/
    └── sse_events.py      # build_*_event、sse_line
```

**Alembic**：仓库根 `alembic/`；表结构仍与历史迁移一致；迁移命令见下文「环境与启动」。

---

## 3. 功能模块与实现程度

> **约定**：**仅记录当前 `src/` 中已存在或已部分落地的能力**；实现程度：**已完成** / **进行中** / **未挂载**。流式聊天字段级约定见 **`docs/chat-stream-api.md`**；变更流水见 **`docs/changelog.md`**。

| 模块 | 主要路径 | 实现程度 | 说明 |
|------|-----------|-----------|------|
| 应用入口 | `src/api.py` | 已完成 | 仅 **`GET /health`** + **`POST /chat/stream`**（**`SessionLocal()`** 须在生成器内创建并在 **`finally`** 中 **`db.close()`**） |
| 健康检查 | `GET /health` | 已完成 | 返回 **`api_response.success`** |
| 流式聊天 | `routers/chat/router.py`、`services/chat_stream.py` | 已完成 | **`routing`**：`auto`（当前恒走 **`chat`**）\|`chat`\|`plan`\|`mcp`；**`plan`/`mcp`** 占位返回 **`error` + `done(conversation_id=null)`** |
| 会话与消息落库 | `models/conversation.py` 等 | 已完成 | **`chat`**：写 user → 精炼 **`memory_summary`** → 流式 assistant → **`turn_id`** 配对；历史 **最近 40 条**（**`id desc` + `reversed`**） |
| Ollama 流式 | `llm/streaming.py`、`llm/messages.py` | 已完成 | **`/api/chat`** **`stream: true`**；消息角色由 **`MessageRole.value`** 映射 |
| SSE | `utils/sse_events.py` | 已完成 | **`delta` / `error` / `done`** |
| 非流式 `POST /chat`、Planner、MCP HTTP、`/tasks`、`/agent`、`/events`、`/conversations`… | — | **未挂载** | 按 **`docs/backend-refactor-plan.md`** 在现行 **`src/`** 上扩展；落地后更新本表 |
| 会话记忆精炼 | `conversation_refine.py`、`chat_stream.py`、`llm/messages.py` | **已完成** | 每轮 user 后精炼落库；**`conversation_rows_to_messages`** 在非空摘要时前置 **`system`**，否则仅最近 **40 条**角色对话；API 历史仍为消息表**原文** |
| 工程 | `Dockerfile`、`docker compose`、`alembic/`、`tests/` | 部分 | **`tests/`** 已对齐精简栈（**`pytest tests`**；含可选 PostgreSQL 集成用例，无库时 **skip**） |

### 3.1 合规（与当前代码一致的一行）

不以「外网搬运视频到 B 站/抖音」等为学习目标；自动化与采集类能力需合规、白名单与二次确认（细则随功能扩展，见 **`docs/project-goals.md`**）。

---

## 4. 环境与启动

- **Python**：虚拟环境 `.venv`；依赖 **`requirements.txt`**。  
- **激活**：Windows：`.venv\Scripts\activate`；Unix：`source .venv/bin/activate`。  
- **本地 API**：`uvicorn src.api:app --reload`（默认 `http://127.0.0.1:8000`）。  
- **数据库**：`.env` 中 `DATABASE_URL`；迁移 **`alembic upgrade head`**。列名 **`tool_succeeded`** 等与迁移 **`1078372ccdda`** 及 ORM 一致。  
- **Ollama**：`.env` 中 `OLLAMA_*`；若本机 `curl` 正常而接口 502，对 `httpx` 使用 **`trust_env=False`** 避免代理误伤 `127.0.0.1`。  
- **Docker**：`docker compose up -d api`；容器内迁移 `docker compose run --rm api alembic upgrade head`；容器访问宿主机 Ollama 可用 `OLLAMA_BASE_URL=http://host.docker.internal:11434`（Docker Desktop）。

---

## 5. API 约定备忘

- **统一 JSON 响应**（**`/health` 等非 SSE**）：`{ "code", "data", "msg" }`；校验错误经异常处理器返回 **`code != 0`** 风格。  
- **`POST /chat/stream`**：**`text/event-stream`**；**`data:`** 后为 JSON，含 **`type`**：**`delta`**（**`text`**）、**`error`**（**`msg`**）、**`done`**（**`conversation_id`**、**`turn_id`**）。详见 **`docs/chat-stream-api.md`**。  
- **历史分页 API**（**`data.records`** 等）：当前 **`src/` 未挂载**；实现时补路由与 **`pytest`**。

---

## 6. 前端

- **`frontend/readme.md`**、**`frontend/.cursor/rules/`**。

---

## 7. 下一次学习的起点

1. **聊天记录精炼**  
   - **已实现**：精炼落库 + **`messages`** 首条 **`system`** 携带摘要（见 **`docs/chat-stream-api.md`**）；列表/API 仍返回消息**原文**。  
   - **可选演进**：过长摘要再压缩、或更早轮次 user 条目不重复进 **`messages`** 等。  

2. **后端（当前精简栈）**：按需挂载 **`GET /conversations/{id}/messages`**、**`POST /chat` 非流式**；**`plan`/`mcp`** 接入真实能力时更新 **`docs/chat-stream-api.md`**。  
3. **能力扩展**：对照 **`docs/backend-refactor-plan.md`** 在 **`src/`** 内逐步实现，并同步 **`readme.md` §3** 与 **`docs/changelog.md`**。  
4. **前端**：**SSE** 解析 **`done`** 中的 **`conversation_id` / `turn_id`**；错误态与 **`routing`** 占位文案联调。

---

## 8. 提交前约定

1. 更新 **`readme.md`**（与本仓库代码状态一致，尤其 **§3 功能模块与实现程度**）及 **`docs/changelog.md`**（本条变更摘要）。  
2. 若 **产品目标** 有变，更新 **`docs/project-goals.md`**。  
3. 若 **文档体系或协作规则** 有变，更新 **`docs/documentation-index.md`** 与 **`docs/collaboration-and-coding-rules.md`**，并检查 **`.cursor/rules/user-profile.mdc`** 是否需要同步。  
4. `git add` / `commit` / `push`。

---

## 9. 学习日志（可选）

长叙事建议写个人笔记或独立文件，避免本文件膨胀；索引见 **`docs/documentation-index.md`**。
