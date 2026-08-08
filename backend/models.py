from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    icon = Column(String, default="🏷️")
    is_default = Column(Boolean, default=True)

    expenses = relationship("Expense", back_populates="category", cascade="all, delete-orphan")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    description = Column(String, nullable=True)
    raw_input = Column(String, nullable=True)
    date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="expenses")


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    month = Column(String, nullable=False, index=True)  # YYYY-MM
    total_amount = Column(Float, default=0.0)
    category_breakdown_json = Column(Text, nullable=True)  # JSON string
    ai_summary = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
