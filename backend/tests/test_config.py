"""Config loading tests."""

from app.core.config import Settings, get_settings


def test_settings_loads_defaults():
    get_settings.cache_clear()
    s = Settings(_env_file=None)
    assert s.app_env == "dev"
    assert "postgresql" in s.database_url


def test_langfuse_not_ready_with_placeholder_keys():
    s = Settings(
        _env_file=None,
        langfuse_enabled=True,
        langfuse_public_key="pk-lf-xxxxxxxx",
        langfuse_secret_key="sk-lf-xxxxxxxx",
    )
    assert s.langfuse_ready is False
