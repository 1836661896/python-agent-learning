import json
import logging
import uuid
from typing import Any


def new_request_id() -> str:
    """生成短 request_id，便于日志关联。"""
    return uuid.uuid4().hex[:12]


def _emit(logger: logging.Logger, level: str, event: str, payload: dict[str, Any]) -> None:
    text = f"{event} {json.dumps(payload, ensure_ascii=False, sort_keys=True)}"
    if level == "info":
        logger.info(text)
    elif level == "warning":
        logger.warning(text)
    else:
        logger.error(text)


def _meta_from_plan_meta(plan_meta: dict[str, Any] | None) -> dict[str, Any]:
    meta = plan_meta or {}
    return {
        "provider_used": meta.get("provider_used", "unknown"),
        "fallback_used": bool(meta.get("fallback_used", False)),
    }


def log_done(
    logger: logging.Logger,
    *,
    event: str,
    endpoint: str,
    request_id: str,
    route_kind: str,
    tool_succeeded: bool,
    plan_meta: dict[str, Any] | None = None,
    level: str | None = None,
    error: Exception | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    统一业务完成日志（成功/失败都用这个）。

    - event: 例如 "chat_request_done" / "agent_request_done" / "chat_stream_done"
    - endpoint: 例如 "/chat" / "/agent/nl-run" / "/chat/stream"
    - route_kind: 例如 "mcp" / "builtin" / "chat" / "runtime_error"
    - plan_meta: planner_meta，用于抽取 provider_used/fallback_used
    - level: 不传则 tool_succeeded=True->info，tool_succeeded=False->warning（若 error 存在则 error）
    - error: 若传入，会附加 error_type/error_msg
    - extra: 附加字段（会 merge 进 payload）
    """
    payload: dict[str, Any] = {
        "request_id": request_id,
        "endpoint": endpoint,
        "route_kind": route_kind,
        "tool_succeeded": tool_succeeded,
        **_meta_from_plan_meta(plan_meta),
    }

    if error is not None:
        payload["error_type"] = type(error).__name__
        payload["error_msg"] = str(error)

    if extra:
        payload.update(extra)

    if level is None:
        if tool_succeeded:
            level = "info"
        else:
            level = "error" if error is not None else "warning"

    _emit(logger, level, event, payload)