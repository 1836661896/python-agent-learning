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

当前 **`src/`** 为**精简重写**（与 **`src_backup/`** 中历史全量路由并存；旧版行为以备份与 **`docs/changelog.md`** 为准）。

```
src/
├── api.py                 # FastAPI 入口：CORS、校验/HTTP 异常、/health、挂载 chat router
├── api_response.py        # 统一 JSON：{ code, data, msg }
├── db/                    # DATABASE_URL、SessionLocal、Base、get_db
├── models/                # Conversation、ConversationMessage（MessageRole 等）
├── schemas/               # ChatRequest、RoutingMode 等
├── types.py               # MessageMode 等与请求/落库对齐的类型
├── llm/                   # Ollama 流式（/api/chat）、messages 拼装
├── routers/
│   └── chat/              # POST /chat/stream（StreamingResponse + SSE）
├── services/
│   └── chat_stream.py     # 路由解析、会话与消息落库、流式生成器
└── utils/
    └── sse_events.py      # build_*_event、sse_line
```

**Alembic**：仓库根 `alembic/`；表结构仍与历史迁移一致；迁移命令见下文「环境与启动」。

---

## 3. 功能模块与实现程度

> **约定**：**仅记录当前 `src/` 中已存在或已部分落地的能力**；历史全量能力见 **`src_backup/`** 与 **`docs/changelog.md`**。实现程度：**已完成** / **进行中** / **未挂载**。流式聊天字段级约定见 **`docs/chat-stream-api.md`**。

| 模块 | 主要路径 | 实现程度 | 说明 |
|------|-----------|-----------|------|
| 应用入口 | `src/api.py` | 已完成 | 仅 **`GET /health`** + **`POST /chat/stream`**（**`SessionLocal()`** 须在生成器内创建并在 **`finally`** 中 **`db.close()`**） |
| 健康检查 | `GET /health` | 已完成 | 返回 **`api_response.success`** |
| 流式聊天 | `routers/chat/router.py`、`services/chat_stream.py` | 已完成 | **`routing`**：`auto`（当前恒走 **`chat`**）\|`chat`\|`plan`\|`mcp`；**`plan`/`mcp`** 占位返回 **`error` + `done(conversation_id=null)`** |
| 会话与消息落库 | `models/conversation.py` 等 | 已完成 | **`chat`**：写 user → 流式 assistant → **`turn_id`** 配对；历史 **最近 40 条**（**`id desc` + `reversed`**） |
| Ollama 流式 | `llm/streaming.py`、`llm/messages.py` | 已完成 | **`/api/chat`** **`stream: true`**；消息角色由 **`MessageRole.value`** 映射 |
| SSE | `utils/sse_events.py` | 已完成 | **`delta` / `error` / `done`** |
| 非流式 `POST /chat`、Planner、MCP HTTP、`/tasks`、`/agent`、`/events`、`/conversations`… | — | **未挂载** | 在 **`src_backup`** 与重构计划中；恢复或重接时更新本表 |
| 会话记忆精炼 | — | **未实现** | **`memory_summary`** 等未在新链路中更新；多轮仅靠最近 N 条消息 |
| 工程 | `Dockerfile`、`docker compose`、`alembic/`、`tests/` | 部分 | 数据库迁移仍可用；**pytest 需随新入口补测或迁移** |

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
- **历史分页 API**（**`data.records`** 等）：当前精简 **`src/` 未挂载**；恢复时以 **`src_backup`** 与测试为准。

---

## 6. 前端

- **`frontend/readme.md`**、**`frontend/.cursor/rules/`**。

---

## 7. 下一次学习的起点

1. **聊天记录精炼（优先，待实现）**  
   - **触发**：每次收到用户新消息时做一次精炼，并**持久化**（可沿用表字段 **`conversation.memory_summary`**、**`memory_updated_at`**，或在 **`conversation_messages.meta`** 中存「该条给模型的精炼版」等，实现前在代码里定稿）。  
   - **精炼输入**：**上一轮已保存的精炼结果** + **本次用户发送的原文**（及实现时认为需要的上下文，如上一轮助手摘要等）。  
   - **展示与模型分离**：用户拉取**历史记录**时，**仍返回每条消息的完整原文**（例如用户第一次发 **`xxxxxxxxxx`**，列表里看到的仍是 **`xxxxxxxxxx`**）；组装**发给大模型的上下文**时，对已进入精炼范围的历史，使用**精炼后的文本**（例如下一轮模型侧「历史用户意图」为 **`xxx`**，而不是把 **`xxxxxxxxxx`** 再原样塞进 **`messages`**）。  
   - **文档**：实现后同步 **`docs/chat-stream-api.md`**（精炼时机、落库字段、与 **`POST /chat/stream`** 的关系）与本节勾选说明。  

2. **后端（当前精简栈）**：为 **`iter_ollama_chat_chunks`** 等补 **`pytest`**（mock 流）；按需挂载 **`GET /conversations/{id}/messages`** 或 **`POST /chat` 非流式**；**`plan`/`mcp`** 接入真实 planner/MCP 时更新 **`docs/chat-stream-api.md`**。  
3. **与旧版对齐**：从 **`src_backup`** 迁回路由时对照 **`docs/backend-refactor-plan.md`**，并同步本 **`readme.md` §3** 与 **`docs/changelog.md`**。  
4. **前端**：**SSE** 解析 **`done`** 中的 **`conversation_id` / `turn_id`**；错误态与 **`routing`** 占位文案联调；历史列表与「模型侧上下文」若分开展示，与第 1 条约定对齐。

---

## 8. 提交前约定

1. 更新 **`readme.md`**（与本仓库代码状态一致，尤其 **§3 功能模块与实现程度**）及 **`docs/changelog.md`**（本条变更摘要）。  
2. 若 **产品目标** 有变，更新 **`docs/project-goals.md`**。  
3. 若 **文档体系或协作规则** 有变，更新 **`docs/documentation-index.md`** 与 **`docs/collaboration-and-coding-rules.md`**，并检查 **`.cursor/rules/user-profile.mdc`** 是否需要同步。  
4. `git add` / `commit` / `push`。

---

## 9. 学习日志（可选）

长叙事建议写个人笔记或独立文件，避免本文件膨胀；索引见 **`docs/documentation-index.md`**。
