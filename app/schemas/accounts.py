from pydantic import BaseModel, Field

class AccountBase(BaseModel):
    account_name: str = Field(min_length=1, examples=["현금"])
    balance: float = Field(default=0, examples=[0])

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    account_name: str | None = None
    balance: float | None = None

class AccountOut(AccountBase):
    id: int
    class Config:
        from_attributes = True
