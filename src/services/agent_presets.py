"""Agent 身份 preset：从 src/prompts/presets/<id>.md 加载规则并拼 system。"""

from dataclasses import dataclass
from pathlib import Path

_PRESETS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "presets"

# 已知 preset （用于校验；新身份：加 md + 在此登记）
PRESET_SCHEDULE = "schedule"

_KNOWN: frozenset[str] = frozenset({PRESET_SCHEDULE})


@dataclass(frozen=True)
class PreseMeta:
    """单个 preset 的元数据（后期可加 display_name、icon 等）。"""

    id: str
    title: str  # 给前端按钮、日志用


# 注册表
_REGISTRY: dict[str, PreseMeta] = {
    PRESET_SCHEDULE: PreseMeta(id=PRESET_SCHEDULE, title="行程规划师"),
}


def known_preset_ids() -> frozenset[str]:
    """已知 preset ID 集合"""
    return _KNOWN


def is_known_preset(preset: str | None) -> bool:
    """是否已知 preset"""
    return (preset or "").strip() in _KNOWN


def get_preset_meta(preset_id: str) -> PreseMeta | None:
    """获取 preset 元数据"""
    return _REGISTRY.get(preset_id.strip())


def _preset_path(preset_id: str) -> Path:
    """获取 preset 路径"""
    pid = preset_id.strip()
    if not pid or pid != Path(pid).name:
        raise ValueError(f"非法 preset ID： {preset_id!r}")
    return _PRESETS_DIR / f"{pid}.md"


# 加载 preset 指南文本
def load_preset_guide_text(preset_id: str) -> str:
    """读区 preset 对应 md 全文。"""
    path = _preset_path(preset_id)
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as e:
        return (
            f"（未能读取 preset 规则：{path}\n错误：{e} \n\n）"
            f"请确认存在 src/prompts/presets/{preset_id.strip()}.md"
        )


# 构建 preset system 内容
def build_preset_system_content(preset_id: str) -> str:
    """拼成一条 system 的 content。"""
    meta = get_preset_meta(preset_id)
    title = meta.title if meta else preset_id
    body = load_preset_guide_text(preset_id)
    return (
        f"你当前处于【{title}】模式（preset={preset_id.strip()}）。"
        "请严格遵循下列规则与用户对话。\n\n"
        f"{body}"
    )
