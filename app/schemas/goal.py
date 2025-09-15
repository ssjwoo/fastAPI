from pydantic import BaseModel, Field

class GoalBase(BaseModel):
    category_id : int = Field(examples=[5])
    month : str = Field(pattern=r"^\d{4}-\d{2}$", examples=["2025-09"])
    monthly_limit : float = Field(examples=[300000.00])

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    monthly_limit : float | None = None

class GoalOut(GoalBase):
    id : int
    user_id : int

    class Config : 
        from_attributes = True
