from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import SessionLocal
from app.schemas.user import UserCreate, UserOut
from app.db.models.user import User
from app.core.security import get_password_hash, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/register", response_model=UserOut)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = User(
        user_name=user.username,
        email=user.email,
        password=get_password_hash(user.password),
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
