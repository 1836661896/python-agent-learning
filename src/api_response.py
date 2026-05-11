"""统一 API 响应结构。"""

from typing import Generic, TypedDict, TypeVar

T = TypeVar("T")


class ResponseResult(TypedDict, Generic[T]):
    code: int
    data: T
    msg: str


def success(msg: str, data=None):
    return {"code": 0, "data": data, "msg": msg}


def fail(msg: str, data=None):
    return {"code": 1, "data": data, "msg": msg}
