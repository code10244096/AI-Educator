"""
API 路由聚合入口（main.py 通过 `from api import router` 引入）。

各功能的实现已拆分到 routers/ 目录：
- routers/grader.py        作业批改（后台任务 + 轮询）、dataset 测试集
- routers/notebook.py      错题本
- routers/lessonplan.py    教案生成 / 列表 / 编辑 / 导出
- routers/classes.py       班级 / 学生 / 作业管理与统计
- routers/questionbank.py  题库管理
- routers/tasks.py         任务聚合
完整接口说明见 backend/API.md。
"""
from fastapi import APIRouter

from routers import classes, grader, lessonplan, notebook, questionbank, tasks

router = APIRouter()
router.include_router(grader.router)
router.include_router(notebook.router)
router.include_router(lessonplan.router)
router.include_router(classes.router)
router.include_router(tasks.router)
router.include_router(questionbank.router)


async def startup_event():
    """初始化数据库、播种演示数据（幂等、不调用 AI）、恢复中断的后台任务（由 main.py 的 lifespan 调用）"""
    from class_service import seed_initial_data
    from database import AsyncSessionLocal, init_db
    from jobs import recover_interrupted_jobs

    await init_db()
    async with AsyncSessionLocal() as db:
        await seed_initial_data(db)
    recovered = await recover_interrupted_jobs()
    if recovered:
        print(f"[startup] {recovered} 个中断的后台任务已标记为失败")
