# Agent Preset（身份提示词）

> **用途**：说明 backend 如何加载「对话身份」规则；与 MCP 工具无关。  
> **代码**：**`src/services/agent_presets.py`**、**`src/prompts/presets/`**、**`src/services/chat_stream.py`**（注入 system）。

---

## 与 MCP 的分工

| 能力 | 位置 |
|------|------|
| 身份 / 多轮追问规则 | **`src/prompts/presets/<id>.md`** → 拼入 **`chat`** 的 system |
| 导出、联网、ping 等 | **MCP `tools/list`**；**`routing=auto`** 时由路由 LLM 选 **`mcp_tool`** + **`mcp_arguments`**；**backend 不写死工具名** |

---

## 请求与会话

| 方式 | 说明 |
|------|------|
| **`ChatRequest.preset`** | 如 **`"schedule"`**；优先于会话里已有值（会写入 **`extra_json.preset`**） |
| **`Conversation.extra_json.preset`** | 同一会话后续轮可省略 **`preset`** |
| **`routing=auto` + 行程关键词** | **`route_auto`** 可自动设 **`preset=schedule`**（见 **`docs/chat-stream-api.md` §5**） |

---

## 新增身份（检查清单）

1. 新建 **`src/prompts/presets/<id>.md`**（规则正文；身份头由 **`build_preset_system_content`** 统一加）。  
2. 在 **`agent_presets.py`** 的 **`_KNOWN`**、**`_REGISTRY`** 登记。  
3. 前端 / API：创建会话或发消息时传 **`preset: "<id>"`**（**`POST /conversation/create` 的 `extra_json` 待扩展**）。  
4. 自测：`python -m pytest tests/test_agent_presets.py tests/test_chat_stream.py -q`

---

## 当前已注册

| id | 文件 | 标题 |
|----|------|------|
| `schedule` | `presets/schedule.md` | 行程规划师 |

维护说明见 **`src/prompts/README.md`**。
