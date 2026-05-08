"""统一 API 响应结构。"""


def success(msg: str, data=None):
    return {
        "code": 0,
        "data": data,
        "msg": msg,
    }


def fail(msg: str, data=None):
    return {
        "code": 1,
        "data": data,
        "msg": msg,
    }
