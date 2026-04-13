from datetime import datetime, timezone


def format_step_ts_utc(dt: datetime) -> str:
    """把任意 datetime 统一格式化为 UTC 文本。"""
    # 若是没有时区信息
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # 换算到utc时区
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%d %H:%M:%S") + " UTC"
