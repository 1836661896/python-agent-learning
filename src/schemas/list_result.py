from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ListResult(BaseModel, Generic[T]):
    records: list[T]
    total: int
    page: int
    limit: int
