import os
import sys
from contextlib import asynccontextmanager

# Add parent directory to sys.path so backend package imports resolve cleanly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import engine, Base, SessionLocal
from backend.models import Category
from backend.routes import expenses, categories, dashboard, ai
from backend.scheduler import start_scheduler, stop_scheduler

DEFAULT_CATEGORIES = [
    {"name": "Food & Dining", "icon": "🍔"},
    {"name": "Groceries", "icon": "🛒"},
    {"name": "Housing/Rent", "icon": "🏠"},
    {"name": "Utilities", "icon": "💡"},
    {"name": "Transport", "icon": "🚗"},
    {"name": "Health & Medical", "icon": "🩺"},
    {"name": "Education", "icon": "📚"},
    {"name": "Entertainment", "icon": "🎬"},
    {"name": "Shopping/Clothing", "icon": "🛍️"},
    {"name": "Savings/Investments", "icon": "📈"},
    {"name": "Loans/EMI", "icon": "💳"},
    {"name": "Miscellaneous", "icon": "📦"},
]


def seed_default_categories():
    """Seeds default human-need expense categories on first run."""
    db = SessionLocal()
    try:
        count = db.query(Category).count()
        if count == 0:
            print("[Main] Seeding default expense categories...")
            for cat_data in DEFAULT_CATEGORIES:
                cat = Category(name=cat_data["name"], icon=cat_data["icon"], is_default=True)
                db.add(cat)
            db.commit()
            print(f"[Main] Seeded {len(DEFAULT_CATEGORIES)} default categories.")
    except Exception as e:
        print(f"[Main] Error seeding categories: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    Base.metadata.create_all(bind=engine)
    seed_default_categories()
    try:
        start_scheduler()
    except Exception as e:
        print(f"[Main] Scheduler start warning: {e}")

    yield

    # Shutdown tasks
    try:
        stop_scheduler()
    except Exception as e:
        print(f"[Main] Scheduler stop warning: {e}")


app = FastAPI(
    title="Smart Expense Tracker API",
    description="Full-stack AI-powered personal expense management API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(expenses.router)
app.include_router(categories.router)
app.include_router(dashboard.router)
app.include_router(ai.router)

# Mount Frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
