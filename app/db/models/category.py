from app.db.base_class import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey
from typing import List


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True)
    category_name: Mapped[str] = mapped_column(String(40), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="categories")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="category")
    budgets: Mapped[List["Budget"]] = relationship("Budget", back_populates="category")
