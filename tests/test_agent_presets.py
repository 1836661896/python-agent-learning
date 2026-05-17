"""`agent_presets`：preset 注册与 system 拼装。"""

from src.services.agent_presets import (
    PRESET_SCHEDULE,
    build_preset_system_content,
    is_known_preset,
    known_preset_ids,
    load_preset_guide_text,
)


def test_known_preset_schedule():
    assert is_known_preset("schedule")
    assert is_known_preset("  schedule  ")
    assert not is_known_preset(None)
    assert not is_known_preset("unknown")
    assert PRESET_SCHEDULE in known_preset_ids()


def test_load_schedule_guide_not_empty():
    text = load_preset_guide_text(PRESET_SCHEDULE)
    assert len(text) > 200
    assert "提问节奏" in text or "职责范围" in text


def test_build_preset_system_content_wraps_title():
    content = build_preset_system_content(PRESET_SCHEDULE)
    assert "行程规划师" in content
    assert f"preset={PRESET_SCHEDULE}" in content
    assert "提问节奏" in content or "职责范围" in content
