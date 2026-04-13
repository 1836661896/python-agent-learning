# Python Agent 学习进度记录

> 这是用于在多台设备之间同步学习进度的文档。  
> 每次提交代码前，都会先由助手提示我更新这里的记录。

**给助手（新对话 / 换设备时）**：请先阅读本文件 + `.cursor/rules/python-study-plan.mdc` + `.cursor/rules/python-learning-checklist.mdc`，以了解：项目目标与学习方式、当前阶段与「下一次学习的起点」、知识点清单与状态。然后按「当前建议」阶段（见下方项目推进计划表）继续教学，知识点按需分散引入、不必一次练完整类方法。

**换设备后快速清单**：① `git pull` ② `source .venv/bin/activate`（Windows 用 `.venv\Scripts\activate`）③ 启动服务 `uvicorn src.api:app --reload` ④ 再按「下一次学习的起点」继续。

---

## 基本项目信息

- **项目名称**：Python Agent 学习项目（后端部分）
- **当前阶段**：阶段 4 已收尾；**阶段 6** 任务与 Agent 步骤已落库；**阶段 8 pytest** 已覆盖 health、`/tasks`、**`/agent/run` + `last-step`**，并新增 **`/agent/nl-run`** 回归测试；**UTC** 在 `src/utils/datetime_fmt.py`；**本机 Ollama**：`POST /chat` + **`POST /agent/nl-run`**（`src/llm/ollama_client.py`，`httpx` 建议 **`trust_env=False`**）。**阶段 7 Docker**：**`docker compose`** 可一键起 **`db` + `api`**（见下文「Docker 备忘」），容器内迁移与 **`/health`、`/tasks`、`/chat`** 已验证。**React 前端**已联调 health、tasks、agent、**agent/steps**。
  - ✅ 阶段 0～3 已完成（含 FastAPI GET /health、POST /tasks）
  - ✅ 前端 **阶段 2（组件拆分）** 已完成（`HealthHeader`、`AgentCommand`、`LastStep`、`StepList`、`TaskSection` 等，见 `frontend/readme.md`）。
  - 🔄 **前端下一步**：**阶段 3**（请求层与错误体验）；已与 **`POST /chat`**、**`POST /agent/nl-run`** 联调（见 **`frontend/readme.md`**）；后续配合后端 **流式 SSE** 扩展 `ChatPanel`。
  - 🔄 **后端下一步**：**聊天流式 + 左侧统一时间线**（见下文「产品/架构共识」）；延续 **NL → 工具** 的结构化与白名单；**鉴权（阶段 9）**；可选 **`/chat` pytest**、**`TEST_DATABASE_URL`**；按需整理 **Alembic 历史重复 revision**。
- **主要目标**：
  - 搭建 Agent 雏形（支持基础命令，历史阶段）✅
  - Web API（FastAPI）作为核心服务层（当前主线）✅
  - 按难易顺序推进项目（详见下方「项目推进计划」）🔄
  - 为前端联调 + 自动化 + 视觉识别打基础

---

## 关联项目（前端）

- **前端项目地址**：与本 backend 同级的 **frontend** 目录。
  - 相对路径（从本仓库根目录）：**`../frontend`** 或 **`frontend`**（若在 myproject 下则为 **`myproject/frontend`**）。
  - 常用绝对路径示例：**`/Users/mrsun/Documents/myproject/frontend`**（以你本机为准）。
- **用途**：React 前端，与本文档描述的后端 API 联调；前端进度与规则见 **frontend/readme.md**、**frontend/.cursor/rules/frontend-project-goal.mdc**。
- **助手约定**：用户提及「前端」「frontend」「前端项目」时，优先到上述 frontend 目录查找规则与 readme。

---

## 产品 / 架构共识（2026-04-09 对话归档）

> 供新对话快速对齐「要做什么、不做什么」；实现时以代码与测试为准，本节仅记共识与约束。

### 能力与路线（已讨论）

- **云端大模型**：可在 `llm` 层增加与 Ollama 并列的实现（环境变量：`base_url`、API Key、模型名）；学习阶段优先 **OpenAI 兼容 HTTP** 或官方 SDK。
- **「真实功能」边界**：自动从外网下载视频并批量发布到 B 站/抖音等，**技术上有人做**，但涉及版权与平台协议，**不作为本学习项目目标**；可改为自有素材、合规链接摘要、半自动或官方开放能力。
- **可落地的练习方向**：云端可切换、无害工具插件、任务长步骤状态机、合规 URL/RSS 摘要、鉴权最小闭环（与阶段 9 一致）。

### 前后端界面与数据（目标形态）

- **右侧**：聊天；期望 **流式返回**（SSE 或 WebSocket 择一）。用户发消息后，后端需区分：**仅对话** vs **需调用工具**（时间、任务增删等）。
- **左侧**：操作历史、任务列表等；**统一「活动/操作记录」模型**，用 **`type` 等字段**区分：聊天、任务变更、工具执行等；与 **`turn_id` / `request_id`** 关联，便于联调与日志。
- **流式协议补充**：除文本 delta 外，预留结构化事件（如 `tool_start` / `tool_end`、`done` / `error`），左侧时间线与右侧正文同步更新。
- **工程要点**：工具 **schema/白名单**、破坏性操作 **确认或二次校验**、历史 **分页/cursor**、与现有 **`agent_service` + `/agent/run` + `/agent/nl-run` + `/chat`** **复用同一套工具注册**，避免多套分叉。

### 大模型「分级 / 路由」（编排）

- **可做**：一级负责 **判断与任务下发**（输出宜 **结构化**：如 `route` / 子任务列表）；二级模块专职（如聊天、任务、版本与时间等），各自 **提示词 + 工具白名单**；后续可继续细分。
- **注意**：多级调用带来 **延迟与费用**；可先用 **代码分支 + 同一模型不同 prompt** 模拟分级，再决定是否独立「路由模型」。
- **流式**：通常仅 **最终对用户回复** 需要 token 流；路由与工具过程用 **事件** 推给左侧更合适。

---

## 最近一次学习（日期：2026-04-08）

### 本次补充（后端服务化整理：移除 CLI 心智，按路由拆分）

- **服务模块重命名**：`src/commands.py` 已迁移为 **`src/agent_service.py`**，保留 `run_tool`、工具匹配、任务读写与 step 记录等服务侧能力；命令行交互函数已移除。
- **API 分层**：`src/api.py` 已从“大一统文件”调整为应用装配层；业务路由拆分到：
  - `src/routers/tasks.py`
  - `src/routers/agent.py`
  - `src/routers/chat.py`
- **统一响应**：新增 `src/api_response.py`，集中维护 `ok/fail` 响应结构，避免重复代码。
- **接口兼容性**：现有对前端开放的路径保持不变（`/health`、`/tasks`、`/agent/*`、`/chat`），前端调用无需改 URL。
- **测试**：`pytest` 已通过（7 项），`test_nl_run_api.py` 的 monkeypatch 目标同步调整为 `src.routers.agent`。
- **启动方式**：`src/main.py` 已改为后端启动入口（`python -m src.main` 可用）；推荐命令仍是 `uvicorn src.api:app --reload`。
- **Schema 分层**：`src/schemas.py` 已拆为 `src/schemas/tasks.py`、`src/schemas/agent.py`、`src/schemas/chat.py`，并通过 `src/schemas/__init__.py` 统一导出。

### 本次记录（本机 Ollama + `POST /chat`；配置与排错）

- **依赖**：本机安装 **Ollama**，拉模型 **`qwen2.5:3b`**（ registry 偶发 DNS 时可换网络或重试 `ollama pull`）。
- **配置**：`.env` / `.env.example` 增加 **`OLLAMA_BASE_URL`**（默认 `http://127.0.0.1:11434`）、**`OLLAMA_MODEL`**；**`python-dotenv`**：`load_dotenv()` 在 **`src/llm/ollama_client.py`** 顶部调用，确保只访问 `/chat` 时也能读到变量（与 `os.getenv` 配合）。
- **代码**：当时在 **`src/schemas.py`** 增加 **`ChatRequest`**（`message: str` + `field_validator`，注意空串用 **`not v.strip()`**、错误用 **`raise ValueError`**，不要 **`return ValueError`**）；当前该模型已迁移到 **`src/schemas/chat.py`**。`src/llm/ollama_client.py` 内通过 **`httpx.post`** 调 Ollama **`/api/chat`**，`stream: false`，解析 **`message.content`**。
- **排错**：本机 `curl` 直连 Ollama 正常而 **`/chat` 报 HTTP 502** 时，**`httpx.Client(..., trust_env=False)`** 避免走环境/系统代理误伤 **`127.0.0.1`**（与终端里验证用的 `httpx.post(..., trust_env=False)` 行为一致）。
- **自测**：`curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d '{"message":"..."}'` → `code=0`，`data` 为模型回复字符串。

### 同日补充（阶段 7 收口：`docker compose` 起 **api + db**）

- **文件**：根目录 **`Dockerfile`**（名称固定，区分大小写；勿用 **`DockerFile`** 以免 Linux/CI 找不到）、**`docker-compose.yml`**（`api` 服务 `build: .`、`depends_on` 等 **`db` healthy**）、**`.dockerignore`**。
- **基础镜像**：若 **Docker Hub / 本地 `registry-mirrors` 403 或超时**，`Dockerfile` 第一行可用 **`FROM public.ecr.aws/docker/library/python:3.9-slim-bookworm`**（AWS 公共镜像，与官方 `python:3.9-slim-bookworm` 对应）。
- **容器内连库**：`DATABASE_URL` 主机名为 **`db`**，例如 `postgresql+psycopg://postgres:postgres@db:5432/agent_db`（与 compose 里 `POSTGRES_*` 一致）。
- **容器内连本机 Ollama**（Mac/Win **Docker Desktop**）：环境变量 **`OLLAMA_BASE_URL=http://host.docker.internal:11434`**（容器里 `127.0.0.1` 不是宿主机）。
- **常用命令**：`docker compose up -d api`；首次或更新模型后 **`docker compose run --rm api alembic upgrade head`**；`docker compose ps`；宿主机 **`curl http://127.0.0.1:8000/health`**。
- **端口**：本机 **`uvicorn` 与容器 `api` 都映射 8000 会冲突**，二选一或改 compose 为 **`"8001:8000"`**。
- **备忘**：迁移日志里若出现多条相似 **`add agent_steps` / `msg`** 的 revision，属历史迭代；换设备以 **`alembic current`** 与表结构为准即可。

### 同日补充（NL → `run_tool` 最小闭环）

- **接口**：新增 **`POST /agent/nl-run`**，流程为「自然语言输入 → Ollama 翻译命令 → 白名单校验 → `run_tool` 执行 → 统一 `{code,data,msg}` 返回」。
- **安全策略**：当前白名单仅放开低风险命令（如 `list/time/help/version/echo`），高风险写操作暂不自动执行。
- **稳定性**：`src/llm/ollama_client.py` 增加命令标准化与 fallback（模型异常输出如 `list/time` 时回落 `unknown`；中文常见问法可兜底映射到 `list`/`time`）。
- **验证**：`curl /agent/nl-run` 已跑通（如“给我看任务列表”“现在几点了”）；返回中 `data.command` 与 `tool_msg` 正常。
- **测试**：新增 `tests/test_nl_run_api.py`，`pytest tests -q` 全量通过（当前 6 项）。

### 上一次学习（日期：2026-03-30，阶段 8 扩展：conftest + 任务/Agent 测试；UTC 工具模块，历史记录）

- **时间**：`src/utils/datetime_fmt.py` 提供 **`format_step_ts_utc`**，**避免 `api` 与 `commands` 循环依赖**；`tool_time` 使用 **`datetime.now(timezone.utc)`**；`POST /agent/run` 与 `GET /agent/last-step` 中时间串可对齐为 **`… UTC`**。
- **测试**：`tests/conftest.py` 注入 **`client`**；`test_tasks_api.py`（创建–列表–删除、重复创建失败、删除不存在失败）；`test_agent_api.py`（`time` + `last-step` + `steps`）；`pytest tests -q` 通过。
- **可选后续**：专用 **`TEST_DATABASE_URL`** 与测试数据隔离；**不继续堆接口测试**时可转 **Docker / 前端阶段 3**。

### 上一次学习（日期：2026-03-27，阶段 8 启动：pytest + Agent 步骤 API 小调整，历史记录）

- **测试**：新增 `pytest.ini`（`pythonpath = .`），`tests/test_health.py` 断言 `GET /health` 返回 200 且 `code == 0`；`requirements.txt` 增加 **`httpx>=0.28.0`**（`TestClient` 依赖）。
- **API**：`GET /agent/last-step`、`GET /agent/steps` 中 **时间戳** 改为 `strftime` 字符串；成功文案统一为 **「查询成功」**；无历史时 **`/agent/steps`** 返回 `fail("暂无操作历史", [])`；删除已不再使用的内存历史相关注释。
- **命令与 Agent（历史记录）**：当时在 `src/commands.py` 完成说明与日志清理；当前已迁移到 `src/agent_service.py`。
- **可选纳入版本库**：根目录 **`docker-compose.yml`**（本地 Postgres 编排）若你希望仓库里就能一键起库，可随本次一并 `git add`；若只在本机用 Postgres.app，也可暂缓提交。

### 上一次学习（日期：2026-03-26，后端阶段 6 深化：配置化 + 依赖注入 + Step 历史落库，历史记录）

- **环境**：本地安装 **Postgres.app**（PostgreSQL 18，端口 **5432**），建库 **`agent_db`**。
- **依赖**：虚拟环境安装 **SQLAlchemy 2.x、Alembic、psycopg[binary]**，并记入 `requirements.txt`（以本机为准）。
- **工程**：`alembic init alembic`，`alembic.ini` 配置 `postgresql+psycopg://postgres@127.0.0.1:5432/agent_db`，`alembic current` / `revision --autogenerate` / `upgrade head` 跑通；库中已有 **`tasks`**、**`alembic_version`** 表。
- **代码**：`src/db/`（`config` / `base` / `session`）、`src/models/task.py`（`TaskModel`）、`alembic/env.py` 挂接 **`target_metadata = Base.metadata`**。
- **API**：`src/api.py` 中 **`GET/POST/DELETE /tasks`** 已改为读写数据库；`curl` 验证：创建 → 列表有数据 → 删除 → 列表为空；重复删除返回 **「没有找到任务」**。
- **配置化**：新增 `.env` / `.env.example`，`src/db/config.py` 使用 `python-dotenv` + `os.getenv("DATABASE_URL")` 读取连接串，`.gitignore` 已忽略 `.env`。
- **迁移配置对齐**：`alembic/env.py` 支持读取环境变量并覆盖 `sqlalchemy.url`，`alembic current` 正常到 `e17858ab7695 (head)`。
- **会话管理工程化**：新增 `src/db/deps.py`，任务路由改为 **`Depends(get_db)`** 注入会话，减少重复 `with SessionLocal()`。
- **单一数据源**：当前 `src/agent_service.py` 中 `tool_list/tool_add/tool_delete` 已使用数据库，API 与 Agent 共用 `tasks` 数据源。
- **Step 历史持久化**：新增 `src/models/step.py`（`agent_steps` 表）与迁移；修复一次空迁移问题后，补充迁移已成功建表（当前表：`tasks`、`agent_steps`、`alembic_version`）。
- **Agent 接口读库**：`GET /agent/last-step`、`GET /agent/steps` 已切换为数据库查询；`POST /agent/run` 执行后可从数据库读到最新步骤，验证通过。
- **本次收尾说明**：当时约定下一次从「时间字段 UTC/时区统一」继续（仍建议在扩展测试与前端联调前完成）。

### 上一次学习（日期：2026-03-24，阶段 4 收尾，历史记录）

- **后端**：`step_history` 改为 **`deque(maxlen=50)`**；`/agent/steps` 使用 `list(AGENT.step_history)`；`curl` 验证通过。

### 已完成内容（历史汇总，便于换设备接续；以下包含早期命令行阶段）

- **环境与命令行（阶段 0，历史阶段）**
  - ✅ 虚拟环境 `.venv`、`src/main.py`、命令行循环、help/version/echo/quit。

- **阶段 1a～1d（历史阶段）**
  - ✅ **list / add**：内存任务列表，`TASK_LIST`、`handle_task`、`add_task`，list 空时提示「暂无任务」，add 后提示成功。
  - ✅ **异常与 Ctrl+C**：主循环 try/except，KeyboardInterrupt/EOFError 时提示「确认要退出？输入 y」，再次 Ctrl+C 视为不退出。
  - ✅ **time 命令**：`datetime.now()`、`strftime("%Y-%m-%d %H:%M:%S")`。
  - ✅ **list 带序号**：`enumerate(TASK_LIST, 1)`，输出 `1. xxx`。
  - ✅ **命令去首尾空格**：`command.strip()`。
  - ✅ **模块拆分**：命令逻辑迁至 `src/commands.py`，main.py 通过 `from commands import show_message, handle_command, save_tasks` 使用。

- **阶段 2a～2b（历史阶段）**
  - ✅ **任务持久化**：`tasks.json`，启动时 `json.loads` 加载，add 或退出时 `json.dumps` 写回，`with open` 读写。
  - ✅ **工程化**：`requirements.txt`，`logging.basicConfig` 与 `logger.info`（启动、加载/保存任务、添加任务、退出时打日志）。

- **阶段 3（Web API，已服务化演进）**
  - ✅ **FastAPI**：`src/api.py`，GET /health，POST /tasks（TaskCreate + field_validator、try/except + logger），与命令行共用 TASK_LIST、save_tasks；uvicorn 启动。
  - ✅ **前后端接口联调**：前端通过请求体（axios `data` / JSON body）传 `description`；后端统一返回结构 `{code, data, msg}`。
  - ✅ **统一错误返回**：增加全局异常处理，将参数校验失败等错误也统一为 `{code, data, msg}` 风格返回（学习阶段 A-1）。
  - ✅ **校验失败提示优化**：参数校验失败时 `msg` 返回更具体的中文原因（如“任务描述不能为空”），并支持多个错误用 `；` 拼接。

- **阶段 4（Agent 工具系统，最小版本）**
  - ✅ 新增 **`POST /agent/run`**：前端传 `{"text": "add xxx"}`，后端调用统一入口并返回 `{code, data, msg}`。
  - ✅ 服务层统一入口 **`run_tool(command)`**（当前位于 `src/agent_service.py`），供 API 路由复用。
  - ✅ 将 `run_tool` 重构为「工具注册表」：`match_*` + `tool_*` + `tools` 列表循环匹配执行，便于后续扩展。
  - ✅ 已接入工具：`list / add / delete / echo / time / help / version`（未知命令返回 `code=1, msg="未知命令"`）。
  - ✅ **`Step` 与 `AGENT.last_step`**：每次 `run_tool` 执行后记录最近一次步骤（含工具名、输入、成败、时间）；未知命令也会写入 `last_step`。
  - ✅ **`GET /agent/last-step`**：返回最近一次 `Step` 的 JSON（与前端 `getLastStep` 联调）。
  - ✅ **前后端全链路**：`myproject/frontend` 已接入 health、tasks、**Agent 命令**、**最后一步**、**操作历史（`/agent/steps`）**（以 `frontend/readme.md` 为准）。

- **任务列表与删除（阶段 1/3 扩展，历史背景）**
  - ✅ **TASK_LIST 结构**：改为存字典 `{"task_id": int, "task_name": str}`，自增 task_id，add 时判重（`any(t["task_name"] == ...)`）。
  - ✅ **delete 命令**：已在数据库版本中稳定可用（`src/agent_service.py` + `/tasks/{task_id}`）。
  - ✅ **echo 修复**：handle_echo 直接打印 adjust_command 的返回值，避免对字符串做 [1:] 和 join 导致重复字符丢失。
  - ✅ **知识点**：列表 pop/remove、列表推导式过滤删除、生成器与 any()、next(... None) 查单条、find-then-remove 与 Python 常见写法。

---

## 项目推进计划（按难易：易→中→较难→难）

> 详细阶段说明与清单对照见 **`.cursor/rules/python-study-plan.mdc`**；知识点进度见 **`.cursor/rules/python-learning-checklist.mdc`**。

| 顺序 | 阶段 | 难易 | 项目功能 |
|------|------|------|----------|
| 0 | 阶段 0：环境与骨架 | 易 | ✅ 环境、命令行、help/version/echo（历史阶段） |
| 1a | 阶段 1a：基础巩固 | 易 | ✅ list / add 命令（内存任务列表） |
| 1b | 阶段 1b：异常与健壮性 | 易 | ✅ try/except、Ctrl+C 确认退出 |
| 1c | 阶段 1c：更多命令与内置 | 易~中 | ✅ time、strip、enumerate |
| 1d | 阶段 1d：模块与包 | 中 | ✅ 早期 commands 模块拆分（已迁移为 agent_service） |
| 2a | 阶段 2a：文件与 IO | 中 | ✅ 任务持久化 tasks.json、with、json |
| 2b | 阶段 2b：工程化 | 中 | ✅ requirements.txt、logging |
| 3 | 阶段 3：Web API | 较难 | ✅ FastAPI /health、POST /tasks |
| 4 | 阶段 4：Agent 工具系统 | 较难 | Task/Step 结构、工具封装 ← **收尾完成（含 steps 历史限长）** |
| 5 | 阶段 5：自动化与视觉 | 难 | 截屏、键鼠、图像识别（预研） |
| 6～11 | 阶段 6～11：真实项目扩展 | 较难 | **数据库+ORM+迁移**（✅）、**pytest**（✅）、**本机 LLM（Ollama `/chat`）**（✅）、**Docker Compose（db + api）**（✅）、**鉴权**、**Redis/异步**、**可观测性**（详见 **`.cursor/rules/python-study-plan.mdc`**） |

---

## 下一次学习的起点（提醒未来的自己）

**换设备后**：`git pull` 拉取最新代码，激活虚拟环境（`source .venv/bin/activate`），然后按下面顺序来。

1. **前端（按需）**：**`myproject/frontend`** —— 继续 **阶段 3**（`http.ts` 错误分类、各 Query 错误态）；布局上已分 **左栏（Agent / 历史 / 任务）** 与 **右栏 `ChatPanel`**，待后端 **SSE** 后接流式 UI。规则见 **`frontend/.cursor/rules/frontend-study-plan.mdc`**。

2. **后端（与「产品/架构共识」对齐）**
   - **流式聊天**：扩展 **`POST /chat`**（或新路由）返回 **SSE**（或 WebSocket），事件类型含 **文本 delta、工具起止、结束/错误**；与 **`turn_id`** 对齐。
   - **统一操作记录**：在现有 **`agent_steps`**（或扩展表/字段）上区分 **`chat` / `task` / `tool` 等**，供 **`GET /agent/steps` 或新列表接口** 与左栏时间线消费；注意 **分页**。
   - **分级路由（渐进）**：`route` → 各子处理器；一级输出 **结构化**；与 **`run_tool`** 白名单、确认策略一致。
   - **阶段 7**：**`docker compose`** 已可 **`db` + `api`**；换设备见 **「最近一次学习 → 阶段 7 收口」**。
   - **pytest 可选**：流式契约测试（mock LLM）；**`/chat`** 用 `skipif`/mock；**`TEST_DATABASE_URL`**。
   - **阶段 9 鉴权**：对外暴露流式与工具前优先评估。

3. **查阅**
   - 本节上方 **「产品/架构共识（2026-04-09）」**
   - 后端阶段与清单：`.cursor/rules/python-study-plan.mdc`、`python-learning-checklist.mdc`
   - 前端进度：**`frontend/readme.md`** 与 **`frontend/.cursor/rules/`**

---

## 提交前更新流程约定

> 每次我要提交代码前，助手会提醒我做下面几件事：

1. **在本文件中更新“最近一次学习”**
   - 修改日期为当前日期。
   - 在“已完成内容”中补充这次新完成的功能或学习点。
   - 在“下一次学习的起点”中写上下一次要做的 2～3 个小目标。

2. **确认内容已经保存**
   - 确认 `readme.md` 已保存（Ctrl+S / Cmd+S）。

3. **再执行 git 提交**
   - 例如：
     ```bash
     git add .
     git commit -m "update progress log and implement xxx"
     git push
     ```

---

---

## 学习日志时间线

### 2026-01-XX（今天）

**主要成果**：
- ✅ 完成阶段 0：命令行程序基础功能全部实现（包括 `echo` 命令）
- ✅ 开始阶段 1：Python 语法基础学习
  - 创建 `basics` 模块，包含变量、数据类型、控制流两个练习文件
  - 系统学习了字符串、数字、列表、字典等基础数据类型
  - 掌握了 `if/else`、`for`、`while` 循环以及 `break`、`continue` 控制语句

**学习重点**：
- 通过类比 JavaScript 理解 Python 语法（如切片、`join()` 方法等）
- 深入理解序列类型（字符串、列表）的切片操作和索引访问
- 理解字典的键值对结构和遍历方法
- 掌握 `range()` 函数的不同用法

**代码文件**：
- `src/main.py`：命令行程序，支持 `help`、`version`、`echo`、`quit` 命令
- `src/basics/01_variables.py`：变量与数据类型练习（109 行）
- `src/basics/02_control_flow.py`：控制流练习（127 行）

---

### 2026-03-13（本次）

**主要成果**：
- ✅ **TASK_LIST** 改为 dict 结构（task_id、task_name），add 判重、自增 id。
- ✅ **delete 命令**：按 task_id 删除，采用 find-then-remove（或 for+enumerate+pop），删除后 save_tasks。
- ✅ **echo 输出修复**：handle_echo 直接打印 adjust_command 返回值，解决重复字符丢失问题。
- ✅ **巩固**：列表 pop/remove、列表推导式、生成器与 any()、next(..., None)、Python 常见删除写法。

---

### 2026-03-13（之前）

**主要成果**：
- ✅ 项目环境搭建（虚拟环境、Git 仓库）
- ✅ 命令行程序基础框架实现
- ✅ 命令处理函数抽象和配置管理

---

## 备注

- 未来如果学习内容变多，可以在本文件中按日期追加新的"小节"，形成一个学习日志时间线。
- 无论在哪台电脑上学习，只要 `git pull` 最新代码，就能通过这个文件快速知道上一次学到哪里、下一步要做什么。