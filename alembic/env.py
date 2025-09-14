from logging.config import fileConfig
from sqlalchemy import create_engine, engine_from_config, pool
from alembic import context

from app.core.config import settings
from app.db.base import Base 

config = context.config

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

engine = create_engine(settings.sync_db_url, echo=True)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """오프라인 모드 (DB 연결 없이 SQL 스크립트 생성)"""
    url = settings.sync_db_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """온라인 모드 (실제 DB에 연결해서 마이그레이션 실행)"""
    url = settings.sync_db_url
    connectable = create_engine(url, echo=True)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
