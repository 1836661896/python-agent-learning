# Python Agent 学习项目 — 后端仓库说明

> **换设备 / 新对话**：根目录本文件 + **`docs/documentation-index.md`**（各文档职责）+ **`.cursor/rules/python-study-plan.mdc`** + **`python-learning-checklist.mdc`** + **`user-profile.mdc`**。  
> **详细变更历史**：**`docs/changelog.md`**。  
> **流式聊天接口约定**：**`docs/chat-stream-api.md`**（`POST /chat/stream`、SSE、`routing`、与旧版差异）。  
> **会话 HTTP**：**`docs/conversations-api.md`**（**`GET /conversation/list`**、**`GET /conversation/{id}/messages`**、**`POST /conversation/delete`**、**`POST /conversation/create`**；分页、**`data`/`fail`**）。  
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
├── api.py                 # FastAPI 入口：CORS、校验/HTTP 异常、/health、挂载 chat + conversation
├── api_response.py        # 统一 JSON：{ code, data, msg }
├── db/                    # DATABASE_URL、SessionLocal、Base、get_db
├── models/                # Conversation、ConversationMessage（MessageRole 等）
├── schemas/               # ChatRequest、RoutingMode、**ConversationListQuery**、**ConversationBatchDeleteBody**、**ConversationCreateBody** 等
├── types.py               # MessageMode 等与请求/落库对齐的类型
├── llm/                   # config、Ollama 流式/非流式（/api/chat）、messages 拼装、mcp_config（MCP HTTP 端点）
├── routers/
│   ├── chat/              # POST /chat/stream（StreamingResponse + SSE）
│   └── conversations.py   # GET …/list、POST …/delete、POST …/create、GET …/{id}/messages（约定见 docs/conversations-api.md）
├── services/
│   ├── chat_context.py    # 拼装发给模型的 messages（最近 N 条 + 摘要；日后 RAG/向量检索入口）
│   ├── chat_stream.py     # 路由解析、会话与消息落库、**chat** 流式 / **mcp** 调工具、精炼落库
│   ├── route_auto.py      # **routing=auto**：list_tools → 非流式 LLM 判别 chat/mcp + 工具名/参数
│   ├── mcp_client.py      # Streamable HTTP：**list_tools** / **call_tool**、**format_call_tool_result**
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
| 应用入口 | `src/api.py` | 已完成 | **`GET /health`**、**`POST /chat/stream`**、**`routers/conversations`**（**`SessionLocal()`** 在流式路由的生成器内创建并在 **`finally`** 中 **`db.close()`**） |
| 健康检查 | `GET /health` | 已完成 | 返回 **`api_response.success`** |
| 流式聊天 **`chat`** | `chat_stream.py`、`chat_context.py` | 已完成 | **`routing=chat`**，或 **`auto` 判别为 chat**：写 user → 精炼 → Ollama 流式 assistant；**`meta`** 含 **`routing`**、**`effective_route`**；上下文 **`build_chat_model_messages`**（最近 **40** 条 + 摘要） |
| **`routing=auto`** | `route_auto.py`、`chat_stream.py` | **已完成** | **`mcp_list_tools_async`** → **`complete_ollama_chat`** 输出 JSON（**`route`** / **`mcp_tool`** / **`mcp_arguments`**）→ 白名单校验（须在 **`tools/list`** 内）；失败回退 **`chat`**；详见 **`docs/chat-stream-api.md` §5** |
| 流式聊天 **`mcp`** | `chat_stream.py`、`mcp_client.py` | **已完成** | **`routing=mcp`** 须请求体 **`mcp_tool`**；**`auto` 判别为 mcp** 时用 **`route_auto`** 结果。工具结果经 **`format_call_tool_result`** → 一条 SSE **`delta`**（**原文**，尚未 LLM 润色）→ assistant 落库 → **`done`**；**不**走 **`refine_memory_summary`** |
| MCP 客户端 | `llm/mcp_config.py`、`services/mcp_client.py` | 已完成 | Streamable HTTP；需本机 **`mcp-server`** HTTP 与 **`.env`** 中 **`MCP_*`** 一致 |
| 会话与消息落库 | `models/conversation.py` 等 | 已完成 | **`chat`** / **`mcp`** 均写 user + assistant、**`turn_id`** 配对；**`mcp`** 会话 **`kind=mcp`** |
| Ollama 流式 | `llm/streaming.py`、`llm/messages.py` | 已完成 | **`/api/chat`** **`stream: true`**；消息角色由 **`MessageRole.value`** 映射 |
| SSE | `utils/sse_events.py` | 已完成 | **`delta` / `error` / `done`** |
| 会话 HTTP | `routers/conversations.py` | **已完成** | **`GET /list`**、**`GET /{id}/messages`**、**`POST /delete`**（**`ids`**；全未命中 **`fail`**；成功 **`data` 可为 null**）、**`POST /create`**（可选 **`kind`**，默认 **`chat`**；**`data.id`**）。约定见 **`docs/conversations-api.md`** |
| 非流式 `POST /chat`、Planner、`/tasks`、`/agent`、`/events` 等 | — | **未挂载** | 按 **`docs/backend-refactor-plan.md`** 在现行 **`src/`** 上扩展；落地后更新本表 |
| 会话记忆精炼 | `conversation_refine.py`、`chat_stream.py`、`llm/messages.py` | **已完成** | 每轮 user 后精炼落库；**`conversation_rows_to_messages`** 在非空摘要时前置 **`system`**；**`refine`** 对模型返回做 JSON 围栏/前缀截取（见 **`docs/changelog.md` 2026-05-12**）；API 历史仍为消息表**原文** |
| **`plan` 路由** | `chat_stream.py` | **未实现** | **`routing=plan`** 仍为占位 **`error`** |
| 工程 | `Dockerfile`、`docker compose`、`alembic/`、`tests/` | 部分 | **`pytest tests`**（含 **`test_chat_stream`** MCP mock、**`test_mcp_client`**、**`test_chat_context`**、**`test_conversations_api`** 等；**`requires_postgres`**） |

### 3.1 合规（与当前代码一致的一行）

不以「外网搬运视频到 B 站/抖音」等为学习目标；自动化与采集类能力需合规、白名单与二次确认（细则随功能扩展，见 **`docs/project-goals.md`**）。

---

## 4. 环境与启动

- **Python**：虚拟环境 `.venv`；依赖 **`requirements.txt`**。  
- **激活**：Windows：`.venv\Scripts\activate`；Unix：`source .venv/bin/activate`。  
- **本地 API**：`uvicorn src.api:app --reload`（默认 `http://127.0.0.1:8000`）。  
- **数据库**：`.env` 中 `DATABASE_URL`；迁移 **`alembic upgrade head`**。列名 **`tool_succeeded`** 等与迁移 **`1078372ccdda`** 及 ORM 一致。  
- **Ollama**：`.env` 中 `OLLAMA_*`；若本机 `curl` 正常而接口 502，对 `httpx` 使用 **`trust_env=False`** 避免代理误伤 `127.0.0.1`。  
- **MCP（调 sibling 服务）**：`.env` 中 **`MCP_SERVER_URL`**（无尾斜杠）、**`MCP_HTTP_PATH`**（如 **`/mcp`**）、**`MCP_TIMEOUT_SECONDS`**；需先在本机启动 **`myproject/mcp-server`** 的 HTTP 模式（与路径一致）。自测可在 backend 根执行 **`python -c "import anyio; from src.services.mcp_client import mcp_list_tools_async; print(anyio.run(mcp_list_tools_async))"`**（依赖远端已启动）。  
- **Docker**：`docker compose up -d api`；容器内迁移 `docker compose run --rm api alembic upgrade head`；容器访问宿主机 Ollama 可用 `OLLAMA_BASE_URL=http://host.docker.internal:11434`（Docker Desktop）。

---

## 5. API 约定备忘

- **统一 JSON 响应**（**`/health` 等非 SSE**）：`{ "code", "data", "msg" }`；校验错误经异常处理器返回 **`code != 0`** 风格。  
- **`POST /chat/stream`**：**`text/event-stream`**；**`data:`** 后为 JSON，含 **`type`**：**`delta`**（**`text`**）、**`error`**（**`msg`**）、**`done`**（**`conversation_id`**、**`turn_id`**）。详见 **`docs/chat-stream-api.md`**。  
- **会话 HTTP**：**`GET /conversation/list`**、**`GET /conversation/{conversation_id}/messages`**、**`POST /conversation/delete`**、**`POST /conversation/create`**（约定见 **`docs/conversations-api.md`**）。

---

## 6. 前端

- **`frontend/readme.md`**、**`frontend/.cursor/rules/`**。

---

## 7. 下一次学习的起点

1. **MCP 返回值润色（当前最高优先）**  
   - **现状**：**`mcp`** / **`auto→mcp`** 的 SSE **`delta`** 为 **`format_call_tool_result` 原文**（如 `pong`），assistant 落库同为原文。  
   - **目标**：工具执行后，将结果 + 用户问题再交 **Ollama 流式** 生成自然语言 **`delta`**；**`meta`** 可保留 **`mcp_raw`** 备查。建议 **`.env`** 开关 **`MCP_REPLY_VIA_LLM`**。  
   - **涉及**：**`chat_stream.py`**（mcp 分支）或抽出 **`mcp_turn.py`**。  

2. **后端动作细分（SSE 协议扩展）**  
   - **目标**：在调工具前后增加 **`tool_call`** / **`tool_result`** 事件（**`utils/sse_events.py`**），与面向用户的 **`delta`** 分离；前端可折叠展示工具原始输出。  
   - **可选**：**`MCP_ALLOWED_TOOLS`** 环境变量白名单（**`mcp_config` + `route_auto` + mcp 分支** 双重校验）。  
   - **文档**：落地后更新 **`docs/chat-stream-api.md` §3**。  

3. **传输层：SSE 与 WebSocket（视情况）**  
   - **当前**：**`POST /chat/stream`** + **SSE** 已满足「单向流式推送 + 一轮一请求」；**`chat`** 多 **`delta`**、**`mcp`** 通常少量事件，**不必为润色单独上 WebSocket**。  
   - **考虑升级 WebSocket 的时机**：需要**服务端主动推送**（多轮 agent 步骤、长任务进度、取消/心跳）、**双向频繁信令**，或前端强依赖单连接多路复用时再评估。  
   - **若暂不上 WS**：继续 SSE；润色与 **`tool_*`** 仍用同一 **`text/event-stream`** 连接即可。  

4. **前端对接**  
   - 默认或可选 **`routing: "auto"`**；解析 **`delta` / `error` / `done`**（后续 **`tool_call` / `tool_result`**）。  
   - 会话 API 与 **`docs/conversations-api.md`** 对齐。  

5. **其它（排后）**  
   - **`routing=plan`** 真实实现（**`PlanOutline`**，见 **`schemas/planning.py`**）。  
   - **`routing=auto` 的 pytest** mock、**`mcp` 分支 `refine_memory_summary`**、**`POST /chat` 非流式**。  
   - 对照 **`docs/backend-refactor-plan.md`** 扩展时同步 **`changelog`**。

---

## 8. 提交前约定

1. 更新 **`readme.md`**（与本仓库代码状态一致，尤其 **§3 功能模块与实现程度**）及 **`docs/changelog.md`**（本条变更摘要）。  
2. 若 **产品目标** 有变，更新 **`docs/project-goals.md`**。  
3. 若 **文档体系或协作规则** 有变，更新 **`docs/documentation-index.md`** 与 **`docs/collaboration-and-coding-rules.md`**，并检查 **`.cursor/rules/user-profile.mdc`** 是否需要同步。  
4. `git add` / `commit` / `push`。

---

## 9. 学习日志（可选）

长叙事建议写个人笔记或独立文件，避免本文件膨胀；索引见 **`docs/documentation-index.md`**。
