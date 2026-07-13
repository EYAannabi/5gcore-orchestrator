"""
5G Core Orchestrator - FastAPI Application
Cloud-Native orchestration platform for Free5GC Kubernetes deployments
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routes import pods, deploy, logs, settings, lifecycle, validations, history

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="5G Core Orchestrator",
    description="Cloud-Native Automation Platform for Free5GC Kubernetes Deployments",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
logger.info("Registering API routes")
app.include_router(pods.router, prefix="/api")
app.include_router(deploy.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(lifecycle.router, prefix="/api")
app.include_router(validations.router, prefix="/api")
app.include_router(history.router, prefix="/api")

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Root endpoint - serve frontend
@app.get("/", tags=["System"])
async def root():
    """Serve the main operator interface"""
    return FileResponse("app/static/index.html")


@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "5G Core Orchestrator",
        "version": "2.0.0"
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("5G Core Orchestrator starting up")
    logger.info("FastAPI documentation available at /api/docs")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("5G Core Orchestrator shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
