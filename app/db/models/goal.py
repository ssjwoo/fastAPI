from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Numeric, String, UniqueConstraint
from app.db.session import Base

class Goal(Base):
    __tablename__ = "goals"

    id : Mapped[int] = mapped_column(Integer, primary_key = True)
    user_id : Mapped[int] = mapped_column(Integer, index = True)
    category_id : Mapped(int) = mapped_column(Integer, index = True)
    month : Mapped[str] = mapped_column(String(7), index = True)
    mothly_limit = Mapped[float] = mapped_column(Numeric(14,20000))