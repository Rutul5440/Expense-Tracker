from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database import get_db
from backend.models import Category, User
from backend.schemas import CategoryCreate, CategoryResponse
from backend.auth import get_optional_current_user

router = APIRouter(prefix="/api/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse])
def get_categories(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Fetch global default categories plus custom categories created by current user."""
    user_id = current_user.id if current_user else None
    return db.query(Category).filter(
        or_(Category.user_id == None, Category.user_id == user_id)
    ).order_by(Category.id.asc()).all()


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Create a new custom expense category for current user."""
    user_id = current_user.id if current_user else None
    name_clean = category_in.name.strip()

    existing = db.query(Category).filter(
        Category.name.ilike(name_clean),
        or_(Category.user_id == None, Category.user_id == user_id)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{name_clean}' already exists."
        )

    category = Category(
        name=name_clean,
        icon=category_in.icon or "🏷️",
        is_default=False,
        user_id=user_id
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
