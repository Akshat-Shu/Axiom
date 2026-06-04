"""
Axiom Flask application factory.

Dependency Inversion Principle wiring happens here — the factory is the
only place that knows which concrete class satisfies each abstract interface.
All high-level engines receive injected abstractions; they never import
concrete classes directly.
"""
import logging
import sys
from flask import Flask, jsonify

from app.config import get_config
from app.extensions import db, migrate, cors


def create_app() -> Flask:
    app = Flask(__name__)
    cfg = get_config()
    app.config.from_object(cfg)

    _configure_logging(app)

    # ------------------------------------------------------------------
    # Initialise Flask extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # ------------------------------------------------------------------
    # DIP wiring: instantiate concrete implementations and inject them
    # into high-level engines via their abstract interfaces.
    #
    # To swap e.g. S3 for local disk, replace S3StorageService with a
    # LocalStorageService(StorageService) — the engines never notice.
    # ------------------------------------------------------------------
    with app.app_context():
        _wire_dependencies(app, cfg)

    # ------------------------------------------------------------------
    # Register API blueprints
    # ------------------------------------------------------------------
    from app.api import users, knowledge, calendar, scheduling

    app.register_blueprint(users.bp)
    app.register_blueprint(knowledge.bp)
    app.register_blueprint(calendar.bp)
    app.register_blueprint(scheduling.bp)

    # ------------------------------------------------------------------
    # Health-check endpoint
    # ------------------------------------------------------------------
    @app.get("/health")
    def health():
        llm_ok = app.llm_service.health_check()
        return jsonify({"status": "ok", "llm_reachable": llm_ok})

    # ------------------------------------------------------------------
    # Global error handlers
    # ------------------------------------------------------------------
    @app.errorhandler(404)
    def not_found(exc):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(exc):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(413)
    def payload_too_large(exc):
        return jsonify({"error": "Payload too large (max 20 MB)"}), 413

    @app.errorhandler(500)
    def internal_error(exc):
        app.logger.exception("Unhandled exception")
        return jsonify({"error": "Internal server error"}), 500

    return app


def _wire_dependencies(app: Flask, cfg) -> None:
    """
    Construct concrete implementations and inject them into engines.
    This is the single place in the codebase that references concrete classes.
    """
    from app.services.storage_s3 import S3StorageService
    from app.services.llm_openrouter import OpenRouterLLMService
    from app.repositories.knowledge_postgres import PostgreSQLKnowledgeRepository
    from app.repositories.calendar_postgres import PostgreSQLCalendarRepository
    from app.repositories.user_postgres import PostgreSQLUserRepository
    from app.engines.knowledge_engine import KnowledgeEngine
    from app.engines.scheduling_engine import SchedulingEngine
    from app.engines.calendar_engine import CalendarEngine

    # --- Concrete implementations (low-level modules) ---
    storage_service = S3StorageService(
        bucket_name=cfg.S3_BUCKET_NAME,
        region=cfg.AWS_REGION,
    )
    llm_service = OpenRouterLLMService(
        api_key=cfg.OPENROUTER_API_KEY,
        model=cfg.OPENROUTER_MODEL,
    )
    knowledge_repo = PostgreSQLKnowledgeRepository()
    calendar_repo = PostgreSQLCalendarRepository()
    user_repo = PostgreSQLUserRepository()

    # --- High-level engines (depend only on abstractions) ---
    knowledge_engine = KnowledgeEngine(
        storage=storage_service,
        llm=llm_service,
        repo=knowledge_repo,
        half_life_days=cfg.DECAY_HALF_LIFE_DAYS,
    )
    scheduling_engine = SchedulingEngine(
        llm=llm_service,
        calendar_repo=calendar_repo,
        knowledge_repo=knowledge_repo,
    )
    calendar_engine = CalendarEngine(repo=calendar_repo)

    # Attach to app for access from blueprints via current_app
    app.llm_service = llm_service
    app.knowledge_engine = knowledge_engine
    app.scheduling_engine = scheduling_engine
    app.calendar_engine = calendar_engine
    app.calendar_repo = calendar_repo
    app.user_repo = user_repo

    app.logger.info("Dependency injection complete")


def _configure_logging(app: Flask) -> None:
    level = logging.DEBUG if app.debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
