from pydantic import BaseModel, Field
from datetime import date

class TransactionBase(BaseModel):
    account_id: int = Field(examples=[1])
    category_id: int = Field(examples=[3])
    amount: float = Field(examples=[-12000.0], description="+수입 / -지출")
    occurred_on: date = Field(examples=["2025-09-12"])
    description: str | None = Field(default=None, examples=["점심 식비"])

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    account_id: int | None = None
    category_id: int | None = None
    amount: float | None = None
    occurred_on: date | None = None
    description: str | None = None

class TransactionOut(TransactionBase):
    id: int
    class Config:
        from_attributes = True
