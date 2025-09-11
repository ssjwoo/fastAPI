from app.db.base_class import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, ForeignKey, TIMESTAMP, func, DECIMAL
from datetime import datetime


class Budget(Base):
    __tablename__ = "budgets"

    budget_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id"), index=True)
    limit_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="budgets")
    category: Mapped["Category"] = relationship("Category", back_populates="budgets")
