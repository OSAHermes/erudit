"""
Erudit - 个人知识管理系统
模块化架构：前端 + 管理后台
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

from core.config import init_db
from api.public import router as public_router
from api.admin import router as admin_router

# 创建 FastAPI 应用
app = FastAPI(title="Erudit - 个人知识管理系统", version="3.0.0")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# 注册路由
app.include_router(public_router)
app.include_router(admin_router)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "请求过于频繁，请稍后再试"})

@app.exception_handler(422)
async def validation_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422, content={"detail": str(exc.errors())})

# 初始化数据库
init_db()


@app.on_event("startup")
async def startup():
    """启动时初始化"""
    init_db()
    print("✅ Erudit 启动成功")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
