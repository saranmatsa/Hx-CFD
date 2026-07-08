"""
CFD Platform - Main FastAPI Application Entry Point

A local-first AI-assisted engineering platform for CFD/CAD/Meshing/Optimization/Visualization.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.database import init_db, get_db
from backend.api.v1.router import router as api_v1_router
from backend.websocket.manager import websocket_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    print("Starting CFD Platform...")
    
    # Initialize database
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization warning: {e}")
    
    # Initialize Celery
    try:
        from celery_app import celery_app
        print(f"Celery app initialized: {celery_app.main}")
    except Exception as e:
        print(f"Celery initialization warning: {e}")
    
    print("CFD Platform started successfully")
    
    yield
    
    # Shutdown
    print("Shutting down CFD Platform...")


# Create FastAPI application
app = FastAPI(
    title="CFD Platform API",
    description="Local-first AI-assisted engineering platform for CFD/CAD/Meshing/Optimization/Visualization",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "cfd-platform"
    }


# Readiness check endpoint
@app.get("/api/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check database connection
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    try:
        # Check Redis connection
        from core.config import settings
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    return {
        "status": "ready" if db_status == "connected" else "degraded",
        "database": db_status,
        "redis": redis_status,
    }


# Include API v1 router
app.include_router(api_v1_router, prefix="/api/v1")


# WebSocket endpoint for real-time updates
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time updates."""
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages
            try:
                import json
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "subscribe":
                    channel = message.get("channel")
                    if channel:
                        await websocket_manager.subscribe(websocket, channel)
                        await websocket.send_json({
                            "type": "subscribed",
                            "channel": channel
                        })
                elif message.get("type") == "unsubscribe":
                    channel = message.get("channel")
                    if channel:
                        await websocket_manager.unsubscribe(websocket, channel)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "channel": channel
                        })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )