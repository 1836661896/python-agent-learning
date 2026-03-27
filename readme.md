# Python Agent 学习进度记录

> 这是用于在多台设备之间同步学习进度的文档。  
> 每次提交代码前，都会先由助手提示我更新这里的记录。

**给助手（新对话 / 换设备时）**：请先阅读本文件 + `.cursor/rules/python-study-plan.mdc` + `.cursor/rules/python-learning-checklist.mdc`，以了解：项目目标与学习方式、当前阶段与「下一次学习的起点」、知识点清单与状态。然后按「当前建议」阶段（见下方项目推进计划表）继续教学，知识点按需分散引入、不必一次练完整类方法。

**换设备后快速清单**：① `git pull` ② `source .venv/bin/activate`（Windows 用 `.venv\Scripts\activate`）③ 若 `delete` 未完成，先补全 `src/commands.py` 的 `delete_task` ④ 再选「阶段 4」或「完善 API/前端」（见下方「下一次学习的起点」）。

---

## 基本项目信息

- **项目名称**：Python Agent 学习项目（后端部分）
- **当前阶段**：阶段 4 已收尾；**阶段 6（数据库 + ORM + Alembic）** 任务与 Agent 步骤已落库；**阶段 8 已接入最小 pytest**（`GET /health`）。**React 前端已与后端联调**（health、tasks、agent/run、agent/last-step、**agent/steps**）。
  - ✅ 阶段 0～3 已完成（含 FastAPI GET /health、POST /tasks）
  - ✅ 前端 **阶段 2（组件拆分）** 已完成（`HealthHeader`、`AgentCommand`、`LastStep`、`StepList`、`TaskSection` 等，见 `frontend/readme.md`）。
  - 🔄 **前端下一步**：**阶段 3**（请求层与错误体验：`http` 错误分类、React Query 错误态等，见 `frontend/.cursor/rules/frontend-study-plan.mdc`）。
  - 🔄 **后端下一步**：时间字段 UTC/时区统一；扩展 pytest（如 `/tasks`、含数据库的用例）；**Docker Compose 置后**（与学习计划一致，最后再收口容器化）。
- **主要目标**：
  - 搭建命令行 Agent 雏形（支持基础命令）✅
  - Web API（FastAPI）与命令行共用逻辑 ✅
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

## 最近一次学习（日期：2026-03-27）

### 本次提交补充记录（阶段 8 启动：pytest + Agent 步骤 API 小调整 + 注释与文档对齐）

- **测试**：新增 `pytest.ini`（`pythonpath = .`），`tests/test_health.py` 断言 `GET /health` 返回 200 且 `code == 0`；`requirements.txt` 增加 **`httpx>=0.28.0`**（`TestClient` 依赖）。
- **API**：`GET /agent/last-step`、`GET /agent/steps` 中 **时间戳** 改为 `strftime` 字符串；成功文案统一为 **「查询成功」**；无历史时 **`/agent/steps`** 返回 `fail("暂无操作历史", [])`；删除已不再使用的内存历史相关注释。
- **命令与 Agent**：`src/commands.py` 顶部说明改为与 **PostgreSQL + agent_steps** 一致；`_record_step` 异常分支增加 **`logger.error`**；`tool_list` docstring 与过时「TASK_LIST」表述清理。
- **可选纳入版本库**：根目录 **`docker-compose.yml`**（本地 Postgres 编排）若你希望仓库里就能一键起库，可随本次一并 `git add`；若只在本机用 Postgres.app，也可暂缓提交。

### 上一次学习（日期：2026-03-26，后端阶段 6 深化：配置化 + 依赖注入 + Step 历史落库）

- **环境**：本地安装 **Postgres.app**（PostgreSQL 18，端口 **5432**），建库 **`agent_db`**。
- **依赖**：虚拟环境安装 **SQLAlchemy 2.x、Alembic、psycopg[binary]**，并记入 `requirements.txt`（以本机为准）。
- **工程**：`alembic init alembic`，`alembic.ini` 配置 `postgresql+psycopg://postgres@127.0.0.1:5432/agent_db`，`alembic current` / `revision --autogenerate` / `upgrade head` 跑通；库中已有 **`tasks`**、**`alembic_version`** 表。
- **代码**：`src/db/`（`config` / `base` / `session`）、`src/models/task.py`（`TaskModel`）、`alembic/env.py` 挂接 **`target_metadata = Base.metadata`**。
- **API**：`src/api.py` 中 **`GET/POST/DELETE /tasks`** 已改为读写数据库；`curl` 验证：创建 → 列表有数据 → 删除 → 列表为空；重复删除返回 **「没有找到任务」**。
- **配置化**：新增 `.env` / `.env.example`，`src/db/config.py` 使用 `python-dotenv` + `os.getenv("DATABASE_URL")` 读取连接串，`.gitignore` 已忽略 `.env`。
- **迁移配置对齐**：`alembic/env.py` 支持读取环境变量并覆盖 `sqlalchemy.url`，`alembic current` 正常到 `e17858ab7695 (head)`。
- **会话管理工程化**：新增 `src/db/deps.py`，任务路由改为 **`Depends(get_db)`** 注入会话，减少重复 `with SessionLocal()`。
- **单一数据源**：`src/commands.py` 中 `tool_list/tool_add/tool_delete` 已切换数据库，命令行与 API 使用同一 `tasks` 数据源。
- **Step 历史持久化**：新增 `src/models/step.py`（`agent_steps` 表）与迁移；修复一次空迁移问题后，补充迁移已成功建表（当前表：`tasks`、`agent_steps`、`alembic_version`）。
- **Agent 接口读库**：`GET /agent/last-step`、`GET /agent/steps` 已切换为数据库查询；`POST /agent/run` 执行后可从数据库读到最新步骤，验证通过。
- **本次收尾说明**：当时约定下一次从「时间字段 UTC/时区统一」继续（仍建议在扩展测试与前端联调前完成）。

### 上一次学习（日期：2026-03-24，阶段 4 收尾）

- **后端**：`step_history` 改为 **`deque(maxlen=50)`**；`/agent/steps` 使用 `list(AGENT.step_history)`；`curl` 验证通过。

### 已完成内容（历史汇总，便于换设备接续）

- **环境与命令行（阶段 0）**
  - ✅ 虚拟环境 `.venv`、`src/main.py`、命令行循环、help/version/echo/quit。

- **阶段 1a～1d**
  - ✅ **list / add**：内存任务列表，`TASK_LIST`、`handle_task`、`add_task`，list 空时提示「暂无任务」，add 后提示成功。
  - ✅ **异常与 Ctrl+C**：主循环 try/except，KeyboardInterrupt/EOFError 时提示「确认要退出？输入 y」，再次 Ctrl+C 视为不退出。
  - ✅ **time 命令**：`datetime.now()`、`strftime("%Y-%m-%d %H:%M:%S")`。
  - ✅ **list 带序号**：`enumerate(TASK_LIST, 1)`，输出 `1. xxx`。
  - ✅ **命令去首尾空格**：`command.strip()`。
  - ✅ **模块拆分**：命令逻辑迁至 `src/commands.py`，main.py 通过 `from commands import show_message, handle_command, save_tasks` 使用。

- **阶段 2a～2b**
  - ✅ **任务持久化**：`tasks.json`，启动时 `json.loads` 加载，add 或退出时 `json.dumps` 写回，`with open` 读写。
  - ✅ **工程化**：`requirements.txt`，`logging.basicConfig` 与 `logger.info`（启动、加载/保存任务、添加任务、退出时打日志）。

- **阶段 3（Web API）**
  - ✅ **FastAPI**：`src/api.py`，GET /health，POST /tasks（TaskCreate + field_validator、try/except + logger），与命令行共用 TASK_LIST、save_tasks；uvicorn 启动。
  - ✅ **前后端接口联调**：前端通过请求体（axios `data` / JSON body）传 `description`；后端统一返回结构 `{code, data, msg}`。
  - ✅ **统一错误返回**：增加全局异常处理，将参数校验失败等错误也统一为 `{code, data, msg}` 风格返回（学习阶段 A-1）。
  - ✅ **校验失败提示优化**：参数校验失败时 `msg` 返回更具体的中文原因（如“任务描述不能为空”），并支持多个错误用 `；` 拼接。

- **阶段 4（Agent 工具系统，最小版本）**
  - ✅ 新增 **`POST /agent/run`**：前端传 `{"text": "add xxx"}`，后端调用统一入口并返回 `{code, data, msg}`。
  - ✅ `src/commands.py` 新增统一入口 **`run_tool(command)`**，让 API 与命令行可逐步复用同一套业务逻辑。
  - ✅ 将 `run_tool` 重构为「工具注册表」：`match_*` + `tool_*` + `tools` 列表循环匹配执行，便于后续扩展。
  - ✅ 已接入工具：`list / add / delete / echo / time / help / version`（未知命令返回 `code=1, msg="未知命令"`）。
  - ✅ **`Step` 与 `AGENT.last_step`**：每次 `run_tool` 执行后记录最近一次步骤（含工具名、输入、成败、时间）；未知命令也会写入 `last_step`。
  - ✅ **`GET /agent/last-step`**：返回最近一次 `Step` 的 JSON（与前端 `getLastStep` 联调）。
  - ✅ **前后端全链路**：`myproject/frontend` 已接入 health、tasks、**Agent 命令**、**最后一步**、**操作历史（`/agent/steps`）**（以 `frontend/readme.md` 为准）。

- **任务列表与删除（阶段 1/3 扩展）**
  - ✅ **TASK_LIST 结构**：改为存字典 `{"task_id": int, "task_name": str}`，自增 task_id，add 时判重（`any(t["task_name"] == ...)`）。
  - 🔄 **delete 命令**：逻辑与写法已确定（find-then-remove 或 for+enumerate+pop，删除后 save_tasks、有/无分别提示）；若 `commands.py` 里 `delete_task` 尚未补全，换设备后先补全再继续。
  - ✅ **echo 修复**：handle_echo 直接打印 adjust_command 的返回值，避免对字符串做 [1:] 和 join 导致重复字符丢失。
  - ✅ **知识点**：列表 pop/remove、列表推导式过滤删除、生成器与 any()、next(... None) 查单条、find-then-remove 与 Python 常见写法。

---

## 项目推进计划（按难易：易→中→较难→难）

> 详细阶段说明与清单对照见 **`.cursor/rules/python-study-plan.mdc`**；知识点进度见 **`.cursor/rules/python-learning-checklist.mdc`**。

| 顺序 | 阶段 | 难易 | 项目功能 |
|------|------|------|----------|
| 0 | 阶段 0：环境与骨架 | 易 | ✅ 环境、命令行、help/version/echo |
| 1a | 阶段 1a：基础巩固 | 易 | ✅ list / add 命令（内存任务列表） |
| 1b | 阶段 1b：异常与健壮性 | 易 | ✅ try/except、Ctrl+C 确认退出 |
| 1c | 阶段 1c：更多命令与内置 | 易~中 | ✅ time、strip、enumerate |
| 1d | 阶段 1d：模块与包 | 中 | ✅ commands 模块、import |
| 2a | 阶段 2a：文件与 IO | 中 | ✅ 任务持久化 tasks.json、with、json |
| 2b | 阶段 2b：工程化 | 中 | ✅ requirements.txt、logging |
| 3 | 阶段 3：Web API | 较难 | ✅ FastAPI /health、POST /tasks |
| 4 | 阶段 4：Agent 工具系统 | 较难 | Task/Step 结构、工具封装 ← **收尾完成（含 steps 历史限长）** |
| 5 | 阶段 5：自动化与视觉 | 难 | 截屏、键鼠、图像识别（预研） |
| 6～11 | 阶段 6～11：真实项目扩展 | 较难 | **数据库+ORM+迁移**（✅ 任务与步骤落库）、**Docker/CI**（Docker 后置）、**pytest**（✅ 已启动：`/health`）、**鉴权**、**Redis/异步任务**、**可观测性与 API 规范**（详见 **`.cursor/rules/python-study-plan.mdc`**） |

---

## 下一次学习的起点（提醒未来的自己）

**换设备后**：`git pull` 拉取最新代码，激活虚拟环境（`source .venv/bin/activate`），然后按下面顺序来。

1. **前端（按需）**：**`myproject/frontend` 阶段 3** —— 请求层与错误体验。规则见 **`frontend/.cursor/rules/frontend-study-plan.mdc`**。

2. **后端**
   - **时间字段 UTC 化（优先）**：`src/models/step.py` 使用 `DateTime(timezone=True)`，默认 `datetime.now(timezone.utc)`；API 展示与 DB 类型一致；必要时 Alembic 迁列型。
   - **pytest 扩展**：为 `GET/POST/DELETE /tasks`、`POST /agent/run` + 读库等在本地有 PG 的前提下增加用例（注意测试库/事务隔离或专用测试库）。
   - **质量**：注释与 README 与「库表即真相」保持一致。
   - **阶段 7 Docker**：放在较后收尾（API + PG 一键起）；当前可用 Postgres.app 或自选 compose。

3. **查阅**
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