# 文档体系索引（各文件职责）

> **用途**：说明仓库内「说明类文档」谁负责记什么、何时更新，避免 `readme.md` 与多份 `docs/` 分工不清。  
> **维护**：文档体系本身变更时，更新**本文件** + 根目录 **`readme.md`** 文首引用；并视情况更新 **`.cursor/rules/user-profile.mdc`**（用户对协作/文档的偏好）。

---

## 总览表

| 序号 | 文件路径 | 核心作用 | 典型更新时机 |
|------|-----------|-----------|----------------|
| 1 | **`readme.md`**（仓库根） | **当前真相**：后端目录与架构摘要、**已实现/进行中的功能模块及实现程度**、启动与运行方式、API 备忘、**下一次学习/开发起点**；文首指向其余文档 | **随代码变更实时同步**（合并、新路由、重构阶段性结果） |
| 2 | **`docs/changelog.md`** | **逐次变更的详细记录**（偏「历史流水」，可按日期/版本写细） | 每次有对外行为、架构或文档结构变化时追加条目 |
| 3 | **`docs/project-goals.md`** | **项目目标与预期能力**（中长期要建成什么）；排学习计划时**以此对齐方向** | **新增/调整产品期望**时更新；日常小步不改 |
| 4 | **`.cursor/rules/*.mdc`** | **助手行为与教学规则**（是否可改 `.py`、讲解语言、节奏等）+ **`python-study-plan.mdc` / `python-learning-checklist.mdc`** 学习路线与知识点 | 规则变化、阶段推进、清单勾选时更新 |
| 5 | **`docs/collaboration-and-coding-rules.md`** | **人类可读**的协作与编码约定摘要，并**指向** `.cursor/rules` 中权威规则 | 与 `.cursor/rules` 同步补充（避免两处长期矛盾） |
| 6 | **`.cursor/rules/user-profile.mdc`** | **个人画像**：背景、偏好、进度摘要；**便于长期配合** | 用户表达新偏好、进度跃迁、**或本次更新了规划类文档且可能影响协作方式**时更新 |
| — | **`docs/llm-providers.md`** | **LLM 多提供商**：**`src/env.py`**、**`providers/`**、**`complete_chat` / `iter_chat_chunks`**、**.env** 与自测 | **新增/切换厂商**或 **env 加载方式**变更时更新 |
| — | **`docs/chat-stream-api.md`** | **`POST /chat/stream`** 的协议说明（SSE、**`routing`**、**`preset`**、落库、精炼与历史窗口） | **`chat_stream` / 路由 / 事件形态变更**时更新 |
| — | **`docs/agent-presets.md`** | **Agent Preset**：**`src/prompts/presets/`**、**`agent_presets.py`**、与 MCP 分工、扩展检查清单 | **新增/修改 preset** 或 **注入 system** 逻辑变更时更新 |
| — | **`docs/conversations-api.md`** | **会话 HTTP**：**`GET /conversation/list`**、**`GET /conversation/{id}/messages`**、**`POST /conversation/delete`**、**`POST /conversation/create`**（分页、**`data`/`fail`**、**§5 测试**） | **`routers/conversations.py`** 或 **`schemas/conversations.py`** 变更时更新 |
| — | **`docs/backend-refactor-plan.md`** | 后端**具体重构执行清单**（删路由、改 Planner、测试与勾选） | 按重构阶段推进时更新 |
| — | **`docs/product-and-refactor-vision.md`** | **重构与工程原则**（与产品目标交叉部分以 `project-goals.md` 为准） | 重构策略、同仓库迁移方式等共识变化时更新 |

---

## 与「学习仓库」相关的其他文件

| 路径 | 作用 |
|------|------|
| **`.cursor/rules/project-goal-advanced-agent.mdc`** | 长期产品方向（自动化、视觉、高级 Agent）的**方向性**约束 |
| **`frontend/readme.md`** | 前端目录、阶段与联调说明 |
| **`../mcp-server/readme.md`** | MCP Server 当前真相；工具与 **`exports/`**；协作文档与 backend **`.cursor/rules` 约束一致** |

---

## 编写约定（摘要）

1. **`readme.md`**：不写长篇历史叙事；历史细节进 **`docs/changelog.md`**。  
2. **目标陈述**：不重复粘贴大段愿景到 `readme`；以 **`docs/project-goals.md`** 为单一目标源，`readme` 只保留与**当前代码状态**对齐的一小段或表格。  
3. **重构时没有的功能**：`readme` 的「实现程度表」中**可不单独开行**；若已规划但未落地，可标 **「未实现 / 规划中」** 并指向 `project-goals.md` 或 `backend-refactor-plan.md`。  
4. **助手更新文档时**：按 **`user-profile.mdc`** 约定，检查是否需同步更新**个人画像**。

---

*修订：2026-05-09 建立文档体系索引；2026-05-10 增加 **`docs/chat-stream-api.md`** 索引；2026-05-12 增加 **`docs/conversations-api.md`** 索引；2026-05-16 增加 **`docs/llm-providers.md`**；2026-05-17 增加 **`docs/agent-presets.md`**；**`readme.md` §7** 下一优先为 **mcp-server**（导出工具、下线 guide tool）、**前端 preset/工具事件**。*
