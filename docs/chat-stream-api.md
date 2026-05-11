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

### `routing` 取值（`RoutingMode`）

| 值 | 行为（当前实现） |
|----|------------------|
| **`auto`** | 经 **`resolve_effective_route`** 解析；现阶段 **`decide_route_auto` 恒为 `chat`**，与强制 **`chat`** 等价 |
| **`chat`** | 走 Ollama 流式对话，**落库** `conversation`（新建时）与 **`conversation_messages`**（user + assistant） |
| **`plan`** | 占位：返回 **`error`**「计划链路尚未接入」，**不落库**；**`done`** 中 **`conversation_id` 为 `null`** |
| **`mcp`** | 占位：同上 |

---

## 3. SSE 事件类型

每条 **`data:`** 后为 JSON 对象，至少包含 **`type`**。

| `type` | 字段 | 说明 |
|--------|------|------|
| **`delta`** | **`text`** | 模型输出的一小段增量文本 |
| **`error`** | **`msg`** | 人类可读错误说明（会话不存在、模型失败、占位未接入等） |
| **`done`** | **`conversation_id`**（`int` 或 `null`）、**`turn_id`**（`string`） | 标志本轮流结束；**`turn_id`** 用于将本轮 user 与 assistant 消息配对 |

**顺序约定（建议客户端依赖）**：正常 **`chat`** 路径为若干 **`delta`** → **`done`**；出错时可能为 **`error`** → **`done`**；**`plan`/`mcp`** 为 **`error`** → **`done`**（**`conversation_id` 为 null**）。

---

## 4. `chat` 链路：落库与多轮上下文

1. **会话**：无 **`conversation_id`** 则 **`INSERT conversation`**（**`kind=chat`** 等），**`flush`** 得到 **`conv_id`**；有 id 则 **`SELECT`**，不存在则 **`error` + `done(null)`** 并结束。  
2. **用户消息**：**`INSERT conversation_messages`**（**`role=user`**，**`turn_id`** 为本轮 UUID hex 截断至 ≤50），**`meta`** 中含 **`routing`**，**`flush`**。  
3. **会话摘要精炼（非流式）**：用当前 **`memory_summary`** 与本轮 **`message`** 调用 **`refine_memory_summary`** → **`complete_ollama_chat`**（**`stream: false`**）；成功则写回 **`memory_summary`/`memory_updated_at`** 并 **`flush`**；异常仅 **`logger.exception`**，不中断后续流式。  
4. **历史窗口**：按 **`conversation_id == conv_id`**、**`order_by(id.desc()).limit(40)`**，再 **`reversed`** 得到时间正序。  
5. **拼装 `messages`**： **`conversation_rows_to_messages(rows, conv.memory_summary or "")`** —— 若 **`memory_summary.strip()`** 非空，则在列表**首部**插入一条 **`role=system`**（固定说明 + **`【会话摘要】`** + 正文）；其后为各条 **`user`/`assistant`** 原文（**含本轮 user**）。精炼失败导致摘要仍为空时**不插** **`system`**。  
6. **模型**：**`POST` Ollama `/api/chat`**，**`stream: true`**，逐块 **`yield` `delta`**。  
7. **助手消息**：流结束后拼接全文 **`INSERT`** **`role=assistant`**，同一 **`turn_id`**，**`commit`**。  
8. **失败**：**`rollback`**（含本轮 user 与新建会话，若尚未 **commit**），**`yield` `error`**；**`finally`** 中若 **`conv_id` 有效则 `yield` `done`**。

**环境变量**：**`OLLAMA_BASE_URL`**、**`OLLAMA_MODEL`**；**`httpx`** 使用 **`trust_env=False`** 以避免本机代理影响 **`127.0.0.1`**。

---

## 5. 与规划中的差异（当前未实现或未接满）

| 能力 | 状态 |
|------|------|
| **摘要进入模型 `messages`** | **已做**：非空 **`memory_summary`** 时首条 **`system`**；否则仅 **40 条角色对话**（见 §4 步骤 5） |
| **`POST /chat` 非流式** | **未实现** |
| **`GET /conversations` / `GET /conversations/{id}/messages`** | **未在 `api.py` 挂载**（表与 ORM 仍存在，可按需加路由） |
| **Planner / MCP / builtin**、`/tasks`、`/agent/*`、`/events` 等 | **未挂载**；扩展路径见 **`docs/backend-refactor-plan.md`** |

---

## 6. 自测示例（`curl`）

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}'

curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"第二句","conversation_id":106,"routing":"chat"}'

curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"x","routing":"plan"}'
```

**`-N`**：不缓冲输出，便于观察流式 **`data:`**。

---

*文档版本：与 2026-05-11 起「精炼落库、无 `src_backup`」的 `src` 对齐。*
