from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import init_db
from app.api.routes import health, documents, qa, agent
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up — initialising database...")
    await init_db()
    print("Database ready.")
    yield
    
    # Shutdown
    print("Shutting down.")
    
app = FastAPI(
    title=settings.APP_NAME,
    description="AI Powered Indian Legal Document Intelligence System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(qa.router, prefix="/api/v1/qa", tags=["qa"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    
    