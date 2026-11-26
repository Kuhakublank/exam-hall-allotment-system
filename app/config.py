"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration shared across environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-fallback-change-in-env")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


class DevelopmentConfig(Config):
    """Local development configuration using PostgreSQL."""

    DEBUG = True


class TestingConfig(Config):
    """Isolated testing configuration (uses TEST_DATABASE_URL or in-memory SQLite)."""

    TESTING = True
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")


class ProductionConfig(Config):
    """Production configuration requiring explicit SECRET_KEY and DATABASE_URL."""

    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
