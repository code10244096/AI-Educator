"""
API 路由聚合入口（main.py 通过 `from api import router` 引入）。

各功能的实现已拆分到 routers/ 目录：
- routers/auth.py          登录 / 退出 / 个人资料 / 修改密码
- routers/grader.py        作业批改（后台任务 + 轮询）
- routers/notebook.py      错题本
- routers/lessonplan.py    教案生成 / 列表 / 编辑 / 导出
- routers/classes.py       班级 / 学生 / 作业管理与统计
- routers/questionbank.py  题库管理
- routers/tasks.py         任务聚合
- routers/workbench.py     工作台汇总（GET /dashboard）

鉴权：除 `POST /auth/login`、`POST /auth/logout` 外，所有接口都需要登录；
业务路由统一在这里通过 `dependencies=[Depends(current_user)]` 挂载，避免遗漏。
完整接口说明见 backend/API.md。
"""
from fastapi import APIRouter, Depends

from auth import current_user
from routers import auth as auth_router
from routers import classes, grader, lessonplan, notebook, questionbank, tasks, workbench

router = APIRouter()

# 账号接口：各自声明依赖（登录 / 退出不需要登录）
router.include_router(auth_router.router)

# 业务接口：一律要求登录，数据按当前教师隔离
business = APIRouter(dependencies=[Depends(current_user)])
business.include_router(grader.router)
business.include_router(notebook.router)
business.include_router(lessonplan.router)
business.include_router(classes.router)
business.include_router(tasks.router)
business.include_router(workbench.router)
business.include_router(questionbank.router)
# 开发用测试集接口（/homework/dataset*、/grader/upload-dataset/*）只在非生产环境注册
from config import settings as _settings  # noqa: E402
if not _settings.IS_PRODUCTION:
    business.include_router(grader.dataset_router)
router.include_router(business)


async def startup_event():
    """初始化数据库、播种演示数据（幂等、不调用 AI）、恢复中断的后台任务（由 main.py 的 lifespan 调用）"""
    from class_service import backfill_ownership, seed_initial_data
    from database import AsyncSessionLocal, init_db
    from jobs import recover_interrupted_jobs

    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_initial_data(db)
        await backfill_ownership(db)
    recovered = await recover_interrupted_jobs()
    if recovered:
        print(f"[startup] {recovered} 个中断的后台任务已标记为失败")
