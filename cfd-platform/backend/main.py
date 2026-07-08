from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from api import projects, meshes, simulations, visualization, optimization, pipeline_routes
from infrastructure.service_manager.api.routes import router as service_manager_router
from infrastructure.service_manager.manager import get_service_manager
from core.config import settings
from core.logging import setup_logging
from core.database import engine, Base
from core.monitoring import get_metrics, MetricsMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    Base.metadata.create_all(bind=engine)
    
    # Auto-start services on application startup
    logger.info("Starting auto-start services...")
    sm = get_service_manager()
    await sm.start_all_auto_start()
    logger.info("Auto-start services complete")
    
    yield
    
    # Graceful shutdown
    logger.info("Shutting down services...")
    sm = get_service_manager()
    await sm.shutdown()
    logger.info("Shutdown complete")


app = FastAPI(
    title="CFD Platform API",
    description="Browser-based CFD simulation platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add monitoring middleware
app.add_middleware(MetricsMiddleware)

app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(meshes.router, prefix="/api/v1/meshes", tags=["meshes"])
app.include_router(simulations.router, prefix="/api/v1/simulations", tags=["simulations"])
app.include_router(visualization.router, prefix="/api/v1/visualization", tags=["visualization"])
app.include_router(optimization.router, prefix="/api/v1/optimization", tags=["optimization"])
app.include_router(pipeline_routes.router, tags=["pipeline"])
app.include_router(service_manager_router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)