import os
import re
import json
from datetime import date, timedelta, datetime
from typing import Dict, Any, List, Optional

# Attempt to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try importing google.genai or fallback
GEMINI_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def _get_genai_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if GEMINI_AVAILABLE and api_key:
        try:
            return genai.Client(api_key=api_key)
        except Exception as e:
            print(f"[AIService] Failed to initialize Gemini Client: {e}")
            return None
    return None


CATEGORY_KEYWORDS = {
    "Food & Dining": [
        "swiggy", "zomato", "restaurant", "food", "pizza", "burger", "lunch", "dinner",
        "breakfast", "cafe", "coffee", "snack", "tea", "starbucks", "mcdonalds", "kfc",
        "dosa", "biryani", "eating out", "sweet", "bakery"
    ],
    "Groceries": [
        "groceries", "grocery", "supermarket", "vegetables", "veggies", "fruits", "milk",
        "blinkit", "zepto", "instamart", "bigbasket", "ration", "mart", "d-mart", "provisions"
    ],
    "Housing/Rent": [
        "rent", "housing", "maintenance", "society fee", "flat rent", "house rent", "brokerage", "landlord"
    ],
    "Utilities": [
        "electricity", "power bill", "water bill", "gas", "cylinder", "internet", "wifi",
        "broadband", "mobile recharge", "jio", "airtel", "vi", "utility", "trash"
    ],
    "Transport": [
        "petrol", "diesel", "fuel", "cab", "uber", "ola", "rapido", "auto", "bus",
        "metro", "train", "flight", "ticket", "taxi", "parking", "toll", "fastag", "vehicle service"
    ],
    "Health & Medical": [
        "doctor", "medicine", "pharmacy", "chemist", "hospital", "clinic", "gym", "fitness",
        "lab test", "health insurance", "dental", "medical", "blood test", "cult.fit"
    ],
    "Education": [
        "course", "udemy", "coursera", "book", "books", "school fee", "college fee",
        "tuition", "stationery", "exam fee", "learning", "subscription study"
    ],
    "Entertainment": [
        "movie", "cinema", "netflix", "spotify", "prime", "youtube", "game", "gaming",
        "party", "concert", "bookmyshow", "steam", "playstation", "outing", "club"
    ],
    "Shopping/Clothing": [
        "amazon", "flipkart", "myntra", "meesho", "clothes", "shoes", "shirt", "pants",
        "dress", "electronics", "laptop", "mobile", "gadget", "watch", "zara", "h&m"
    ],
    "Savings/Investments": [
        "sip", "mutual fund", "stock", "shares", "crypto", "deposit", "fd", "rd",
        "savings", "investment", "zerodha", "groww", "nps", "ppf"
    ],
    "Loans/EMI": [
        "emi", "credit card", "loan", "car emi", "home emi", "interest", "debt payoff"
    ]
}


def parse_natural_language_heuristic(text: str, categories_list: List[str]) -> Dict[str, Any]:
    """Fallback rule-based heuristic parsing for free text entries."""
    lowered = text.lower()

    # 1. Amount Extraction
    # Look for numbers with optional currency symbols: e.g. 450, 450.50, rs 450, 450 rs, $450, ₹450
    amount = 0.0
    amount_match = re.search(r'(?:₹|\$|rs\.?|inr)?\s*(\d+(?:\.\d{1,2})?)\s*(?:rs|rupees|inr|\$)?', lowered)
    if amount_match:
        try:
            amount = float(amount_match.group(1))
        except ValueError:
            amount = 0.0

    # 2. Date Extraction
    target_date = date.today()
    if "yesterday" in lowered:
        target_date = date.today() - timedelta(days=1)
    elif "day before yesterday" in lowered:
        target_date = date.today() - timedelta(days=2)
    elif "last night" in lowered or "this morning" in lowered:
        target_date = date.today()
    else:
        # Check for X days ago
        days_ago_match = re.search(r'(\d+)\s*days?\s*ago', lowered)
        if days_ago_match:
            days = int(days_ago_match.group(1))
            target_date = date.today() - timedelta(days=days)

    # 3. Category Categorization
    matched_category = "Miscellaneous"
    max_score = 0
    
    for cat_name, keywords in CATEGORY_KEYWORDS.items():
        if cat_name in categories_list:
            score = 0
            for kw in keywords:
                if kw in lowered:
                    score += 1
            if score > max_score:
                max_score = score
                matched_category = cat_name

    # 4. Description Cleaning
    cleaned_desc = text
    if amount_match:
        cleaned_desc = re.sub(r'(?:₹|\$|rs\.?|inr)?\s*\d+(?:\.\d{1,2})?\s*(?:rs|rupees|inr|\$)?', ' ', cleaned_desc, flags=re.IGNORECASE)
    
    cleaned_desc = re.sub(r'\b(yesterday|today|day before yesterday|last night|this morning|\d+\s*days?\s*ago|spent|paid|bought|for|on|rs|inr|rupees)\b', ' ', cleaned_desc, flags=re.IGNORECASE)
    cleaned_desc = re.sub(r'\s+', ' ', cleaned_desc).strip()

    
    if not cleaned_desc:
        cleaned_desc = text.strip()
    else:
        cleaned_desc = cleaned_desc.capitalize()


    return {
        "amount": amount,
        "category_name": matched_category,
        "description": cleaned_desc,
        "date": target_date.isoformat(),
        "confidence": 0.85 if max_score > 0 else 0.5,
        "is_ai": False,
        "raw_text": text
    }


def parse_natural_language(text: str, categories_list: List[str]) -> Dict[str, Any]:
    """Parse free text using Gemini API with intelligent fallback."""
    client = _get_genai_client()
    if not client:
        return parse_natural_language_heuristic(text, categories_list)

    today_str = date.today().isoformat()
    categories_str = ", ".join([f'"{c}"' for c in categories_list])

    prompt = f"""
You are an intelligent financial expense parser. Extract key expense information from the text input below.
Today's date is: {today_str}.
Available categories are: [{categories_str}]

Input text: "{text}"

Respond STRICTLY with a valid JSON object matching this schema:
{{
  "amount": number (positive numeric value),
  "category_name": string (must be one of the available categories, or "Miscellaneous"),
  "description": string (short clean summary of item/service),
  "date": string (YYYY-MM-DD format based on context like "yesterday", "2 days ago", or today),
  "confidence": number (between 0.0 and 1.0)
}}
Do NOT output markdown formatting like ```json or any explanations. Return only raw JSON.
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        response_text = response.text.strip()
        # Remove ```json wrappers if present
        cleaned_json = re.sub(r'^```json\s*', '', response_text)
        cleaned_json = re.sub(r'\s*```$', '', cleaned_json)

        data = json.loads(cleaned_json)
        
        # Validate category name match
        cat_name = data.get("category_name", "Miscellaneous")
        if cat_name not in categories_list:
            # Pick best fuzzy fallback
            cat_name = "Miscellaneous"

        return {
            "amount": float(data.get("amount", 0.0)),
            "category_name": cat_name,
            "description": data.get("description", text),
            "date": data.get("date", today_str),
            "confidence": float(data.get("confidence", 0.9)),
            "is_ai": True,
            "raw_text": text
        }
    except Exception as e:
        print(f"[AIService] Gemini API parsing failed or key invalid ({e}). Falling back to heuristic.")
        return parse_natural_language_heuristic(text, categories_list)


def generate_monthly_ai_summary(
    month: str,
    total_amount: float,
    prev_month_total: float,
    category_breakdown: Dict[str, float],
    expense_count: int
) -> str:
    """Generate plain-English narrative summary of monthly expenses."""
    client = _get_genai_client()

    # Heuristic fallback builder
    def build_heuristic_summary():
        if total_amount == 0 and expense_count == 0:
            return f"No expenses logged for {month}. You're all caught up!"

        diff = total_amount - prev_month_total
        pct = (diff / prev_month_total * 100) if prev_month_total > 0 else 0

        sorted_cats = sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)
        top_cat_text = ""
        if sorted_cats:
            top_cat, top_amt = sorted_cats[0]
            top_pct = (top_amt / total_amount * 100) if total_amount > 0 else 0
            top_cat_text = f" Your top category was **{top_cat}** at ₹{top_amt:,.2f} ({top_pct:.1f}% of total spend)."

        trend_text = ""
        if prev_month_total > 0:
            if diff > 0:
                trend_text = f" Total spending increased by **{pct:.1f}%** compared to last month (₹{prev_month_total:,.2f})."
            elif diff < 0:
                trend_text = f" Great job! Total spending decreased by **{abs(pct):.1f}%** compared to last month (₹{prev_month_total:,.2f})."
            else:
                trend_text = f" Spending remained flat compared to last month."

        return (
            f"In **{month}**, you logged a total of **{expense_count} expenses** amounting to **₹{total_amount:,.2f}**.{top_cat_text}{trend_text}"
            f" Keep tracking to maintain healthy financial habits!"
        )

    if not client:
        return build_heuristic_summary()

    prompt = f"""
You are a friendly personal financial advisor AI. Write a concise, engaging, plain-English monthly insight report (2-3 paragraphs max) based on the spending data for {month}.

Data:
- Month: {month}
- Total Spend: ₹{total_amount:,.2f}
- Previous Month Total Spend: ₹{prev_month_total:,.2f}
- Number of Transactions: {expense_count}
- Category Breakdown: {json.dumps(category_breakdown, indent=2)}

Provide actionable insights, highlight top categories, note month-over-month trend changes, and give a motivating tip. Format with markdown (bolding key numbers).
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"[AIService] Gemini narrative generation failed ({e}). Falling back to heuristic summary.")
        return build_heuristic_summary()
