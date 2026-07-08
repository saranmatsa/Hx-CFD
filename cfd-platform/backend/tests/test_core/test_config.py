from core.config import settings


@pytest.mark.unit
def test_settings_loaded():
    """Test that settings are loaded correctly."""
    assert hasattr(settings, "DATABASE_URL")
    assert hasattr(settings, "CORS_ORIGINS")
    assert hasattr(settings, "REDIS_URL")


@pytest.mark.unit
def test_settings_defaults():
    """Test that settings have sensible defaults."""
    assert settings.CORS_ORIGINS is not None
    assert isinstance(settings.CORS_ORIGINS, list)
