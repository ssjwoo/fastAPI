# Category 모델 - 카테고리 관리
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    type = Column(String)

    # 사용자
    user = relationship("User")

    # 거래내역
    transactions = relationship("Transaction", back_populates="category")

    # 목표
    goals = relationship("Goal", back_populates="category")
