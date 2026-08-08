from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import extract, desc, or_

from backend.database import get_db
from backend.models import Expense, Category, User
from backend.schemas import ExpenseCreate, ExpenseResponse
from backend.auth import get_optional_current_user

router = APIRouter(prefix="/api/expenses", tags=["Expenses"])


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense_in: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Create a new expense entry linked to the current user."""
    user_id = current_user.id if current_user else None
    
    # Check category existence (global default or owned by user)
    category = db.query(Category).filter(
        Category.id == expense_in.category_id,
        or_(Category.user_id == None, Category.user_id == user_id)
    ).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {expense_in.category_id} not found."
        )

    expense = Expense(
        amount=expense_in.amount,
        category_id=expense_in.category_id,
        user_id=user_id,
        description=expense_in.description,
        raw_input=expense_in.raw_input,
        date=expense_in.date or date.today()
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("", response_model=List[ExpenseResponse])
def get_expenses(
    month: Optional[str] = Query(None, description="Filter by YYYY-MM"),
    category_id: Optional[int] = Query(None, description="Filter by Category ID"),
    search: Optional[str] = Query(None, description="Search description or raw input"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieve expense list scoped to current user."""
    user_id = current_user.id if current_user else None
    query = db.query(Expense).join(Category).filter(Expense.user_id == user_id)

    if month:
        try:
            year, month_num = map(int, month.split("-"))
            query = query.filter(
                extract("year", Expense.date) == year,
                extract("month", Expense.date) == month_num
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month format. Expected YYYY-MM."
            )

    if category_id:
        query = query.filter(Expense.category_id == category_id)

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            (Expense.description.ilike(search_fmt)) | (Expense.raw_input.ilike(search_fmt))
        )

    expenses = query.order_by(desc(Expense.date), desc(Expense.id)).offset(offset).limit(limit).all()
    return expenses


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Delete an expense entry owned by current user."""
    user_id = current_user.id if current_user else None
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.user_id == user_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found."
        )
    db.delete(expense)
    db.commit()
    return None
