from fastapi import FastAPI
from app.api.routes import auth
from app.core.config import settings

print(">>> MAIN DB USER:", settings.db_user)
print(">>> MAIN DB URL:", f"mysql+aiomysql://{settings.db_user}:{settings.db_password}@{settings.db_host}/{settings.db_name}")

app = FastAPI()

# 라우터 등록
app.include_router(auth.router)

