# Account 모델 - 계정 관리
from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    type = Column(String)
    balance = Column(Float, default=0.0)

    # 사용자 관계
    user = relationship("User")
    
    # 거래내역 관계
    transactions = relationship("Transaction", back_populates="account")
