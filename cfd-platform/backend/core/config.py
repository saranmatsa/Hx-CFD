from pydantic_settings import BaseSettings
from functools import lru_cache
import os
import secrets


def _generate_secret_key() -> str:
    """Generate a secure secret key."""
    return secrets.token_hex(32)


class Settings(BaseSettings):
    APP_NAME: str = "CFD Platform"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://cfduser:cfdpass@localhost:5432/cfddb"
    )
    
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    OPENFOAM_DIR: str = os.getenv("OPENFOAM_DIR", "/opt/OpenFOAM")
    GMSH_BIN: str = os.getenv("GMSH_BIN", "/usr/bin/gmsh")
    FREECAD_BIN: str = os.getenv("FREECAD_BIN", "/usr/bin/freecad")
    PARAVIEW_BIN: str = os.getenv("PARAVIEW_BIN", "/usr/bin/paraview")
    
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Security - Generate secure secret key if not provided via environment
    SECRET_KEY: str = os.getenv("SECRET_KEY") or _generate_secret_key()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    DATA_DIR: str = os.getenv("DATA_DIR", "/data")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/data/uploads")
    PROJECTS_DIR: str = os.getenv("PROJECTS_DIR", "/data/projects")
    TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp/cfd")
    
    # AI Provider API Keys
    NIM_API_KEY: str = os.getenv("NIM_API_KEY", "")
    NIM_BASE_URL: str = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LM_STUDIO_BASE_URL: str = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()