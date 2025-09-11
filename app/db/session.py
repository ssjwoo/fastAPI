from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = "mysql+aiomysql://root:12345@localhost/finance"

# DB연결 - 디버깅용으로 echo=True
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
