from app.db.base_class import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, TIMESTAMP, func, DECIMAL
from datetime import datetime
from typing import Optional


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.category_id"), index=True)
    amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    account: Mapped["Account"] = relationship("Account", back_populates="transactions")
    category: Mapped["Category"] = relationship("Category", back_populates="transactions")
