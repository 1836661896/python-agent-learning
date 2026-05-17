# Python Agent 学习项目 — 后端仓库说明

> **换设备 / 新对话**：根目录本文件 + **`docs/documentation-index.md`**（各文档职责）+ **`.cursor/rules/python-study-plan.mdc`** + **`python-learning-checklist.mdc`** + **`user-profile.mdc`**。  
> **详细变更历史**：**`docs/changelog.md`**。  
> **流式聊天接口约定**：**`docs/chat-stream-api.md`**（`POST /chat/stream`、SSE、`routing`、与旧版差异）。  
> **LLM 多提供商与 `.env`**：**`docs/llm-providers.md`**（`LLM_PROVIDER`、`providers/`、`complete_chat` / `iter_chat_chunks`、自测）。  
> **Agent Preset（身份提示词）**：**`docs/agent-presets.md`**（**`preset`**、**`src/prompts/presets/`**、与 MCP 分工）。  
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
├── env.py                 # 应用侧唯一 load_dotenv（backend 根 .env）；api 启动时 import
├── api.py                 # FastAPI 入口：首行 import src.env；CORS、/health、挂载路由
├── api_response.py        # 统一 JSON：{ code, data, msg }
├── db/                    # DATABASE_URL、SessionLocal、Base、get_db（不单独 load_dotenv）
├── models/                # Conversation、ConversationMessage（MessageRole 等）
├── schemas/               # ChatRequest、RoutingMode、**ConversationListQuery** 等
├── types.py               # MessageMode 等与请求/落库对齐的类型
├── providers/             # LLM 厂商适配：ollama.py、zhipu.py；注册表 get_provider
├── llm/                   # config（LLM_PROVIDER、MCP_REPLY_VIA_LLM）、complete_chat、iter_chat_chunks、messages、mcp_config
├── routers/
│   ├── chat/              # POST /chat/stream（StreamingResponse + SSE）
│   └── conversations.py   # 会话 list/delete/create/messages（见 docs/conversations-api.md）
├── prompts/               # preset 规则正文：presets/schedule.md 等（见 prompts/README.md）
├── services/
│   ├── agent_presets.py   # preset 注册与 build_preset_system_content
│   ├── chat_context.py    # 拼装发给模型的 messages（最近 N 条 + 摘要 + extra_system）
│   ├── chat_stream.py     # 路由、落库、**chat** 流式 / **mcp** 调工具、精炼、preset 注入
│   ├── route_auto.py      # **routing=auto**：list_tools → 行程关键词→chat+preset → 规则/LLM 选 mcp
│   ├── mcp_client.py      # MCP list_tools / call_tool
│   └── conversation_refine.py  # memory 精炼 → complete_chat
└── utils/
    ├── json_coerce.py     # 模型 JSON 截取（route/refine）
    └── sse_events.py      # SSE 事件拼装
```

**Alembic**：仓库根 `alembic/`；表结构仍与历史迁移一致；迁移命令见下文「环境与启动」。

---

## 3. 功能模块与实现程度

> **约定**：**仅记录当前 `src/` 中已存在或已部分落地的能力**；实现程度：**已完成** / **进行中** / **未挂载**。流式聊天字段级约定见 **`docs/chat-stream-api.md`**；变更流水见 **`docs/changelog.md`**。

| 模块 | 主要路径 | 实现程度 | 说明 |
|------|-----------|-----------|------|
| 应用入口 | `src/api.py` | 已完成 | **`GET /health`**、**`POST /chat/stream`**、**`routers/conversations`**（**`SessionLocal()`** 在流式路由的生成器内创建并在 **`finally`** 中 **`db.close()`**） |
| 健康检查 | `GET /health` | 已完成 | 返回 **`api_response.success`** |
| 流式聊天 **`chat`** | `chat_stream.py`、`chat_context.py`、`llm/streaming.py` | 已完成 | **`routing=chat`** 或 **`auto→chat`**：写 user → 精炼 → **`iter_chat_chunks`** 流式 assistant（由 **`LLM_PROVIDER`** 选智谱/Ollama）；**`meta`** 含 **`routing`**、**`effective_route`**；可选 **`preset`** 注入额外 **system**（见 **`docs/agent-presets.md`**） |
| **Agent preset** | `prompts/presets/`、`agent_presets.py`、`schemas/chat.py` | **已完成** | **`preset=schedule`** 等；请求体或会话 **`extra_json.preset`**；**`auto`** 行程关键词可自动设 **`preset=schedule`**；**不写死 MCP 工具名** |
| **LLM 多提供商** | `env.py`、`providers/*`、`llm/completion.py`、`llm/streaming.py` | **已完成** | **`LLM_PROVIDER`**（`zhipu`/`ollama`）+ 可选 **`LLM_FALLBACK_PROVIDER`**；业务只调 **`complete_chat` / `iter_chat_chunks`**；详见 **`docs/llm-providers.md`** |
| **`routing=auto`** | `route_auto.py`、`utils/json_coerce.py` | **已完成** | **`list_tools`** → 行程关键词 → **`chat`+`preset=schedule`** → 规则兜底（点名工具且无必填参数 → **`mcp`**）→ **`complete_chat`** 判别 JSON；**不在代码里绑定导出/联网工具名**。详见 **`docs/chat-stream-api.md` §5** |
| 流式聊天 **`mcp`** | `chat_stream.py`、`mcp_client.py` | **已完成** | SSE：**`tool_call`** → **`tool_result`**（**`mcp_raw`**）→ **`delta`**（润色或原文）；失败时 **`tool_result.is_error`** + **`error`**。**`MCP_REPLY_VIA_LLM`** 控制润色；assistant **`meta`** 可含 **`mcp_raw`** |
| MCP 客户端 | `llm/mcp_config.py`、`services/mcp_client.py` | 已完成 | Streamable HTTP；需本机 **`mcp-server`** HTTP 与 **`.env`** 中 **`MCP_*`** 一致 |
| 会话与消息落库 | `models/conversation.py` 等 | 已完成 | **`chat`** / **`mcp`** 均写 user + assistant、**`turn_id`** 配对；**`mcp`** 会话 **`kind=mcp`** |
| LLM 流式 / 非流式实现 | `providers/ollama.py`、`providers/zhipu.py` | 已完成 | Ollama：**`/api/chat`**；智谱：**`/chat/completions`**（OpenAI 兼容）；由 **`iter_chat_chunks` / `complete_chat`** 分发 |
| SSE | `utils/sse_events.py`、`chat_stream.py` | 已完成 | **`delta` / `error` / `done`**；**`mcp`** 另有 **`tool_call`**、**`tool_result`**（见 **`docs/chat-stream-api.md` §3**） |
| 会话 HTTP | `routers/conversations.py` | **已完成** | **`GET /list`**、**`GET /{id}/messages`**、**`POST /delete`**（**`ids`**；全未命中 **`fail`**；成功 **`data` 可为 null**）、**`POST /create`**（可选 **`kind`**，默认 **`chat`**；**`data.id`**）。约定见 **`docs/conversations-api.md`** |
| 非流式 `POST /chat`、Planner、`/tasks`、`/agent`、`/events` 等 | — | **未挂载** | 按 **`docs/backend-refactor-plan.md`** 在现行 **`src/`** 上扩展；落地后更新本表 |
| 会话记忆精炼 | `conversation_refine.py`、`chat_stream.py`、`llm/messages.py` | **已完成** | 每轮 user 后精炼落库；**`conversation_rows_to_messages`** 在非空摘要时前置 **`system`**；**`refine`** 对模型返回做 JSON 围栏/前缀截取（见 **`docs/changelog.md` 2026-05-12**）；API 历史仍为消息表**原文** |
| **`plan` 路由** | `chat_stream.py` | **未实现** | **`routing=plan`** 仍为占位 **`error`** |
| 工程 | `Dockerfile`、`docker compose`、`alembic/`、`tests/` | 部分 | **`pytest tests`**（含 **`test_agent_presets`**、**`test_route_auto`**、**`test_chat_stream`** preset/auto、**`test_conversations_api`** 等；**`requires_postgres`**） |

### 3.1 合规（与当前代码一致的一行）

不以「外网搬运视频到 B 站/抖音」等为学习目标；自动化与采集类能力需合规、白名单与二次确认（细则随功能扩展，见 **`docs/project-goals.md`**）。

---

## 4. 环境与启动

- **Python**：虚拟环境 `.venv`；依赖 **`requirements.txt`**。  
- **激活**：Windows：`.venv\Scripts\activate`；Unix：`source .venv/bin/activate`。  
- **环境变量**：复制 **`.env.example`** → **`.env`**。应用启动时由 **`src/env.py`** 加载（**`api.py`** 首行 **`import src.env`**）；**`alembic`** 独立 **`load_dotenv`**。零散脚本须先 **`import src.env`**。  
- **LLM**：**`LLM_PROVIDER`**（`zhipu` / `ollama`）、**`ZHIPU_*`** 或 **`OLLAMA_*`**、可选 **`LLM_FALLBACK_PROVIDER`**；架构与自测见 **`docs/llm-providers.md`**。  
- **本地 API**：`uvicorn src.api:app --reload`（默认 `http://127.0.0.1:8000`）。  
- **数据库**：`.env` 中 `DATABASE_URL`；迁移 **`alembic upgrade head`**。  
- **Ollama（备用或 `LLM_PROVIDER=ollama`）**：**`OLLAMA_*`**；`httpx` 使用 **`trust_env=False`** 避免代理误伤 `127.0.0.1`。  
- **MCP（调 sibling 服务）**：**`MCP_SERVER_URL`**、**`MCP_HTTP_PATH`**、**`MCP_TIMEOUT_SECONDS`**；**`MCP_REPLY_VIA_LLM`**（`true`/`false`，默认 `false`）控制工具返回是否再经 LLM 润色。需先启动 **`myproject/mcp-server`** HTTP 模式。自测 **`list_tools`**：`python -c "import src.env, anyio; from src.services.mcp_client import mcp_list_tools_async; print(anyio.run(mcp_list_tools_async))"`。  
- **Docker**：`docker compose up -d api`；容器内迁移 `docker compose run --rm api alembic upgrade head`；容器访问宿主机 Ollama 可用 `OLLAMA_BASE_URL=http://host.docker.internal:11434`（Docker Desktop）。

---

## 5. API 约定备忘

- **统一 JSON 响应**（**`/health` 等非 SSE**）：`{ "code", "data", "msg" }`；校验错误经异常处理器返回 **`code != 0`** 风格。  
- **`POST /chat/stream`**：**`text/event-stream`**；**`data:`** 后为 JSON，含 **`type`**：**`delta`**、**`error`**、**`done`**；**`mcp`** 另有 **`tool_call`**、**`tool_result`**。详见 **`docs/chat-stream-api.md`**。  
- **会话 HTTP**：**`GET /conversation/list`**、**`GET /conversation/{conversation_id}/messages`**、**`POST /conversation/delete`**、**`POST /conversation/create`**（约定见 **`docs/conversations-api.md`**）。

---

## 6. 前端

- **`frontend/readme.md`**、**`frontend/.cursor/rules/`**。

---

## 7. 下一次学习的起点

> **本仓库（backend）本阶段告一段落**：行程规则已迁至 **preset**；**`route_auto`** 仅动态 **tools/list + LLM**，无写死导出/guide 工具。下一主战场在 **`myproject/mcp-server`**。

1. **mcp-server（下一优先）**  
   - 实现 **`export_schedule_document`**（或等价导出工具）；**下线** **`get_schedule_planning_guide`**（提示词已由 backend **`preset=schedule`** 承担）。  
   - 工具 **description** 写清用途，便于 **`routing=auto`** 的 LLM 选型。  

2. **前端（与 mcp-server 并行时可做）**  
   - **行程规划师**入口：发 **`routing: "chat"`** + **`preset: "schedule"`**（或依赖 **`auto`** 关键词）。  
   - 解析 SSE **`tool_call` / `tool_result`**；可选 **`MCP_ALLOWED_TOOLS`** 白名单（backend 已具备配置位时可接）。  

3. **backend 暂缓项（需要时再开）**  
   - **`POST /conversation/create`** 支持 **`extra_json.preset`**；**`routing=plan`**；**`mcp` 分支精炼**；非流式 **`POST /chat`**。  
   - **WebSocket**：当前 SSE 足够；见 **`docs/chat-stream-api.md`**。  

4. **自测**  
   - **`python -m pytest tests/ -q`**；行程：**`docs/agent-presets.md`**、**`docs/chat-stream-api.md` §5**。

---

## 8. 提交前约定

1. 更新 **`readme.md`**（与本仓库代码状态一致，尤其 **§3 功能模块与实现程度**）及 **`docs/changelog.md`**（本条变更摘要）。  
2. 若 **产品目标** 有变，更新 **`docs/project-goals.md`**。  
3. 若 **文档体系或协作规则** 有变，更新 **`docs/documentation-index.md`** 与 **`docs/collaboration-and-coding-rules.md`**，并检查 **`.cursor/rules/user-profile.mdc`** 是否需要同步。  
4. `git add` / `commit` / `push`。

---

## 9. 学习日志（可选）

长叙事建议写个人笔记或独立文件，避免本文件膨胀；索引见 **`docs/documentation-index.md`**。
