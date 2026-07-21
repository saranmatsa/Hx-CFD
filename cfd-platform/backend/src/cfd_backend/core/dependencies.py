"""
Dependency injection and service container for CFD Backend.

Provides FastAPI dependency injection for database, Redis, Celery,
and external service clients with proper lifecycle management.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from cfd_backend.core.config import Settings, get_settings
from cfd_backend.core.logging import get_logger
from cfd_backend.services.engine_registry import EngineRegistry
from cfd_backend.services.workflow_service import LocalWorkflowService

logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    @property
    def engine(self) -> AsyncEngine:
        """Get or create the async engine."""
        if self._engine is None:
            self._engine = create_async_engine(
                self.settings.database_url,
                echo=self.settings.database_echo,
                poolclass=NullPool if self.settings.is_development else None,
                pool_pre_ping=True,
            )
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create the session factory."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
        return self._session_factory
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        from cfd_backend.models.base import Base
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


class RedisManager:
    """Manages Redis connections."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None
    
    @property
    def client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._pool = redis.ConnectionPool.from_url(
                self.settings.redis_url,
                max_connections=self.settings.redis_max_connections,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)
        return self._client
    
    async def close(self) -> None:
        """Close Redis connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
    
    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            return await self.client.ping()
        except Exception:
            return False


class CeleryManager:
    """Manages Celery application."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._app = None
    
    @property
    def app(self):
        """Get or create Celery app."""
        if self._app is None:
            from celery import Celery
            self._app = Celery("cfd_backend")
            self._app.conf.update(
                broker_url=self.settings.celery_broker_url,
                result_backend=self.settings.celery_result_backend,
                task_serializer=self.settings.celery_task_serializer,
                result_serializer=self.settings.celery_result_serializer,
                accept_content=self.settings.celery_accept_content,
                timezone=self.settings.celery_timezone,
                enable_utc=self.settings.celery_enable_utc,
                task_track_started=True,
                task_time_limit=3600,
                worker_prefetch_multiplier=1,
            )
        return self._app


class ExternalToolsManager:
    """Manages external tool detection and validation."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._openfoam_version: Optional[str] = None
        self._gmsh_version: Optional[str] = None
        self._paraview_version: Optional[str] = None
    
    async def detect_openfoam(self) -> Optional[str]:
        """Detect OpenFOAM installation and version."""
        import subprocess
        import os
        
        # Try configured path first
        if self.settings.openfoam_path:
            bashrc = self.settings.openfoam_path / "etc" / "bashrc"
            if bashrc.exists():
                try:
                    result = await asyncio.create_subprocess_exec(
                        "bash", "-c", f"source {bashrc} && foamVersion",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, _ = await result.communicate()
                    if result.returncode == 0:
                        version = stdout.decode().strip()
                        self._openfoam_version = version
                        return version
                except Exception as e:
                    logger.warning("OpenFOAM detection failed", path=str(self.settings.openfoam_path), error=str(e))
        
        # Try common locations
        common_paths = [
            Path("/opt/openfoam"),
            Path("/usr/lib/openfoam"),
            Path("C:/Program Files/OpenFOAM"),
            Path("C:/OpenFOAM"),
        ]
        
        for path in common_paths:
            bashrc = path / "etc" / "bashrc"
            if bashrc.exists():
                try:
                    result = await asyncio.create_subprocess_exec(
                        "bash", "-c", f"source {bashrc} && foamVersion",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, _ = await result.communicate()
                    if result.returncode == 0:
                        version = stdout.decode().strip()
                        self._openfoam_version = version
                        return version
                except Exception:
                    continue
        
        return None
    
    async def detect_gmsh(self) -> Optional[str]:
        """Detect Gmsh installation and version."""
        import subprocess
        
        gmsh_cmd = str(self.settings.gmsh_path) if self.settings.gmsh_path else "gmsh"
        
        try:
            result = await asyncio.create_subprocess_exec(
                gmsh_cmd, "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()
            if result.returncode == 0:
                version = stdout.decode().strip()
                self._gmsh_version = version
                return version
        except Exception as e:
            logger.warning("Gmsh detection failed", error=str(e))
        
        return None
    
    async def detect_paraview(self) -> Optional[str]:
        """Detect ParaView installation and version."""
        import subprocess
        
        pv_cmd = str(self.settings.paraview_path) if self.settings.paraview_path else "pvpython"
        
        try:
            result = await asyncio.create_subprocess_exec(
                pv_cmd, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()
            if result.returncode == 0:
                version = stdout.decode().strip()
                self._paraview_version = version
                return version
        except Exception as e:
            logger.warning("ParaView detection failed", error=str(e))
        
        return None
    
    async def detect_all(self) -> dict:
        """Detect all external tools."""
        return {
            "openfoam": await self.detect_openfoam(),
            "gmsh": await self.detect_gmsh(),
            "paraview": await self.detect_paraview(),
        }
    
    @property
    def openfoam_version(self) -> Optional[str]:
        return self._openfoam_version
    
    @property
    def gmsh_version(self) -> Optional[str]:
        return self._gmsh_version
    
    @property
    def paraview_version(self) -> Optional[str]:
        return self._paraview_version


class ServiceContainer:
    """Main service container for dependency injection."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.db = DatabaseManager(self.settings)
        self.redis = RedisManager(self.settings)
        self.celery = CeleryManager(self.settings)
        self.tools = ExternalToolsManager(self.settings)
        self.engines = EngineRegistry(self.settings)
        self.workflow = LocalWorkflowService(self.settings, self.engines)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all services."""
        if self._initialized:
            return
        
        logger.info("Initializing services")
        
        # Initialize database
        await self.db.create_tables()
        logger.info("Database initialized")

        # The managed desktop process exposes only the private workflow API.
        # That workflow is intentionally local-first and uses
        # ``EngineRegistry`` below as its single source of truth for tool
        # availability.  Redis/Celery and the legacy ExternalToolsManager are
        # not in that request path, so probing an unavailable Redis server or
        # repeating executable discovery only delays every HX CFD launch.
        # Keep those probes for the full, non-desktop REST application where
        # the legacy services can still depend on them.
        managed_desktop = os.environ.get("CFD_PLATFORM_TAURI") == "1"
        if managed_desktop:
            logger.info(
                "Skipping optional legacy infrastructure probes for managed desktop workflow"
            )
        else:
            # Check Redis
            if await self.redis.ping():
                logger.info("Redis connected")
            else:
                logger.warning("Redis not available")

            # Detect external tools for legacy API consumers.  Desktop
            # workflow requests use EngineRegistry directly below.
            tools = await self.tools.detect_all()
            logger.info("External tools detected", tools=tools)

        engine_inventory = await self.engines.inventory(refresh=True)
        unavailable_engines = [
            engine["id"] for engine in engine_inventory if engine["status"] == "unavailable"
        ]
        logger.info(
            "Engineering engine inventory initialized",
            available=len(engine_inventory) - len(unavailable_engines),
            unavailable=unavailable_engines,
        )
        
        self._initialized = True
        logger.info("All services initialized")
    
    async def shutdown(self) -> None:
        """Shutdown all services."""
        logger.info("Shutting down services")
        
        await self.db.close()
        await self.redis.close()
        
        self._initialized = False
        logger.info("Services shut down")

    async def is_ready(self) -> bool:
        """Return local service readiness without requiring Redis or cloud access."""
        return self._initialized
    
    @asynccontextmanager
    async def lifespan(self) -> AsyncGenerator["ServiceContainer", None]:
        """Lifespan context manager for FastAPI."""
        await self.initialize()
        try:
            yield self
        finally:
            await self.shutdown()


# Global service container instance
_service_container: Optional[ServiceContainer] = None


def get_service_container() -> ServiceContainer:
    """Get the global service container."""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer()
    return _service_container


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    container = get_service_container()
    async with container.db.session() as session:
        yield session


async def get_redis_client() -> redis.Redis:
    """FastAPI dependency for Redis client."""
    container = get_service_container()
    return container.redis.client


def get_settings_dependency() -> Settings:
    """FastAPI dependency for settings."""
    return get_settings()


def get_tools_manager() -> ExternalToolsManager:
    """FastAPI dependency for external tools manager."""
    container = get_service_container()
    return container.tools
