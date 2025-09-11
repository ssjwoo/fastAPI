from app.db.base_class import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, TIMESTAMP, func, ForeignKey
from datetime import datetime
from typing import Optional, List


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True)
    bank_name: Mapped[str] = mapped_column(String(40), nullable=False)
    card_name: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP, server_default=func.now(), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="account")
