from datetime import date as date_type, datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


# --- Category Schemas ---
class CategoryBase(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Food & Dining"})
    icon: Optional[str] = Field("🏷️", json_schema_extra={"example": "🍔"})


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int
    is_default: bool

    model_config = ConfigDict(from_attributes=True)


# --- Expense Schemas ---
class ExpenseBase(BaseModel):
    amount: float = Field(..., gt=0, json_schema_extra={"example": 450.0})
    category_id: int = Field(..., json_schema_extra={"example": 1})
    description: Optional[str] = Field(None, json_schema_extra={"example": "Swiggy lunch order"})
    raw_input: Optional[str] = Field(None, json_schema_extra={"example": "swiggy lunch 450"})
    date: date_type = Field(default_factory=date_type.today)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseResponse(ExpenseBase):
    id: int
    created_at: datetime
    category: Optional[CategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)



# --- AI & Parsing Schemas ---
class NaturalLanguageInput(BaseModel):
    text: str = Field(..., json_schema_extra={"example": "spent 250 on petrol yesterday"})



class AIParseResponse(BaseModel):
    amount: float
    category_name: str
    category_id: Optional[int] = None
    description: str
    date: str
    confidence: float
    is_ai: bool = True
    raw_text: str


# --- Analytics & Dashboard Schemas ---
class CategoryBreakdownItem(BaseModel):
    category_name: str
    icon: str
    amount: float
    percentage: float
    count: int


class DashboardSummary(BaseModel):
    month: str
    total_amount: float
    prev_month_total: float
    percentage_change: float
    expense_count: int
    top_categories: list[CategoryBreakdownItem]
    category_breakdown: Dict[str, float]


class MonthlyReportResponse(BaseModel):
    id: Optional[int] = None
    month: str
    total_amount: float
    category_breakdown: Dict[str, float]
    ai_summary: str
    generated_at: str
