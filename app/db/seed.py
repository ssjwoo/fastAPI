import asyncio
from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.security import get_password_hash

async def seed():
    async with SessionLocal() as session:
        # admin 계정
        admin = User(
            user_name="admin",
            email="admin@example.com",
            password= get_password_hash("admin1234")  # 비번 해싱
        )

        # demo 계정
        demo = User(
            user_name="demo",
            email="demo@example.com",
            password= get_password_hash("demo1234")  # 비번 해싱
        )

        session.add_all([admin, demo])
        await session.commit()
        print("✅ Admin & Demo user seeded!")

if __name__ == "__main__":
    asyncio.run(seed())
