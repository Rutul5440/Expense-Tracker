import json
from datetime import datetime, date
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import extract, func

from backend.models import Expense, Category, MonthlyReport
from backend.services.ai_service import generate_monthly_ai_summary


def get_previous_month(month_str: str) -> str:
    """Calculates previous month string in YYYY-MM format."""
    dt = datetime.strptime(month_str, "%Y-%m")
    if dt.month == 1:
        prev_dt = datetime(dt.year - 1, 12, 1)
    else:
        prev_dt = datetime(dt.year, dt.month - 1, 1)
    return prev_dt.strftime("%Y-%m")


def calculate_dashboard_data(db: Session, month_str: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Calculate real-time aggregated metrics for dashboard for a specific YYYY-MM month scoped by user_id."""
    year, month = map(int, month_str.split("-"))

    # Fetch expenses for target month
    expenses = (
        db.query(Expense)
        .join(Category)
        .filter(
            extract("year", Expense.date) == year,
            extract("month", Expense.date) == month,
            Expense.user_id == user_id
        )
        .all()
    )

    prev_month_str = get_previous_month(month_str)
    prev_year, prev_month = map(int, prev_month_str.split("-"))

    prev_expenses = (
        db.query(Expense)
        .filter(
            extract("year", Expense.date) == prev_year,
            extract("month", Expense.date) == prev_month,
            Expense.user_id == user_id
        )
        .all()
    )

    prev_total = sum(e.amount for e in prev_expenses)
    total_amount = sum(e.amount for e in expenses)
    expense_count = len(expenses)

    pct_change = 0.0
    if prev_total > 0:
        pct_change = round(((total_amount - prev_total) / prev_total) * 100, 2)

    category_breakdown = {}
    top_categories = []

    if expenses:
        # Convert to Pandas DataFrame for aggregation
        data = [
            {
                "amount": e.amount,
                "category_name": e.category.name if e.category else "Uncategorized",
                "icon": e.category.icon if e.category else "🏷️"
            }
            for e in expenses
        ]
        df = pd.DataFrame(data)

        grouped = df.groupby(["category_name", "icon"]).agg(
            amount=("amount", "sum"),
            count=("amount", "count")
        ).reset_index()

        grouped = grouped.sort_values(by="amount", ascending=False)

        for _, row in grouped.iterrows():
            cat_name = row["category_name"]
            amt = float(row["amount"])
            cnt = int(row["count"])
            pct = round((amt / total_amount * 100), 2) if total_amount > 0 else 0.0

            category_breakdown[cat_name] = round(amt, 2)
            top_categories.append({
                "category_name": cat_name,
                "icon": row["icon"],
                "amount": round(amt, 2),
                "percentage": pct,
                "count": cnt
            })

    return {
        "month": month_str,
        "total_amount": round(total_amount, 2),
        "prev_month_total": round(prev_total, 2),
        "percentage_change": pct_change,
        "expense_count": expense_count,
        "top_categories": top_categories,
        "category_breakdown": category_breakdown
    }


def get_or_generate_monthly_report(db: Session, month_str: str, force_refresh: bool = False, user_id: Optional[int] = None) -> MonthlyReport:
    """Fetch cached monthly report or generate AI report if missing/forced, scoped by user_id."""
    report = db.query(MonthlyReport).filter(
        MonthlyReport.month == month_str,
        MonthlyReport.user_id == user_id
    ).first()

    if report and not force_refresh:
        return report

    # Calculate metrics
    dashboard_data = calculate_dashboard_data(db, month_str, user_id=user_id)
    
    ai_narrative = generate_monthly_ai_summary(
        month=month_str,
        total_amount=dashboard_data["total_amount"],
        prev_month_total=dashboard_data["prev_month_total"],
        category_breakdown=dashboard_data["category_breakdown"],
        expense_count=dashboard_data["expense_count"]
    )

    breakdown_json = json.dumps(dashboard_data["category_breakdown"])

    if report:
        report.total_amount = dashboard_data["total_amount"]
        report.category_breakdown_json = breakdown_json
        report.ai_summary = ai_narrative
        report.generated_at = datetime.utcnow()
    else:
        report = MonthlyReport(
            month=month_str,
            user_id=user_id,
            total_amount=dashboard_data["total_amount"],
            category_breakdown_json=breakdown_json,
            ai_summary=ai_narrative,
            generated_at=datetime.utcnow()
        )
        db.add(report)

    db.commit()
    db.refresh(report)
    return report
