import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ------------------------------------------------------------------ #
    # Paste your OpenRouter API key into .env as OPENROUTER_API_KEY=sk-... #
    # ------------------------------------------------------------------ #
    OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production")

    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://axiom_user:axiom_pass@localhost:5432/axiom",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    @property
    def SQLALCHEMY_ENGINE_OPTIONS(self) -> dict:
        uri = self.SQLALCHEMY_DATABASE_URI
        if uri.startswith("sqlite"):
            # SQLite doesn't support connection pooling options
            return {}
        return {"pool_pre_ping": True, "pool_recycle": 300}

    # S3 — credentials resolved automatically from EC2 instance IAM role
    S3_BUCKET_NAME: str = os.environ.get("S3_BUCKET_NAME", "tt-bootcamp-axiom")
    AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")

    MAX_CONTENT_LENGTH: int = 20 * 1024 * 1024  # 20 MB upload cap

    # Decay settings — set DECAY_HALF_LIFE_DAYS=0.01 in .env for a ~14-minute half-life (demo mode)
    DECAY_THRESHOLD: float = float(os.environ.get("DECAY_THRESHOLD", "0.7"))
    DECAY_HALF_LIFE_DAYS: float = float(os.environ.get("DECAY_HALF_LIFE_DAYS", "14"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


def get_config() -> Config:
    env = os.environ.get("FLASK_ENV", "development")
    return ProductionConfig() if env == "production" else DevelopmentConfig()
