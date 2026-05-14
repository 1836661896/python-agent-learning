# 会话 HTTP（列表、历史、批量删除、新建）

> **何时更新**：修改 **`src/routers/conversations.py`**、**`src/schemas/conversations.py`** 或分页/筛选/排序/删除/新建约定时同步本文件。  
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

## 3. `POST /conversation/delete` — 批量删除

**作用**：按主键**批量**删除 **`conversation`** 多行。每条关联的 **`conversation_messages`** 由外键 **`ON DELETE CASCADE`** 级联删除（见 **`src/models/conversation_messages.py`**）。

### 路径与方法

- **`POST /conversation/delete`**

### 请求体（JSON）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| **`ids`** | **`number[]`**（整数主键） | 是 | 待删除会话 id 列表；**实现侧对 `ids` 去重**后再查库与删除。 |

**校验**（**`schemas/conversations.py`**）：**`ids`** 至少含一个元素；空数组由校验拦截，不进入路由。

### 成功

- **`code === 0`**。  
- **`msg`**：含删除成功类文案（**可**含本次删除条数）。  
- **`data`**：**可为 `null`**。前端收到成功后**重新请求** **`GET /conversation/list`** 即可。

### 业务失败（当前实现）

- 经查询后，**请求中的 id 在库中均不存在**（即无可删除行）：**`code !== 0`**，**`msg`** 提示未找到会话等；**`data` 可为 `null`**。前端可 toast 后仍**重拉列表**以保持与列表页一致。

### 数据库或其它异常

- **`code !== 0`**；**`data`** 可为 **`null`**；**`rollback`**。

### 路由注册注意

- **`POST /conversation/delete`** 与 **`GET /conversation/list`**、**`POST /conversation/create`** 均为字面路径，宜写在 **`GET /conversation/{conversation_id}/messages`** 之前，避免与动态段混淆。

---

## 4. `POST /conversation/create` — 新建空会话（约定）

> **说明**：创建时**不**负责生成标题、润色 **`kind` 展示名**等；这些交给后续**大模型在聊天/精炼流程**里逐步完善（与 **`chat_stream`**、**`conversation_refine`** 等一致）。**路由实现见 `src/routers/conversations.py`**。

**作用**：插入一行 **`conversation`**（空会话，可无消息），供前端拿到 **`id`** 后再调 **`POST /chat/stream`**（传 **`conversation_id`**）。

### 路径与方法

- **`POST /conversation/create`**

### 请求体（可选）

- **可不传请求体**（无 **`Content-Type: application/json`** 或无 body），或传 **`{}`**。  
- **若传 JSON**，仅 **`kind`** 有意义地**可选**出现；其它键（如 **`memory_title`**）创建阶段**不要求**客户端填写——**默认一律空**（由后端落默认值），避免与「标题交给大模型」重复约定。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| **`kind`** | **`chat` / `mcp` / `plan`**（与 **`ConversationKind`** 一致） | 否 | **不传**或与无 body 时，由后端默认 **`chat`**（表 **`kind`** 非空，需占位枚举值）。 |

**后端默认值（无 body 或缺字段时）**（与 **`src/models/conversation.py`** 一致）：

- **`kind`**：**`chat`**（若未传）。  
- **`memory_title`**：**`""`**。  
- **`memory_summary`**：**`""`**。  
- **`extra_json`**：**`{}`**。  
- **`memory_updated_at`**：**`null`**；**`owner_id`**：**`null`**（鉴权前）。

### 成功

- **`code === 0`**；**`msg`** 简短即可。  
- **`data`**：**`{ "id": <新会话主键> }`**（仅此即可；**`kind`/标题等不必在创建响应里补全**）。

### 失败

- 校验失败（例如将来若允许传 **`kind`** 却传了非法值）：**`code !== 0`**。  
- 数据库异常：**`code !== 0`**，**`rollback`**。

### 路由注册注意

- 与 **`/list`**、**`/delete`** 同为字面路径，注册顺序参见 **§3**。

---

## 5. 测试

集成用例见 **`tests/test_conversations_api.py`**（**`requires_postgres`**；无库时 **skip**）。**列表与历史**已有覆盖。**删除 / 新建**：可按 **`§3` / `§4`** 补充用例（空 **`ids`**、全未命中 **`fail`**、**`POST /create`** 返回 **`data.id`** 与列表可查到等）；非提交硬性要求。
