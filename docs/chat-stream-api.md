# 流式聊天 API 说明（`POST /chat/stream`）

> **适用范围**：当前仓库 **`src/`** 中的 **`POST /chat/stream`**；与根目录 **`readme.md`** 一致处为准。  
> **LLM 提供商**（智谱/Ollama、**.env`**、自测）：**`docs/llm-providers.md`**。  
> **Agent Preset**：**`docs/agent-presets.md`**（身份规则与 MCP 分工）。  
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
| **`preset`** | `string \| null` | 否 | 对话身份 id（如 **`schedule`**）；拼入 **system**（见 **`docs/agent-presets.md`**）。请求体优先于会话 **`extra_json.preset`** |

### `routing` 取值（`RoutingMode`）

| 值 | 行为（当前实现） |
|----|------------------|
| **`auto`** | 见下文 **§5**：**`decide_route_auto`**（**`list_tools`** + 非流式 LLM JSON）→ **`chat`** 或 **`mcp`**；失败/解析失败回退 **`chat`** |
| **`chat`** | 走 **`iter_chat_chunks`** 流式对话（由 **`LLM_PROVIDER`** 选厂商），**落库** `conversation`（新建时 **`kind=chat`**）与 **`conversation_messages`** |
| **`plan`** | 占位：返回 **`error`**「计划链路尚未接入」，**不落库**；**`done`** 中 **`conversation_id` 为 `null`** |
| **`mcp`** | 见下文 **§6**：**`mcp_call_tool_async`** → 可选 LLM 润色（**`MCP_REPLY_VIA_LLM`**）→ SSE **`delta`** → assistant 落库 → **`done`** |

---

## 3. SSE 事件类型

每条 **`data:`** 后为 JSON 对象，至少包含 **`type`**。

| `type` | 字段 | 说明 |
|--------|------|------|
| **`delta`** | **`text`** | 面向用户的一小段增量文本（**`chat`** 模型输出；**`mcp`** 为润色后中文或工具原文） |
| **`tool_call`** | **`tool`**, **`arguments`** | 即将调用 MCP 工具（仅 **`mcp`** / **`auto→mcp`**） |
| **`tool_result`** | **`tool`**, **`text`**, 可选 **`is_error`** | 工具返回原文或错误说明；**`is_error: true`** 表示调用失败 |
| **`error`** | **`msg`** | 人类可读错误说明（会话不存在、模型失败、占位未接入等） |
| **`done`** | **`conversation_id`**（`int` 或 `null`）、**`turn_id`**（`string`） | 标志本轮流结束；**`turn_id`** 用于将本轮 user 与 assistant 消息配对 |

**顺序约定（建议客户端依赖）**：

- **`chat` 成功**（含 **`auto→chat`**）：若干 **`delta`** → **`done`**。  
- **`mcp` 成功**（含 **`auto→mcp`**）：**`tool_call`** → **`tool_result`** → 一条或多条 **`delta`** → **`done`**。  
- **`mcp` 调工具失败**（已发出 **`tool_call`**）：**`tool_result`**（**`is_error: true`**）→ **`error`** → **`done`**。  
- **其它失败**（未调工具，如缺 **`mcp_tool`**、会话不存在）：**`error`** → **`done`**（**`conversation_id` 可能为 `null`**）。  
- **`plan`**：仍为占位 **`error`** → **`done(null)`**。

---

## 4. `chat` 链路：落库与多轮上下文

1. **会话**：无 **`conversation_id`** 则 **`INSERT conversation`**（**`kind=chat`** 等），**`flush`** 得到 **`conv_id`**；有 id 则 **`SELECT`**，不存在则 **`error` + `done(null)`** 并结束。  
2. **用户消息**：**`INSERT conversation_messages`**（**`role=user`**，**`turn_id`** 为本轮 UUID hex 截断至 ≤50），**`meta`** 中含 **`routing`**、**`effective_route`**（**`auto`** 时与最终分支一致），**`flush`**。  
3. **会话摘要精炼（非流式）**：**`refine_memory_summary`** → **`complete_chat`**；成功则写回 **`memory_summary`/`memory_updated_at`** 并 **`flush`**；异常仅 **`logger.exception`**，不中断后续流式。  
4. **历史窗口**：按 **`conversation_id == conv_id`**、**`order_by(id.desc()).limit(40)`**，再 **`reversed`** 得到时间正序。  
5. **拼装 `messages`**： **`build_chat_model_messages(db, conv_id, memory_summary, extra_system=...)`**（内部 **`conversation_rows_to_messages`**）—— 若摘要非空则首部 **`system`**（记忆摘要）；**`preset`** 时再追加一条 **`system`**（身份规则）；否则仅最近角色对话（**含本轮 user**）。  
6. **模型**：**`iter_chat_chunks(messages)`**（**`src/llm/streaming.py`** → **`get_provider(LLM_PROVIDER).iter_chunks`**），逐块 **`yield` `delta`**。  
7. **助手消息**：流结束后拼接全文 **`INSERT`** **`role=assistant`**，同一 **`turn_id`**，**`commit`**。  
8. **失败**：**`rollback`**（含本轮 user 与新建会话，若尚未 **commit**），**`yield` `error`**；**`finally`** 中若 **`conv_id` 有效则 `yield` `done`**。

**环境变量**：**`LLM_PROVIDER`**、**`ZHIPU_*`** / **`OLLAMA_*`**、可选 **`LLM_FALLBACK_PROVIDER`**；详见 **`docs/llm-providers.md`**。各 Provider 的 **`httpx`** 使用 **`trust_env=False`**。

---

## 5. `auto` 链路：`route_auto.py`

> **入口**：**`chat_stream.stream_chat_turn`** 在 **`body.routing == "auto"`** 时调用 **`decide_route_auto(body.message)`**，得到 **`AutoRouteResult`**（**`route`**, **`mcp_tool`**, **`mcp_arguments`**, 可选 **`preset`**），再进入 §4 或 §6。

1. **`mcp_list_tools_async`**：拉远端工具列表；失败 → 回退 **`route=chat`**（无 **`preset`**）。  
2. **行程关键词**（**`_try_schedule_chat_route`**）：如「规划行程」「明天去哪」等 → **`route=chat`**、**`preset=schedule`**，**不**调路由 LLM；**`chat_stream`** 将 **`preset`** 写入会话 **`extra_json`**。  
3. **规则兜底**（**`_try_obvious_mcp_route`**）：用户话匹配「调用/使用/执行/call + 工具名」，且该工具 **无** `inputSchema.required` → 直接 **`route=mcp`**、**`mcp_arguments={}`**，**不**调路由 LLM。  
4. **Prompt + `complete_chat`**：工具列表含 **description** 与参数摘要（**`_tool_schema_hint`**）；只输出 JSON（**`route`** / **`mcp_tool`** / **`mcp_arguments`**）。**backend 不在此写死具体工具名**。  
5. **解析**：**`utils/json_coerce.extract_first_json_object`** → **`json.loads`**；失败回退 **`chat`**。  
6. **校验**：**`mcp_tool`** 须在 **`tools/list`** 的 **`name`** 集合内；否则回退 **`chat`**。  
7. **分支**：**`route=chat`** → §4（若 **`preset`** 有值则注入 system）；**`route=mcp`** → §6。

**代价**：**`auto`** 至少 **0～1 次** 路由 LLM（规则命中则 0 次）+ 若 **`chat`** 还有精炼 + 流式；若 **`mcp`** 有工具调用，且 **`MCP_REPLY_VIA_LLM=true`** 时再多一次流式 LLM。

---

## 6. `mcp` 链路：工具调用

> **前提**：本机 **`mcp-server`** 已以 Streamable HTTP 启动；**`.env`** 中 **`MCP_SERVER_URL`**、**`MCP_HTTP_PATH`** 与之一致（见 **`readme.md` §4**）。

1. **工具名**：**`routing=mcp`** 时请求体必填 **`mcp_tool`**；**`routing=auto`** 且判别为 **`mcp`** 时用 **`auto_decision`** 中的 **`mcp_tool`** / **`mcp_arguments`**。未解析到工具名 → **`error`**「routing=mcp 时请传 mcp_tool」→ **`done(null)`**。  
2. **会话**：无 **`conversation_id`** 则新建 **`conversation`**（**`kind=mcp`**）；有 id 则校验存在。  
3. **用户消息**：**`meta`** 含 **`routing`**、**`effective_route`**、**`mcp_tool`**、**`mcp_arguments`**。  
4. **SSE `tool_call`**：**`yield`** **`tool`** + **`arguments`**。  
5. **调工具**：**`anyio.run(mcp_call_tool_async, ...)`** → **`mcp_raw`**；**`yield` `tool_result`**（**`text=mcp_raw`**）。  
6. **面向用户的 `delta`**：  
   - **`MCP_REPLY_VIA_LLM=false`**（默认）：**`yield` 一条 `delta`**（**`mcp_raw`**）；assistant **`meta`** 含 **`mcp_tool`**。  
   - **`MCP_REPLY_VIA_LLM=true`**：**`iter_chat_chunks`** 流式 **`delta`**；assistant **`content`** 为润色全文，**`meta`** 含 **`mcp_tool`**、**`mcp_raw`**。  
7. **`commit`**；调工具异常：**`tool_result`**（**`is_error: true`**）→ **`error`** → **`finally`** 中 **`done`**。

**说明**：**不**调用 **`refine_memory_summary`**。环境变量见 **`readme.md` §4**、**`llm/config.py`**。

---

## 7. 与规划中的差异（当前未实现或未接满）

| 能力 | 状态 |
|------|------|
| **`routing=mcp` 显式 `mcp_tool`** | **已实现**（§6） |
| **`routing=auto` 自动选 MCP / 工具** | **已实现**（§5） |
| **MCP 结果经 LLM 润色后再 `delta`** | **已实现**（**`MCP_REPLY_VIA_LLM`**，§6） |
| **SSE `tool_call` / `tool_result`** | **已实现**（§3、§6） |
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

curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"我想规划明天行程","routing":"auto"}'

curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"就明天","routing":"chat","preset":"schedule","conversation_id":1}'
```

**PowerShell**（`curl` 常为别名，建议用下面或 **`curl.exe`**）：

```powershell
$body = '{"message":"帮我 ping 一下","routing":"auto"}'
Invoke-WebRequest -Uri "http://127.0.0.1:8000/chat/stream" -Method POST -ContentType "application/json; charset=utf-8" -Body $body
```

成功 **`mcp`**（显式或 **`auto→mcp`**）：**`MCP_REPLY_VIA_LLM=false`** 时 **`delta.text`** 多为工具原文（如 **`pong`**）；**`true`** 时为自然语言流式多段 **`delta`**，assistant **`meta.mcp_raw`** 保留原文。**`auto→chat`** 则为多段 **`delta`** + **`done`**。

---

*文档版本：与 2026-05-17 起「**`preset`**、**`auto` 行程→`chat`+`preset=schedule`**、**`route_auto` 不写死 MCP 工具名**」的 `src` 对齐；下一优先见 **`readme.md` §7**（**mcp-server** 导出工具、前端 preset/工具事件）。*
