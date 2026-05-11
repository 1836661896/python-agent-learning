from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api_response import ResponseResult
from src.db.deps import get_db
from src.schemas.conversations import ConversationListItem, ConversationListQuery
from src.schemas.list_result import ListResult

router = APIRouter(prefix="/conversation", tags=["conversations"])


@router.get("/list")
def list_conversations(
    query: ConversationListQuery = Depends(), db: Session = Depends(get_db)
) -> ResponseResult[ListResult[ConversationListItem]]: ...
