# LLM 多提供商架构与配置

> **何时更新**：调整 **`src/providers/`**、**`src/llm/completion.py` / `streaming.py`**、**`src/env.py`** 或 **`.env.example`** 中与 **`LLM_*` / `ZHIPU_*` / `OLLAMA_*`** 相关的约定时，同步本文件与根目录 **`readme.md` §3、§4**。

---

## 1. 设计目标

- **业务层**（`chat_stream`、`route_auto`、`conversation_refine`）只调用统一入口，不直接依赖某一厂商：
  - 非流式：**`complete_chat(messages)`**（`src/llm/completion.py`）
  - 流式：**`iter_chat_chunks(messages)`**（`src/llm/streaming.py`）
- **厂商差异**（URL、鉴权、SSE 解析）集中在 **`src/providers/`** 各文件。
- **切换模型**：改 **`.env`** 的 **`LLM_PROVIDER`** 及对应厂商变量；**不必**改 `chat_stream` 等主流程。
- **新增厂商**：新增 `providers/xxx.py` 实现 **`complete` + `iter_chunks`**，在 **`providers/__init__.py`** 的 **`_REGISTRY`** 注册，并更新 **`.env.example`**。

---

## 2. 目录与职责

```text
src/
├── env.py                 # 应用侧唯一 load_dotenv（backend 根 .env）
├── api.py                 # 首行 import src.env，保证后续 import 能读到环境变量
├── llm/
│   ├── config.py          # LLM_PROVIDER、LLM_FALLBACK_PROVIDER、LLM_TIMEOUT_SEC（不 load_dotenv）
│   ├── completion.py      # complete_chat → get_provider → Provider.complete
│   ├── streaming.py       # iter_chat_chunks → get_provider → Provider.iter_chunks
│   ├── messages.py        # build_user_message、conversation_rows_to_messages
│   └── mcp_config.py      # MCP_*（不 load_dotenv，依赖 env.py 或 alembic 独立加载）
└── providers/
    ├── base.py            # ChatProvider 协议（complete + iter_chunks）
    ├── __init__.py        # _REGISTRY、get_provider(name)
    ├── ollama.py          # OllamaProvider：/api/chat
    └── zhipu.py           # ZhipuProvider：OpenAI 兼容 /chat/completions
```

**Alembic**（`alembic/env.py`）为**独立进程**，保留自己的 **`load_dotenv()`**，不经过 `src.api`。

---

## 3. 环境变量（`.env`）

| 变量 | 含义 |
|------|------|
| **`LLM_PROVIDER`** | 主提供商：`zhipu` \| `ollama`（小写，见 `llm/config.py`） |
| **`LLM_FALLBACK_PROVIDER`** | 主提供商失败时的备用，如 `ollama`；留空则不回退 |
| **`LLM_TIMEOUT_SEC`** | HTTP 超时（秒），各 Provider 共用 |
| **`MCP_REPLY_VIA_LLM`** | `true`/`false`（默认 `false`）：MCP 工具返回后是否再 **`iter_chat_chunks`** 润色（见 **`chat_stream` mcp 分支**） |
| **`ZHIPU_API_KEY`** | 智谱 API Key（`LLM_PROVIDER=zhipu` 时必填） |
| **`ZHIPU_BASE_URL`** | 默认 `https://open.bigmodel.cn/api/paas/v4` |
| **`ZHIPU_MODEL`** | 如 `glm-4-flash` |
| **`OLLAMA_BASE_URL`** | 默认 `http://127.0.0.1:11434` |
| **`OLLAMA_MODEL`** | 如 `qwen:7b` |

复制 **`.env.example`** → **`.env`** 后按上表填写。勿将真实 Key 提交 git。

---

## 4. `.env` 加载约定

| 入口 | 如何加载 `.env` |
|------|------------------|
| **`uvicorn src.api:app`** | `api.py` 顶部 **`import src.env`** |
| **`alembic upgrade`** | `alembic/env.py` 内 **`load_dotenv()`** |
| **`python -c` / 零散脚本** | **第一行**写 **`import src.env`**，再 import 其它 `src.*` |
| **pytest** | 多数用例 mock LLM；若需真实 Key，可在 **`tests/conftest.py`** 顶部 **`import src.env`** |

**不要**在 `llm/config.py`、`db/config.py`、`mcp_config.py`、`providers/__init__.py` 再分散 **`load_dotenv`**（已收敛到 **`src/env.py`** + Alembic）。

**Import 顺序**：创建 **`ZhipuProvider()` / `OllamaProvider()`** 单例时会读 `os.getenv`；须保证此前已执行 **`import src.env`**。

---

## 5. 谁在用 LLM？

| 调用方 | 入口 | 流式 |
|--------|------|------|
| 聊天 **`routing=chat`** 或 **`auto→chat`** | `chat_stream` → `iter_chat_chunks` | 是 |
| 会话精炼 | `conversation_refine` → `complete_chat` | 否 |
| **`routing=auto` 判别** | `route_auto` → `complete_chat` | 否 |
| **`routing=mcp`** | 默认工具原文 SSE；**`MCP_REPLY_VIA_LLM=true`** 时 **`iter_chat_chunks`** 润色 | 是（润色时） |

---

## 6. 自测命令（backend 根、已 `source .venv/bin/activate`）

```bash
# 1）环境变量是否加载
python -c "
import src.env
import os
from src.llm.config import llm_provider
print('LLM_PROVIDER=', llm_provider)
print('ZHIPU_API_KEY set=', bool(os.getenv('ZHIPU_API_KEY')))
"

# 2）非流式（智谱示例）
python -c "
import src.env
from src.llm.completion import complete_chat
from src.llm.messages import build_user_message
print(complete_chat(build_user_message('只回复：智谱OK')))
"

# 3）流式
python -c "
import src.env
from src.llm.streaming import iter_chat_chunks
from src.llm.messages import build_user_message
print(''.join(iter_chat_chunks(build_user_message('说 hi'))))
"

# 4）API 健康检查（会经 api.py 加载 env）
uvicorn src.api:app --reload
# 另开终端：curl -s http://127.0.0.1:8000/health
```

**通过标准（智谱为主时）**：无 `fallback to ollama`（除非故意配置 fallback）；回复为中文短句而非本机 qwen 典型英文开场。

**关掉 fallback 便于排错**：

```bash
LLM_FALLBACK_PROVIDER= python -c "import src.env; ..."
```

---

## 7. 扩展新提供商（ checklist ）

1. 新建 **`src/providers/<name>.py`**，类实现 **`name`**、**`complete`**、**`iter_chunks`**。
2. 在 **`providers/__init__.py`** 的 **`_REGISTRY`** 注册。
3. **`.env.example`** 增加该厂商变量说明。
4. 更新本文件与 **`readme.md` §3**。
5. 补充 **`tests/`** mock 或可选集成测。

若新厂商 API 与 OpenAI **`/chat/completions`** 兼容，可复制 **`zhipu.py`** 改 URL/环境变量名。

---

## 8. 已知限制（与 readme §7 对齐）

- **`routing=auto`**：复杂工具（**`inputSchema.required` 非空**）须由 LLM 填 **`mcp_arguments`**；点名无必填工具可走规则兜底。
- **MCP 润色**：已支持 **`MCP_REPLY_VIA_LLM`**；SSE **`tool_call`/`tool_result`** 已实现（见 **`docs/chat-stream-api.md` §3**）。下一优先：**前端**展示、**`MCP_ALLOWED_TOOLS`**。

---

*建立：2026-05-16 — LLM 多提供商与 `src/env.py` 收敛说明。*
