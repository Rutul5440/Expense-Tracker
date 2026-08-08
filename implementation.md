# Smart Expense Tracker — Implementation Plan

## 1. Project Overview

A personal expense tracker that:
- Lets a user log expenses across all basic human-need categories (food, housing, health, transport, etc.)
- Auto-categorizes free-text entries using Generative AI (e.g. "swiggy order 450" → Food & Dining)
- Generates a monthly report/dashboard automatically at month-end (category-wise + overall totals)
- Provides an AI-generated plain-English monthly summary/insight ("Food spend rose 30% this month")
- Works as a fully responsive web app — usable and good-looking on an Android phone browser, not just desktop

This is a full-stack personal project: backend + database + GenAI integration + responsive frontend + automation. Good scope for a portfolio project — not too small, not unrealistically huge.

---

## 2. Tech Stack Decision

Two options were considered. Recommendation: **Option B**, because "very good UI, fully responsive on mobile" is a hard requirement, and Streamlit does not give full control over that.

### Option A — Streamlit (fast, limited UI control)
- Pros: Extremely fast to build, good for internal tools/demos
- Cons: Mobile responsiveness is basic; limited custom CSS/layout control; UI will look "toolish," not "product-like"
- Use this only if you want a quick MVP in 1–2 days and don't mind so-so mobile polish

### Option B — FastAPI + Tailwind CSS + Vanilla JS (Recommended)
- **Backend:** FastAPI (Python) — REST API, serves data, handles GenAI calls, scheduled jobs
- **Database:** SQLite via SQLAlchemy — file-based, zero setup, fine for personal/single-user scale
- **Frontend:** HTML + Tailwind CSS (mobile-first, fully responsive by design) + vanilla JS (or lightweight Alpine.js for interactivity) + Chart.js for graphs
- **Why Tailwind:** mobile-first utility classes make "looks good on Android phone" straightforward — you design for small screens first, then scale up
- **GenAI:** Claude API (or OpenAI) for categorization, natural-language parsing, and monthly summary generation
- **Automation:** APScheduler (in-process) or a system cron job to trigger month-end report generation
- **Charts:** Chart.js (lightweight, mobile-friendly, responsive canvas)

This gives you a real full-stack build: Python backend, proper database, REST API, GenAI, and a hand-designed responsive frontend — much stronger as a project than a Streamlit dashboard.

---

## 3. Expense Categories (Basic Human Needs Coverage)

| Category | Examples |
|---|---|
| Food & Dining | restaurants, food delivery, snacks |
| Groceries | supermarket, vegetables, daily essentials |
| Housing/Rent | rent, maintenance, repairs |
| Utilities | electricity, water, gas, internet, mobile recharge |
| Transport | fuel, cab, bus, metro, vehicle maintenance |
| Health & Medical | doctor, medicines, insurance, gym |
| Education | courses, books, fees |
| Entertainment | movies, subscriptions (Netflix/Spotify), outings |
| Shopping/Clothing | clothes, electronics, personal items |
| Savings/Investments | SIP, mutual funds, deposits |
| Loans/EMI | credit card, personal loan, EMIs |
| Miscellaneous | anything uncategorized/one-off |

Categories should be stored in DB (not hardcoded) so the user can add custom ones later.

---

## 4. Database Schema (SQLite)

```sql
-- categories table
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    icon TEXT,               -- for UI display
    is_default BOOLEAN DEFAULT 1
);

-- expenses table
CREATE TABLE expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    category_id INTEGER NOT NULL,
    description TEXT,
    raw_input TEXT,           -- original free-text entry, if used
    date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- monthly_reports table (cached generated reports)
CREATE TABLE monthly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,      -- 'YYYY-MM'
    total_amount REAL,
    category_breakdown_json TEXT,  -- {"Food": 4500, "Rent": 12000, ...}
    ai_summary TEXT,          -- GenAI-generated narrative
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. Backend API Endpoints (FastAPI)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/expenses` | Add new expense (supports free-text via `raw_input`) |
| GET | `/expenses` | List expenses (filterable by month/category) |
| DELETE | `/expenses/{id}` | Delete an expense |
| GET | `/categories` | List all categories |
| POST | `/categories` | Add custom category |
| GET | `/dashboard/{month}` | Get totals + category breakdown for a given month |
| GET | `/reports/{month}` | Get (or trigger) AI-generated monthly report |
| POST | `/ai/categorize` | Given free text, return suggested category + parsed amount/date |

---

## 6. GenAI Integration Points

1. **Smart entry parsing**
   Input: `"spent 200 on petrol yesterday"`
   AI extracts: `{ amount: 200, category: "Transport", date: <yesterday's date> }`
   → reduces manual form-filling to a single text box (big UX win, especially on mobile)

2. **Auto-categorization**
   Given a description, classify into one of the existing categories (with confidence, so user can override)

3. **Monthly narrative report**
   Given the month's totals + category breakdown, generate a short plain-English summary:
   e.g. "Your total spend this month was ₹28,400. Food & Dining was your biggest category, up 22% from last month. Consider reviewing your food delivery frequency."

Prompted via Claude/OpenAI API, called from the FastAPI backend (never directly from frontend, to protect API keys).

---

## 7. Monthly Automation Flow

1. Scheduled job (APScheduler, runs daily, checks if it's the 1st of the month) triggers on month-end/start
2. Pulls all expenses for the closed month from DB
3. Computes category-wise totals + overall total (Pandas groupby)
4. Sends summary data to GenAI → gets narrative report back
5. Stores result in `monthly_reports` table
6. Dashboard automatically shows this cached report when user opens the app — no need to regenerate every time

---

## 8. Dashboard & UI Design (Mobile-First, Fully Responsive)

**Design approach:**
- Build mobile-first with Tailwind CSS (`sm:`, `md:`, `lg:` breakpoints scale up from a phone-first base layout)
- Test primarily at 375–430px width (typical Android screen), then scale to tablet/desktop
- Use a bottom navigation bar on mobile (common Android UX pattern) vs. a sidebar on desktop
- Large touch targets (min 44px) for buttons — critical for phone usability
- Charts (Chart.js) set to `responsive: true, maintainAspectRatio: false` inside a fixed-height container so they resize properly on small screens

**Key screens:**
1. **Quick Add** — single text input ("spent 200 on groceries") + AI parses it; also a manual form fallback
2. **Dashboard (current month)** — total spend card, category-wise pie/donut chart, top 3 categories
3. **Monthly Report** — AI narrative summary + bar chart comparing to previous month
4. **History** — scrollable list of all expenses, filterable by category/date
5. **Categories** — manage/add custom categories

**Responsive behavior:**
- Mobile: single-column stacked cards, bottom nav
- Tablet/Desktop: 2–3 column grid, sidebar nav
- Charts and cards use `flex`/`grid` with Tailwind responsive classes — no fixed pixel widths

---

## 9. Suggested Build Order

1. Set up FastAPI + SQLite + SQLAlchemy models (categories, expenses)
2. Build core CRUD API endpoints
3. Build mobile-first Tailwind frontend: Quick Add screen + expense list
4. Add Pandas-based dashboard aggregation endpoint + Chart.js charts
5. Integrate GenAI for free-text parsing/categorization
6. Integrate GenAI for monthly narrative report generation
7. Add APScheduler automation for month-end report generation
8. Polish responsive UI across screen sizes (test on real Android device/Chrome DevTools mobile view)
9. (Optional) Export monthly report as PDF, add email delivery

---

## 10. Folder Structure

```
expense-tracker/
├── backend/
│   ├── main.py                # FastAPI app entrypoint
│   ├── models.py               # SQLAlchemy models
│   ├── database.py             # DB connection/session
│   ├── routes/
│   │   ├── expenses.py
│   │   ├── categories.py
│   │   ├── dashboard.py
│   │   └── ai.py
│   ├── services/
│   │   ├── ai_service.py       # GenAI calls (categorize, parse, summarize)
│   │   └── report_service.py   # Monthly aggregation + report generation
│   ├── scheduler.py            # APScheduler month-end job
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── quick-add.html
│   ├── dashboard.html
│   ├── history.html
│   ├── css/
│   │   └── styles.css          # Tailwind build output
│   └── js/
│       ├── api.js
│       ├── dashboard.js
│       └── charts.js
└── expense_tracker.db          # SQLite DB file
```

---

## 11. Is This a Good Project? (Honest Assessment)

Yes — this covers:
- Backend API design (FastAPI)
- Database modeling (SQLite/SQLAlchemy)
- Data aggregation (Pandas)
- Real GenAI integration with a clear purpose (not just a chatbot bolted on)
- Automation/scheduling
- Responsive frontend design — a skill many "AI project" portfolios skip entirely

This is a legitimately strong, well-rounded portfolio project. Not foolish at all — the combination of practical utility + AI + responsive UI + automation is exactly what stands out over generic tutorial-clone projects.
