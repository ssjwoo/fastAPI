from fastapi import Depends, HTTPException
import jwt
from app.core.security import SECRET_KEY, ALGORITHM
from app.db.session import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

async def get_current_user(token: str = Depends(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
