"""统一 API 响应结构。"""


def ok(msg: str, data=None):
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
