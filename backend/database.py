from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

# 创建异步会话
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 创建基类
Base = declarative_base()


async def get_db():
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库（检测 schema 变更时自动重建）"""
    from sqlalchemy import inspect

    async with engine.begin() as conn:
        def _setup(connection):
            inspector = inspect(connection)
            required_columns = {
                "homework_assignments": ["dataset_file_id", "status", "assign_date"],
                "homework_submissions": ["student_name", "grading_status", "dataset_file_id"],
            }
            needs_rebuild = False
            for table, cols in required_columns.items():
                if inspector.has_table(table):
                    existing = {c["name"] for c in inspector.get_columns(table)}
                    if not all(c in existing for c in cols):
                        needs_rebuild = True
                        break
                elif table == "class_members" and not inspector.has_table("class_members"):
                    needs_rebuild = True

            if not inspector.has_table("class_members"):
                needs_rebuild = True

            if needs_rebuild:
                Base.metadata.drop_all(connection)
            Base.metadata.create_all(connection)

        await conn.run_sync(_setup)
