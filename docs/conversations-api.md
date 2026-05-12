# 会话列表与会话历史（HTTP）

> **何时更新**：修改 **`src/routers/conversations.py`**、**`src/schemas/conversations.py`** 或分页/筛选/排序约定时同步本文件。  
> **统一响应**：非 SSE 接口均为 **`{ "code", "data", "msg" }`**；成功 **`code === 0`**，业务或校验失败 **`code !== 0`**（与 **`src/api_response.py`** 一致）。

---

## 路径前缀说明

当前实现使用前缀 **`/conversation`**（单数）。重构文档 **`docs/backend-refactor-plan.md`** 中曾用复数 **`/conversations`** 表述能力名称；若日后改为复数路径，以 **`readme.md`** 与本文件为准并做前后端联调迁移。

---

## 1. `GET /conversation/list`

**作用**：分页返回会话表 **`conversation`** 中的记录（列表项含 **`memory_title`** 等，不含消息正文）。

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page` | 整数 | `1` | 页码，从 1 起 |
| `limit` | 整数 | `10` | 每页条数 |
| `kind` | 可选枚举 | 不传则不过滤 | **`chat` / `mcp` / `plan`**，与 **`ConversationKind`** 一致 |

### 成功时 `data` 形状（`ListResult`）

- **`records`**：`ConversationListItem` 数组（`id`、`kind`、`memory_title`、`created_at`、`memory_updated_at` 等，与 **`src/schemas/conversations.py`** 一致）。
- **`total`**：满足筛选条件的总条数。
- **`page` / `limit`**：与请求一致。

### 排序

按会话 **`created_at` 降序**（较新的会话排在前面）。

### 失败与 `data`

路由返回类型允许 **`data` 为 `null`**（如数据库异常时 **`fail(...)`** 未附带 `data`）。前端应 **`code !== 0` 时勿假定 `data` 必有 `records`**。

---

## 2. `GET /conversation/{conversation_id}/messages`

**作用**：分页返回指定会话在 **`conversation_messages`** 表中的消息（表内存储的**原文**，不含精炼摘要拼进列表的逻辑；摘要仅用于流式聊天时的模型上下文，见 **`docs/chat-stream-api.md`**）。

### 路径参数

- **`conversation_id`**：整数，目标会话主键。

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page` | 整数 | `1` | 页码 |
| `limit` | 整数 | `10` | 每页条数 |
| `role` | 可选枚举 | 不传则不过滤 | **`user` / `assistant` / `system`**（**`MessageRole`**） |

### 成功时 `data` 形状（`ListResult`）

- **`records`**：`ConversationMessageItem` 数组（`id`、`conversation_id`、`role`、`content`、`turn_id`、`meta`、`created_at` 等）。
- **`total` / `page` / `limit`**：同上。

### 排序

按消息 **`created_at` 降序**（较新的消息在前）。

### 会话不存在

返回 **`code !== 0`**，**`msg`** 含「不存在」类提示；**`data` 可能为 `null`**（与当前路由声明 **`ResponseResult[ListResult[...] | None]`** 一致）。前端与测试应兼容 **`data` 为空** 的解析。

### 失败与 `data`

数据库或其它异常时，**`fail`** 分支同样可能 **`data` 为 `null`**；处理建议同列表接口。

---

## 3. 测试

集成用例见 **`tests/test_conversations_api.py`**，依赖本机可连的 **`DATABASE_URL`**（**`requires_postgres`**；无库时跳过）。
