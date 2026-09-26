from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
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


def _column_default_sql(column) -> str:
    """为 ALTER TABLE ADD COLUMN 生成简单的默认值子句（仅支持标量默认值）"""
    default = column.default
    if default is None or not getattr(default, "is_scalar", False):
        return ""
    value = default.arg
    if isinstance(value, bool):
        return f" DEFAULT {1 if value else 0}"
    if isinstance(value, (int, float)):
        return f" DEFAULT {value}"
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f" DEFAULT '{escaped}'"
    return ""


def _migrate_add_missing_columns(connection) -> list:
    """
    幂等的增量迁移：对已存在的表补齐模型中新增的列（ALTER TABLE ADD COLUMN）。
    只加列、不删列、不删表，绝不丢数据。返回新增的列名列表。
    """
    from sqlalchemy import inspect

    inspector = inspect(connection)
    added = []
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            col_type = column.type.compile(dialect=connection.dialect)
            ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}{_column_default_sql(column)}'
            connection.exec_driver_sql(ddl)
            added.append(f"{table.name}.{column.name}")
        # 新增列上的索引（CREATE INDEX IF NOT EXISTS 语义，只加不删）
        for index in table.indexes:
            index.create(connection, checkfirst=True)
    return added


async def init_db():
    """初始化数据库：创建缺失的表 + 补齐缺失的列（安全迁移，不会删除任何数据）"""
    import models  # noqa: F401  确保所有模型已注册到 Base.metadata

    async with engine.begin() as conn:
        def _setup(connection):
            Base.metadata.create_all(connection)
            added = _migrate_add_missing_columns(connection)
            if added:
                print(f"[db] 已自动补齐字段: {', '.join(added)}")

        await conn.run_sync(_setup)
