"""
Core configuration module for CFD Backend.

Provides centralized configuration management using Pydantic Settings
with support for environment variables, config files, and validation.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "CFD Platform Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "tauri://localhost"],
        alias="CORS_ORIGINS"
    )
    
    # Paths
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    logs_dir: Path = Field(default=Path("./logs"), alias="LOGS_DIR")
    projects_dir: Path = Field(default=Path("./projects"), alias="PROJECTS_DIR")
    temp_dir: Path = Field(default=Path("./tmp"), alias="TEMP_DIR")
    cache_dir: Path = Field(default=Path("./cache"), alias="CACHE_DIR")
    
    # External tools (auto-detected or configured)
    freecad_path: Optional[Path] = Field(default=None, alias="FREECAD_PATH")
    openfoam_path: Optional[Path] = Field(default=None, alias="OPENFOAM_PATH")
    openfoam_version: str = Field(default="v2306", alias="OPENFOAM_VERSION")
    gmsh_path: Optional[Path] = Field(default=None, alias="GMSH_PATH")
    gmsh_version: str = Field(default="4.11.0", alias="GMSH_VERSION")
    cfmesh_path: Optional[Path] = Field(default=None, alias="CFMESH_PATH")
    paraview_path: Optional[Path] = Field(default=None, alias="PARAVIEW_PATH")
    paraview_version: str = Field(default="5.12.0", alias="PARAVIEW_VERSION")
    
    # Python environment
    python_executable: str = Field(default="python", alias="PYTHON_EXECUTABLE")
    venv_path: Optional[Path] = Field(default=None, alias="VENV_PATH")
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/cfd.db",
        alias="DATABASE_URL"
    )
    database_echo: bool = False
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_max_connections: int = 10
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: List[str] = ["json"]
    celery_timezone: str = "UTC"
    celery_enable_utc: bool = True
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")  # json or console
    log_file: Optional[Path] = Field(default=None, alias="LOG_FILE")
    log_max_bytes: int = 10_485_760  # 10MB
    log_backup_count: int = 5
    
    # Simulation
    max_concurrent_simulations: int = Field(default=2, alias="MAX_CONCURRENT_SIMULATIONS")
    simulation_timeout: int = Field(default=3600, alias="SIMULATION_TIMEOUT")  # seconds
    default_mesh_size: float = Field(default=0.01, alias="DEFAULT_MESH_SIZE")
    default_turbulence_model: str = Field(default="kOmegaSST", alias="DEFAULT_TURBULENCE_MODEL")
    
    # AI/ML
    physicsnemo_enabled: bool = Field(default=True, alias="PHYSICSNEMO_ENABLED")
    physicsnemo_model_path: Optional[Path] = Field(default=None, alias="PHYSICSNEMO_MODEL_PATH")
    physicsnemo_python: Optional[Path] = Field(default=None, alias="PHYSICSNEMO_PYTHON")
    physicsnemo_cfd_path: Optional[Path] = Field(default=None, alias="PHYSICSNEMO_CFD_PATH")
    cuda_visible_devices: str = Field(default="0", alias="CUDA_VISIBLE_DEVICES")
    
    # Optimization
    nevergrad_budget: int = Field(default=100, alias="NEVERGRAD_BUDGET")
    openmdao_max_iter: int = Field(default=50, alias="OPENMDAO_MAX_ITER")
    
    # Monitoring
    health_check_interval: int = Field(default=30, alias="HEALTH_CHECK_INTERVAL")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    prometheus_port: int = Field(default=9090, alias="PROMETHEUS_PORT")
    
    # Security
    secret_key: str = Field(default="dev-secret-change-in-production", alias="SECRET_KEY")
    api_key_header: str = Field(default="X-API-Key", alias="API_KEY_HEADER")
    allowed_api_keys: List[str] = Field(default=[], alias="ALLOWED_API_KEYS")
    
    # Token expiration
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Auth settings
    allow_registration: bool = Field(default=True, alias="ALLOW_REGISTRATION")
    require_email_verification: bool = Field(default=False, alias="REQUIRE_EMAIL_VERIFICATION")
    max_login_attempts: int = Field(default=5, alias="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=15, alias="LOCKOUT_DURATION_MINUTES")
    
    @field_validator("data_dir", "logs_dir", "projects_dir", "temp_dir", "cache_dir", mode="before")
    @classmethod
    def expand_paths(cls, v: str | Path) -> Path:
        """Expand user and environment variables in paths."""
        if isinstance(v, str):
            v = os.path.expanduser(os.path.expandvars(v))
        return Path(v).resolve()
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("allowed_api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, v: str | List[str]) -> List[str]:
        """Parse API keys from string or list."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev", "local")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ("production", "prod")
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        for dir_path in [
            self.data_dir,
            self.logs_dir,
            self.projects_dir,
            self.temp_dir,
            self.cache_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
