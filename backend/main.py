"""
FastAPI application for BAR Community Map Sharing Portal.
Main entry point for the backend API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from routes import auth, maps, ratings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting BAR Community Map Sharing Portal API")
    yield
    # Shutdown
    print("Shutting down BAR Community Map Sharing Portal API")


# Initialize FastAPI app
app = FastAPI(
    title="BAR Community Map Sharing Portal",
    description="API for sharing and managing Beyond All Reason (BAR) community maps",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "BAR Community Map Sharing Portal API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(auth.router, prefix="/api", tags=["authentication"])
app.include_router(maps.router, prefix="/api", tags=["maps"])
app.include_router(ratings.router, prefix="/api", tags=["ratings"])
