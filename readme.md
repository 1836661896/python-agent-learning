# Python Agent 学习进度记录

> 这是用于在多台设备之间同步学习进度的文档。  
> 每次提交代码前，都会先由助手提示我更新这里的记录。

**给助手（新对话 / 换设备时）**：请先阅读本文件 + `.cursor/rules/python-study-plan.mdc` + `.cursor/rules/python-learning-checklist.mdc`，以了解：项目目标与学习方式、当前阶段与「下一次学习的起点」、知识点清单与状态。然后按「当前建议」阶段（见下方项目推进计划表）继续教学，知识点按需分散引入、不必一次练完整类方法。

**换设备后快速清单**：① `git pull` ② `source .venv/bin/activate`（Windows 用 `.venv\Scripts\activate`）③ 若 `delete` 未完成，先补全 `src/commands.py` 的 `delete_task` ④ 再选「阶段 4」或「完善 API/前端」（见下方「下一次学习的起点」）。

---

## 基本项目信息

- **项目名称**：Python Agent 学习项目（后端部分）
- **当前阶段**：阶段 3（Web API）已完成 — 下一步做阶段 4（Agent 工具系统）或启动前端
  - ✅ 阶段 0～3 已完成（含 FastAPI GET /health、POST /tasks，与命令行共用 TASK_LIST）
  - 🔄 下一步：阶段 4（Task/Step 结构、工具封装）或启动 React 前端联调
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

## 最近一次学习（日期：2026-03-13）

### 已完成内容

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
| 4 | 阶段 4：Agent 工具系统 | 较难 | Task/Step 结构、工具封装 ← **当前建议** |
| 5 | 阶段 5：自动化与视觉 | 难 | 截屏、键鼠、图像识别（预研） |

---

## 下一次学习的起点（提醒未来的自己）

**换设备后**：`git pull` 拉取最新代码，激活虚拟环境（`source .venv/bin/activate`），然后按下面顺序来。

1. **先检查并补全 delete 命令（若未完成）**
   - 打开 `src/commands.py` 中的 `delete_task`：若仍是「生成器 + print(isIn)、删除逻辑被注释」的状态，需先补全。
   - 推荐写法：`task_id` 需转为 int（若从 adjust_command 得到的是字符串）；用 `for i, t in enumerate(TASK_LIST): if t["task_id"] == task_id: TASK_LIST.pop(i); save_tasks(); print("已删除"); return`，循环外 `print("未找到该任务")`。或在 main 里对 delete 分支把 `adjust_command` 得到的内容转成 int 再传。
   - 补全后再选下面 2 或 3 继续。

2. **阶段 4：Agent 工具系统**
   - 定义 Task/Step 数据结构（类或 dataclass），将 list、add、delete、time、echo 等命令封装为「工具」，统一命令解析与日志。
   - 对应清单 §4 进阶、§9 logging。

3. **或继续完善 API 与前端**
   - 后端补 GET /tasks、按 id 的 GET/PUT/DELETE，与前端联调。

4. **查阅**
   - 完整阶段说明与清单章节对照：`.cursor/rules/python-study-plan.mdc`
   - 知识点是否已学/未学：`.cursor/rules/python-learning-checklist.mdc`

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