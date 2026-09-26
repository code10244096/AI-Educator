from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import settings
from api import router, startup_event
from llm import LLMError
from usage_api import router as usage_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库并播种演示数据（幂等、不调用 AI）"""
    await startup_event()
    yield


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI 教学助手系统 - 提供作业批改、错题本、教案生成等功能",
    lifespan=lifespan,
)


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    """AI 模型调用失败统一返回 502 + 中文原因"""
    return JSONResponse(status_code=502, content={"detail": str(exc)})

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix=settings.API_PREFIX)
app.include_router(usage_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
