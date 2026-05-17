import logging

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import src.env  # noqa: F401  # 副作用：加载 .env
from src.api_response import fail, success
from src.routers.chat import router as chat_router
from src.routers.conversations import router as conversation_router

logger = logging.getLogger(__name__)

# 应用装配层：仅负责中间件、异常处理、健康检查与路由挂载。
app = FastAPI(title="Agent Python Study Project", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc: RequestValidationError):
    # 统一把 Pydantic 校验错误转成项目约定的 {code, data, msg} 返回。
    # exc.errors() 是一个列表，里面每一项是一个字段错误信息 (dict)
    errors = exc.errors()
    msgs = []
    for err in errors:
        if isinstance(err, dict) and isinstance(err.get("msg"), str):
            m = err["msg"]
            if ", " in m:
                m = m.split(", ", 1)[-1]
            msgs.append(m)
    msg = "；".join(msgs) if msgs else "参数校验失败"
    return JSONResponse(status_code=200, content=fail(msg))


@app.exception_handler(HTTPException)
def http_exception_handler(request, exc: HTTPException):
    msg = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return JSONResponse(status_code=exc.status_code, content=fail(msg))


# 健康监测，确保接口畅通
@app.get("/health")
def health():
    return success("服务器正常")


app.include_router(chat_router)
app.include_router(conversation_router)
