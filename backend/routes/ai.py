from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database import get_db
from backend.models import Category, User
from backend.schemas import NaturalLanguageInput, AIParseResponse
from backend.services.ai_service import parse_natural_language
from backend.auth import get_optional_current_user

router = APIRouter(prefix="/api/ai", tags=["GenAI Integration"])


@router.post("/parse", response_model=AIParseResponse)
def parse_expense_text(
    input_data: NaturalLanguageInput,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """Parse free text into structured expense data (amount, category, description, date)."""
    text = input_data.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    user_id = current_user.id if current_user else None

    # Fetch available categories for current user
    categories = db.query(Category).filter(
        or_(Category.user_id == None, Category.user_id == user_id)
    ).all()
    cat_names = [c.name for c in categories]

    parsed = parse_natural_language(text, cat_names)

    # Match category ID if possible
    cat_id = None
    matched_cat = db.query(Category).filter(
        Category.name.ilike(parsed["category_name"]),
        or_(Category.user_id == None, Category.user_id == user_id)
    ).first()

    if matched_cat:
        cat_id = matched_cat.id
        parsed["category_name"] = matched_cat.name
    else:
        # Fallback to Miscellaneous category if available
        misc_cat = db.query(Category).filter(Category.name == "Miscellaneous").first()
        if misc_cat:
            cat_id = misc_cat.id

    parsed["category_id"] = cat_id
    return AIParseResponse(**parsed)
