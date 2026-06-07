from fastapi import APIRouter
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "ok", "service": "legal-intelligence-api"}

@router.get("/health/db")
async def db_health_check():
    """Check database connection"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}