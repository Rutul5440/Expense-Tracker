from datetime import date as date_type, datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, EmailStr


# --- Auth Schemas ---
class UserRegister(BaseModel):
    email: str = Field(..., json_schema_extra={"example": "user@example.com"})
    username: str = Field(..., json_schema_extra={"example": "John Doe"})
    password: str = Field(..., min_length=6, json_schema_extra={"example": "secret123"})


class UserLogin(BaseModel):
    email: str = Field(..., json_schema_extra={"example": "user@example.com"})
    password: str = Field(..., json_schema_extra={"example": "secret123"})


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# --- Category Schemas ---
class CategoryBase(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Food & Dining"})
    icon: Optional[str] = Field("🏷️", json_schema_extra={"example": "🍔"})


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int
    is_default: bool
    user_id: Optional[int] = None

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
    user_id: Optional[int] = None
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
    top_categories: List[CategoryBreakdownItem]
    category_breakdown: Dict[str, float]


class MonthlyReportResponse(BaseModel):
    id: Optional[int] = None
    month: str
    total_amount: float
    category_breakdown: Dict[str, float]
    ai_summary: str
    generated_at: str


# --- Friend & Split Expense Schemas ---
class FriendBase(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Friend 1"})
    email: Optional[str] = Field(None, json_schema_extra={"example": "friend@example.com"})
    phone: Optional[str] = Field(None, json_schema_extra={"example": "+919876543210"})


class FriendCreate(FriendBase):
    pass


class FriendResponse(FriendBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    net_balance: float = 0.0  # > 0 means friend owes user; < 0 means user owes friend

    model_config = ConfigDict(from_attributes=True)


class ParticipantCreate(BaseModel):
    friend_id: Optional[int] = None  # None if participant is User
    is_user: bool = False
    share_amount: Optional[float] = None  # If None, split equally


class ParticipantResponse(BaseModel):
    id: int
    friend_id: Optional[int] = None
    friend_name: Optional[str] = None
    is_user: bool
    share_amount: float

    model_config = ConfigDict(from_attributes=True)


class SplitTransactionCreate(BaseModel):
    title: str = Field(..., json_schema_extra={"example": "Soda & Snacks"})
    total_amount: float = Field(..., gt=0, json_schema_extra={"example": 20.0})
    transaction_type: str = Field("EXPENSE", json_schema_extra={"example": "EXPENSE"})  # EXPENSE, DIRECT_LOAN, SETTLEMENT
    paid_by_user: bool = True
    paid_by_friend_id: Optional[int] = None
    date: date_type = Field(default_factory=date_type.today)
    notes: Optional[str] = None
    participants: List[ParticipantCreate]
    log_as_personal_expense: bool = False
    category_id: Optional[int] = None


class SplitTransactionResponse(BaseModel):
    id: int
    title: str
    total_amount: float
    transaction_type: str
    paid_by_user: bool
    paid_by_friend_id: Optional[int] = None
    paid_by_name: str
    date: date_type
    notes: Optional[str] = None
    created_at: datetime
    participants: List[ParticipantResponse]

    model_config = ConfigDict(from_attributes=True)


class SettleUpRequest(BaseModel):
    friend_id: int
    amount: float = Field(..., gt=0)
    notes: Optional[str] = Field("Settled up", json_schema_extra={"example": "Paid via UPI"})

