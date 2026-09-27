from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import production_problems, settings
from api import router, startup_event
from auth import require_admin
from llm import LLMError
from usage_api import router as usage_router


def _announce_database() -> None:
    """启动时醒目打印实际使用的数据库，未显式配置 DATABASE_URL 时给出警告"""
    url = settings.DATABASE_URL
    shown = url.split("///", 1)[-1] if url.startswith("sqlite") else url.split("@")[-1]
    print(f"[startup] 环境：{settings.APP_ENV}；数据库：{shown}（来源：{settings.DATABASE_URL_SOURCE}）", flush=True)
    if not settings.DATABASE_URL_SOURCE.startswith("环境变量"):
        bar = "!" * 70
        for line in (bar, f"注意：没有设置 DATABASE_URL，正在使用 {shown}",
                     "如果这不是你想用的库，请立即停止服务并设置 DATABASE_URL", bar):
            print(f"[startup] {line}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动：生产安全检查 → 初始化数据库 → （仅开发环境显式开启时）播种演示数据 → 恢复中断任务"""
    problems = production_problems(settings)
    if problems:
        for problem in problems:
            print(f"[startup] 拒绝启动：{problem}", flush=True)
        raise RuntimeError("；".join(problems))
    _announce_database()
    await startup_event()
    yield


# 创建 FastAPI 应用（生产环境关闭 /docs、/redoc、/openapi.json）
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI 教学助手系统 - 提供作业批改、错题本、教案生成等功能",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_API_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_API_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_API_DOCS else None,
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
# 运维接口（模型用量统计）仅管理员可访问
app.include_router(usage_router, prefix=settings.API_PREFIX, dependencies=[Depends(require_admin)])


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
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
