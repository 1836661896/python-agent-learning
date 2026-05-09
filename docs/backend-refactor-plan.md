# 后端重构与精简 — 执行与进度文档

> **范围**：**仅后端**；**不包含**前端目录重构、接口路径改名以外的联调改造说明（前端可在后端稳定后单独排期）。  
> **用途**：换设备 / 新 Cursor 窗口时，助手与用户先读本文件，可快速对齐「要做到什么、做到哪一步、验收标准」。  
> **维护约定**：每完成一个阶段，在下文 **§7 进度记录** 更新勾选状态与日期；如有决策变更，在 **§8 决策备忘** 补一行。

**关联文档**：

- 目标目录树（长期）：[`expected-directory-structure.md`](./expected-directory-structure.md)
- 仓库功能总览与对外接口：`readme.md`

---

## 1. 背景与动机

- 仓库经历了「命令行学习 → FastAPI → 数据库 → LLM → MCP → 会话记忆」的堆叠，**早期为教学服务的任务列表、内置命令、结构化 `/agent/run` 等与当前「以模型编排 + MCP 为主」的产品方向重叠**，增加心智负担。
- 本次重构目标：在**不改变核心业务价值**的前提下，**收敛为「聊天 + Planner（路由判断）+ MCP + 观测与支线」**，便于后续按 `modules/` 竖切或继续演进。

---

## 2. 目标态（完成后应具备）

### 2.1 能力保留（后端）

- `GET /health`
- `POST /chat`、`POST /chat/stream`（SSE），Planner 输出形态收敛为 **`mcp` 与 `chat` 两种**（见 §3）。
- MCP：`mcp_client.list_tools` / `call_tool`、用户显式 `mcp ...` 语法、路由 **`/mcp/*`**、`/agent/mcp-run`（若仍需要直连 MCP 的调试入口可保留）。
- `POST /agent/nl-run`：**去掉 builtin 执行分支**；规划结果为 `mcp` 则调 MCP，为 `chat` 则继续返回「更适合 `/chat`」类响应（与现逻辑一致即可）。
- 会话与记忆：`conversation` / `conversation_messages`、`GET /conversations/{id}/messages`、`conversation_memory` 与 **`MEMORY_*`**。
- 可观测：`GET /events`、chat/agent 侧事件与结构化日志。
- 文档支线：`doc_sessions` 相关路由（除非单独决定下线）。
- 多 LLM 提供商、`plan_with_llm`、fallback 等与 Planner 相关的 `src/llm/` 能力。

### 2.2 能力移除或停用（后端）

| 项 | 说明 |
|----|------|
| **`GET/POST/DELETE /tasks`** | 早期任务 CRUD；移除路由及相关 Schema。**数据库 `tasks` 表**：可选择保留空表、或新增 Alembic migration 删除表（二选一，在 §8 记录决定）。 |
| **`POST /agent/run`** | 直接执行字符串命令（list/time/echo…）；移除。 |
| **`src/agent_service.py`（及 `run_tool`、内置 `Tool` 列表）** | 与 builtin / 命令行时代绑定；Planner 不再产出 builtin 后应删除或已无引用则可删文件。 |
| **Planner `kind: "builtin"`** | 从模型 prompt、`validate_plan`、chat/agent 所有 builtin 分支中移除；若模型仍输出 builtin，应在校验阶段**明确报错**，便于排查。 |
| **`nl_utils` 中 builtin 白名单与 payload 组装** | 如 `ALLOWED_BUILTIN_CMDS`、`is_allowed_nl_command`、`build_builtin_event_payload` 等在移除 builtin 后删除无引用代码。 |
| **可选：`src/llm/intent.py`** | 若全仓库无引用，作为早期规则路由可删除，避免误导。 |

### 2.3 待定决策（需在 §8 勾选）

- **`GET /agent/last-step`、`GET /agent/steps`**：若步骤来源仅剩已删除的 `run_tool`，新环境下可能长期无数据。选项：**A)** 暂时保留接口（兼容前端）；**B)** 移除路由；**C)** 后续让 MCP 执行也写入 `agent_steps`（独立迭代）。**本次重构可先选 A 或 B，并在 §8 写明。**

---

## 3. Planner 契约变更（核心）

**现行（重构前）**：`kind ∈ {mcp, builtin, chat}`。

**目标（重构后）**：`kind ∈ {mcp, chat}`。

**需要你落地的改动要点**：

1. **`src/llm/agent_plan.py`**  
   - System prompt 只描述两种 JSON。  
   - `validate_plan`：去掉 builtin 分支；若 `kind == "builtin"` 可统一抛出 `PlanError`（提示已不再支持）。  
   - `_finalize_plan_from_model_text` / `plan_with_ollama` / `plan_with_zhipu` / `plan_with_llm`：**移除 `allowed_builtin_cmds` 参数**（或等价简化签名）。

2. **`src/llm/types.py`、`src/llm/llm_factory.py`**  
   - `LLMClient.plan(...)` 与适配器实现：**去掉第三个参数 `allowed_builtin_cmds`**。

3. **所有调用 `llm_client.plan(...)` 处**  
   - `src/routers/chat/logic.py`  
   - `src/routers/agent.py`  
   - 以及测试中 monkeypatch 的 lambda 签名需同步。

4. **Chat 包**  
   - 删除非流式 `_handle_builtin_non_stream` 及流式里 builtin 分支；删除对 `_chat_pkg().run_tool`、`build_builtin_event_payload`、`_record_builtin_rejected_event`、`_builtin_rejected_message` 等的引用。  
   - `src/routers/chat/__init__.py`：**移除 `run_tool` 的导出**（若测试依赖 monkeypatch `src.routers.chat.run_tool`，改为 patch 其它稳定锚点或改写测试）。

---

## 4. 分阶段执行顺序（推荐）

按顺序做可降低「半截不可用」时间；每一阶段结束建议 **`python -m pytest -q`** 或至少跑与改动相关的子集。

| 阶段 | 内容 | 验收要点 |
|------|------|----------|
| **R1** | 收窄 Planner 契约（§3）：改 `agent_plan`、`types`、`llm_factory`，全仓库替换 `plan` 调用签名 | 无 `allowed_builtin_cmds`；非法 kind/builtin 有清晰错误 |
| **R2** | Chat：`logic.py` / `non_stream.py` / `sse.py` / `events.py` / `chat_turn.py` 去掉 builtin | `/chat` 与 `/chat/stream` 仅 mcp / chat / fallback chat |
| **R3** | Agent：`agent.py` 去掉 builtin 分支与 **`/agent/run`**；去掉对 `run_tool` 的 import | `nl-run` 仅剩 mcp 与 chat 分流 |
| **R4** | 移除 **`tasks` 路由**、`schemas/tasks`、`models/task`（若删模型则在 §8 写明清库策略）；**删除 `agent_service.py`** | `api.py` 不再 include tasks；无残余 import |
| **R5** | 精简 **`nl_utils`**（删 builtin 相关函数）；删除 **`intent.py`**（若未引用） | `grep builtin`、`grep run_tool`、`grep TaskModel` 仓库根目录自查干净 |
| **R6** | **测试**：删改 `test_tasks_api.py`、`test_agent_api.py`、builtin 相关 chat/stream/nl_run/agent_plan 用例 | `pytest` 通过 |
| **R7** | **文档**：更新 `readme.md` §2 功能表（去掉 tasks、agent/run、planner builtin）；本节 §7 打勾 | 新会话读后不因陈旧描述误判 |

---

## 5. 文件核对清单（执行时逐项勾选）

### 5.1 装配与路由

- [ ] `src/api.py` — 移除 `tasks_router` 及对应 import  
- [ ] `src/routers/__init__.py` — 移除 `tasks_router` 导出（若有）

### 5.2 删除或大幅删减的文件（按需）

- [ ] `src/routers/tasks.py`  
- [ ] `src/agent_service.py`  
- [ ] `src/schemas/tasks.py`  
- [ ] `src/models/task.py`（若删除，同步 `src/models/__init__.py`）  
- [ ] `src/llm/intent.py`（确认无引用后）

### 5.3 Schema

- [ ] `src/schemas/__init__.py` — 去掉 `TaskCreate`、`AgentRunRequest`（若已删除 `/agent/run`）  
- [ ] `src/schemas/agent.py` — 删除 `AgentRunRequest`（若不再使用）

### 5.4 Planner 与 LLM

- [ ] `src/llm/agent_plan.py`  
- [ ] `src/llm/types.py`  
- [ ] `src/llm/llm_factory.py`

### 5.5 Chat / Agent / NL

- [ ] `src/routers/chat/logic.py`  
- [ ] `src/routers/chat/non_stream.py`  
- [ ] `src/routers/chat/sse.py`（文档字符串若仍写 builtin 需改）  
- [ ] `src/routers/chat/events.py`  
- [ ] `src/routers/chat/chat_turn.py`  
- [ ] `src/routers/chat/__init__.py`  
- [ ] `src/routers/agent.py`  
- [ ] `src/routers/nl_utils.py`

### 5.6 测试（至少全文检索替换）

- [ ] `tests/test_tasks_api.py` — 删除或整文件移除  
- [ ] `tests/test_agent_api.py` — 不再依赖 `/agent/run`  
- [ ] `tests/test_chat_api.py`、`tests/test_chat_stream_plan.py` — builtin 改为 mcp/chat  
- [ ] `tests/test_nl_run_api.py` — builtin 用例改为 mcp 或 chat 场景  
- [ ] `tests/test_agent_plan.py`、`test_agent_plan_provider.py`、`test_agent_plan_ollama.py`、`test_agent_plan_zhipu.py`  
- [ ] `tests/test_nl_utils.py` — 去掉 builtin 相关断言  
- [ ] `tests/test_conversation_memory_chat.py` — `plan` mock 签名改为两参数（或 `*args`）

---

## 6. 数据库与迁移（提醒）

- 删除 **`TaskModel`** 并不等于自动删除数据库里的 **`tasks` 表**。若需要删表，应 **单独 Alembic revision**（`op.drop_table('tasks')`），并在团队环境执行 `alembic upgrade head`。  
- 若暂时保留空表，仅在 §8 写明「表保留、代码无引用」即可。

---

## 7. 进度记录（人工更新）

| 阶段 | 状态 | 完成日期 | 备注 |
|------|------|----------|------|
| R1 Planner 契约 | ☐ 未开始 / ☐ 进行中 / ☐ 完成 | | |
| R2 Chat 去 builtin | ☐ / ☐ / ☐ | | |
| R3 Agent 去 builtin + 删 `/agent/run` | ☐ / ☐ / ☐ | | |
| R4 删 tasks + agent_service + task 模型 | ☐ / ☐ / ☐ | | |
| R5 nl_utils / intent 清理 | ☐ / ☐ / ☐ | | |
| R6 pytest 全绿 | ☐ / ☐ / ☐ | | |
| R7 readme + 本文件 §8 | ☐ / ☐ / ☐ | | |

---

## 8. 决策备忘

（在此记录与「默认方案」不同的选择，例如：`tasks` 表是否 drop、`/agent/steps` 是否保留。）

- （待补充）

---

## 9. 给助手（新对话）的读取说明

开场请先读：`readme.md` → **本文件** → `.cursor/rules/python-study-plan.mdc` → `user-profile.mdc`。  
若用户说「后端重构」，以 **§7 进度记录** 为准接着指导；**不要假设前端同步完成**。  
用户本地执行改动时，助手默认**不直接改 `.py`**（除非用户当次写明「本次允许修改代码」）。

---

## 10. 文档修订历史

| 日期 | 说明 |
|------|------|
| 2026-05-09 | 初稿：后端专用重构目标、分阶段、文件清单、进度表与助手约定。 |
