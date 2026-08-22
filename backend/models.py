from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    expenses = relationship("Expense", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("MonthlyReport", back_populates="user", cascade="all, delete-orphan")
    friends = relationship("Friend", back_populates="user", cascade="all, delete-orphan")
    split_transactions = relationship("SplitTransaction", back_populates="user", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    icon = Column(String, default="🏷️")
    is_default = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    user = relationship("User", back_populates="categories")
    expenses = relationship("Expense", back_populates="category", cascade="all, delete-orphan")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    amount = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    description = Column(String, nullable=True)
    raw_input = Column(String, nullable=True)
    date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    month = Column(String, nullable=False, index=True)  # YYYY-MM
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    total_amount = Column(Float, default=0.0)
    category_breakdown_json = Column(Text, nullable=True)  # JSON string
    ai_summary = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reports")


class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="friends")
    participants = relationship("SplitParticipant", back_populates="friend", cascade="all, delete-orphan")


class SplitTransaction(Base):
    __tablename__ = "split_transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    transaction_type = Column(String, default="EXPENSE")  # EXPENSE, DIRECT_LOAN, SETTLEMENT
    paid_by_user = Column(Boolean, default=True)
    paid_by_friend_id = Column(Integer, ForeignKey("friends.id"), nullable=True)
    date = Column(Date, nullable=False, default=date.today)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="split_transactions")
    paid_by_friend = relationship("Friend", foreign_keys=[paid_by_friend_id])
    participants = relationship("SplitParticipant", back_populates="transaction", cascade="all, delete-orphan")


class SplitParticipant(Base):
    __tablename__ = "split_participants"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("split_transactions.id"), nullable=False)
    is_user = Column(Boolean, default=False)
    friend_id = Column(Integer, ForeignKey("friends.id"), nullable=True)
    share_amount = Column(Float, nullable=False, default=0.0)

    transaction = relationship("SplitTransaction", back_populates="participants")
    friend = relationship("Friend", back_populates="participants")

