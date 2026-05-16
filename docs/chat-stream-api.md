# 流式聊天 API 说明（`POST /chat/stream`）

> **适用范围**：当前仓库 **`src/`** 中的 **`POST /chat/stream`**；与根目录 **`readme.md`** 一致处为准。  
> **更新时机**：变更请求体、SSE 事件形态、路由策略或历史窗口时同步修改本文件与 **`docs/changelog.md`**。

---

## 1. 端点与协议

| 项 | 值 |
|----|-----|
| **方法 / 路径** | **`POST /chat/stream`** |
| **请求头** | **`Content-Type: application/json`** |
| **响应** | **`text/event-stream`（SSE）**；每条事件为 **`data: {JSON}\n\n`** |

---

## 2. 请求体：`ChatRequest`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| **`message`** | `string` | 是 | 用户输入；经校验后非空（首尾空白已 strip） |
| **`conversation_id`** | `integer \| null` | 否 | 不传或 `null`：服务端**新建会话**并在 **`done`** 中返回新 id；传入时须为已存在的 **`conversation.id`** |
| **`routing`** | 见下表 | 否 | 默认 **`"auto"`** |
| **`mcp_tool`** | `string \| null` | 否 | **`routing=mcp` 时必填**（工具名，须为远端 **`tools/list`** 中的 **`name`**） |
| **`mcp_arguments`** | `object` | 否 | 传给 **`tools/call`** 的参数对象，默认 **`{}`** |

### `routing` 取值（`RoutingMode`）

| 值 | 行为（当前实现） |
|----|------------------|
| **`auto`** | 见下文 **§5**：**`decide_route_auto`**（**`list_tools`** + 非流式 LLM JSON）→ **`chat`** 或 **`mcp`**；失败/解析失败回退 **`chat`** |
| **`chat`** | 走 Ollama 流式对话，**落库** `conversation`（新建时 **`kind=chat`**）与 **`conversation_messages`**（user + assistant） |
| **`plan`** | 占位：返回 **`error`**「计划链路尚未接入」，**不落库**；**`done`** 中 **`conversation_id` 为 `null`** |
| **`mcp`** | 见下文 **§6**：显式 **`mcp_tool`**，或由 **`auto`** 判别后注入工具名；**`mcp_call_tool_async`** → SSE **`delta`**（工具结果**原文**）→ assistant 落库 → **`done`**（**尚未** LLM 润色） |

---

## 3. SSE 事件类型

每条 **`data:`** 后为 JSON 对象，至少包含 **`type`**。

| `type` | 字段 | 说明 |
|--------|------|------|
| **`delta`** | **`text`** | 模型输出的一小段增量文本 |
| **`error`** | **`msg`** | 人类可读错误说明（会话不存在、模型失败、占位未接入等） |
| **`done`** | **`conversation_id`**（`int` 或 `null`）、**`turn_id`**（`string`） | 标志本轮流结束；**`turn_id`** 用于将本轮 user 与 assistant 消息配对 |

**规划中（未实现）**：**`tool_call`**（**`tool`**, **`arguments`**）、**`tool_result`**（**`tool`**, **`text`**, 可选 **`is_error`**）—— 见 **`readme.md` §7**。

**顺序约定（建议客户端依赖）**：

- **`chat` 成功**（含 **`auto→chat`**）：若干 **`delta`** → **`done`**。  
- **`mcp` 成功**（含 **`auto→mcp`**）：一条（或多条）**`delta`**（工具结果**原文**）→ **`done`**。  
- **失败**：**`error`** → **`done`**（未建会话或未传 **`mcp_tool`** 时 **`conversation_id` 可能为 `null`**）。  
- **`plan`**：仍为占位 **`error`** → **`done(null)`**。

---

## 4. `chat` 链路：落库与多轮上下文

1. **会话**：无 **`conversation_id`** 则 **`INSERT conversation`**（**`kind=chat`** 等），**`flush`** 得到 **`conv_id`**；有 id 则 **`SELECT`**，不存在则 **`error` + `done(null)`** 并结束。  
2. **用户消息**：**`INSERT conversation_messages`**（**`role=user`**，**`turn_id`** 为本轮 UUID hex 截断至 ≤50），**`meta`** 中含 **`routing`**、**`effective_route`**（**`auto`** 时与最终分支一致），**`flush`**。  
3. **会话摘要精炼（非流式）**：用当前 **`memory_summary`** 与本轮 **`message`** 调用 **`refine_memory_summary`** → **`complete_ollama_chat`**（**`stream: false`**）；成功则写回 **`memory_summary`/`memory_updated_at`** 并 **`flush`**；异常仅 **`logger.exception`**，不中断后续流式。  
4. **历史窗口**：按 **`conversation_id == conv_id`**、**`order_by(id.desc()).limit(40)`**，再 **`reversed`** 得到时间正序。  
5. **拼装 `messages`**： **`build_chat_model_messages(db, conv_id, memory_summary)`**（内部 **`conversation_rows_to_messages`**）—— 若摘要非空则首部 **`system`**，否则仅最近角色对话（**含本轮 user**）。  
6. **模型**：**`POST` Ollama `/api/chat`**，**`stream: true`**，逐块 **`yield` `delta`**。  
7. **助手消息**：流结束后拼接全文 **`INSERT`** **`role=assistant`**，同一 **`turn_id`**，**`commit`**。  
8. **失败**：**`rollback`**（含本轮 user 与新建会话，若尚未 **commit**），**`yield` `error`**；**`finally`** 中若 **`conv_id` 有效则 `yield` `done`**。

**环境变量**：**`OLLAMA_BASE_URL`**、**`OLLAMA_MODEL`**；**`httpx`** 使用 **`trust_env=False`** 以避免本机代理影响 **`127.0.0.1`**。

---

## 5. `auto` 链路：`route_auto.py`

> **入口**：**`chat_stream.stream_chat_turn`** 在 **`body.routing == "auto"`** 时调用 **`decide_route_auto(body.message)`**，得到 **`AutoRouteResult`**（**`route`**, **`mcp_tool`**, **`mcp_arguments`**），再进入 §4 或 §6。

1. **`mcp_list_tools_async`**：拉远端工具列表；失败 → 回退 **`route=chat`**。  
2. **Prompt + `complete_ollama_chat`**：要求只输出 JSON，**`route`** 为 **`chat`** 或 **`mcp`**（不允许 **`plan`**）；**`mcp`** 时含 **`mcp_tool`**、**`mcp_arguments`**。  
3. **解析**：**`_coerce_route_json_text`**（去围栏；**`find("{")` + `rfind("}")`** 截取对象）→ **`json.loads`**。  
4. **校验**：**`mcp_tool`** 须在 **`tools/list`** 的 **`name`** 集合内；否则回退 **`chat`**。  
5. **分支**：**`route=chat`** → §4；**`route=mcp`** → §6（工具名/参数来自判别结果，**无需**请求体 **`mcp_tool`**）。

**代价**：**`auto`** 每轮至少 **1 次** 非流式 LLM（路由）+ 若走 **`chat`** 还有精炼 + 流式；若走 **`mcp`** 还有工具调用（润色落地后会再多一次流式 LLM）。

---

## 6. `mcp` 链路：工具调用

> **前提**：本机 **`mcp-server`** 已以 Streamable HTTP 启动；**`.env`** 中 **`MCP_SERVER_URL`**、**`MCP_HTTP_PATH`** 与之一致（见 **`readme.md` §4**）。

1. **工具名**：**`routing=mcp`** 时请求体必填 **`mcp_tool`**；**`routing=auto`** 且判别为 **`mcp`** 时用 **`auto_decision`** 中的 **`mcp_tool`** / **`mcp_arguments`**。未解析到工具名 → **`error`**「routing=mcp 时请传 mcp_tool」→ **`done(null)`**。  
2. **会话**：无 **`conversation_id`** 则新建 **`conversation`**（**`kind=mcp`**）；有 id 则校验存在。  
3. **用户消息**：**`meta`** 含 **`routing`**、**`effective_route`**、**`mcp_tool`**、**`mcp_arguments`**。  
4. **调工具**：**`anyio.run(mcp_call_tool_async, tool_name, arguments)`**；**`format_call_tool_result`**。  
5. **响应**：**`yield` `delta`**（整段工具**原文**）；**`INSERT`** assistant；**`commit`**。  
6. **失败**：**`rollback`** → **`error`** → **`finally`** 中 **`done`**。

**说明**：当前 **不**调用 **`refine_memory_summary`**；**不**对工具结果做 LLM 润色（下一优先见 **`readme.md` §7**）。

---

## 7. 与规划中的差异（当前未实现或未接满）

| 能力 | 状态 |
|------|------|
| **`routing=mcp` 显式 `mcp_tool`** | **已实现**（§6） |
| **`routing=auto` 自动选 MCP / 工具** | **已实现**（§5） |
| **MCP 结果经 LLM 润色后再 `delta`** | **未实现** |
| **SSE `tool_call` / `tool_result`** | **未实现** |
| **`MCP_ALLOWED_TOOLS` 白名单** | **未实现** |
| **`routing=plan`** | **占位** |
| **WebSocket 替代 SSE** | **未做**；当前 SSE 足够；见 **`readme.md` §7** |
| **摘要进入模型 `messages`（`chat`）** | **已做**（**`chat_context`**） |
| **`POST /chat` 非流式** | **未实现** |
| **会话 HTTP** | **已挂载**（见 **`docs/conversations-api.md`**） |
| **`/tasks`、`/agent/*`、`/events` 等** | **未挂载**；见 **`docs/backend-refactor-plan.md`** |

---

## 8. 自测示例

**bash / Git Bash**（**`-N`** 不缓冲 SSE）：

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"你好","routing":"chat"}'

curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"测MCP","routing":"mcp","mcp_tool":"ping","mcp_arguments":{}}'

curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"帮我 ping 一下","routing":"auto"}'
```

**PowerShell**（`curl` 常为别名，建议用下面或 **`curl.exe`**）：

```powershell
$body = '{"message":"帮我 ping 一下","routing":"auto"}'
Invoke-WebRequest -Uri "http://127.0.0.1:8000/chat/stream" -Method POST -ContentType "application/json; charset=utf-8" -Body $body
```

成功 **`mcp`**（显式或 **`auto→mcp`**）响应 **`Content`** 中应含 **`"type": "delta"`**、**`"text": "pong"`**（以 **`ping` 工具为准）及 **`"type": "done"`**。**`auto→chat`** 则为多段 **`delta`** + **`done`**。

---

*文档版本：与 2026-05-16 起「**`routing=auto`**（**`route_auto.py`**）、**`routing=mcp` + `mcp_tool`**、**`chat_context`**」的 `src` 对齐；下一优先见 **`readme.md` §7**（**MCP 润色**、**`tool_*` SSE**、白名单；**WebSocket 视情况**）。*
