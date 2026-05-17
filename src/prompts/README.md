# Agent Preset 提示词（运行时）

本目录存放**会被 backend 在聊天时加载**的规则正文，供大模型作为 `system` 消息的一部分使用。

这与仓库根目录下的 **`docs/`** 不同：`docs/` 是给人看的项目说明、API 文档、变更记录；**本目录是程序运行时数据**。

---

## 目录结构

```text
src/prompts/
├── README.md           # 本说明（维护者阅读）
└── presets/
    ├── schedule.md     # preset id = schedule（行程规划师）
    └── …               # 以后新增身份：xxx.md ↔ preset id = xxx
```

**约定**

| 项 | 规则 |
|----|------|
| **preset id** | 与文件名一致（不含 `.md`），如 `schedule` |
| **API / 数据库** | 请求体 `preset: "schedule"` 或会话 `extra_json.preset` 同值 |
| **代码注册** | `src/services/agent_presets.py` 中 `_KNOWN`、`_REGISTRY` |
| **注入方式** | `build_preset_system_content(preset_id)` 拼外层说明 + 读入本 md 全文 |

外层说明（模式名、`preset=` 等）在 **`agent_presets.py`** 中统一生成；**`presets/*.md` 只写该身份的行为规则**，不要再写一遍「你是某某模式」的标题，避免与代码重复。

---

## 新增一个 preset（检查清单）

1. 新建 `presets/<id>.md`（UTF-8，Markdown）。
2. 在 `agent_presets.py` 中：
   - 把 `<id>` 加入 `_KNOWN`；
   - 在 `_REGISTRY` 增加 `PresetMeta(id=..., title="前端按钮文案")`。
3. （后续）`ChatRequest.preset`、会话 `extra_json`、前端按钮传同一 `<id>`。
4. 自测：
   ```bash
   python -c "from src.services.agent_presets import build_preset_system_content; print(len(build_preset_system_content('<id>')))"
   ```

---

## 当前已注册的 preset

| id | 文件 | 标题（UI） | 说明 |
|----|------|------------|------|
| `schedule` | `presets/schedule.md` | 行程规划师 | 多轮追问行程；导出等能力由 MCP 注册工具提供，`routing=auto` 时由路由模型选用 |

对话规则在本目录维护；**backend 不在代码里绑定具体 MCP 工具名**。

---

## 修改注意事项

- 改 md 后**无需重启 MCP**；uvicorn `--reload` 会在下次请求时重新读文件。
- 控制单文件长度，避免挤占过多 context（与 `MEMORY_*` 等配置一并考虑）。
- 涉及 `schedule_json` 字段、导出格式的**设计说明**可写在 `docs/` 或 mcp-server 文档；**给模型看的执行规则**写在本目录对应 md 中。
