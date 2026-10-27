"""Flask application factory. No database schema or UI in foundation stage."""
import logging

from flask import Flask, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import load_config
from app.extensions import db, login_manager, csrf, migrate
from app.routes.auth import bp as auth_bp
from app.routes.pages import bp as pages_bp
from app.routes.datasets import bp as datasets_bp
from app.routes.preprocessing import bp as preprocessing_bp
from app.routes.admin_datasets import bp as admin_datasets_bp
from app.routes.classification import bp as classification_bp
from app.routes.testing import bp as testing_bp
from app.cli import create_superadmin
from app import models  # register tables with SQLAlchemy metadata



def create_app():
    app = Flask(__name__)
    app.config.update(load_config())
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    @app.errorhandler(413)
    def upload_too_large(error):
        return jsonify(status="error", message="Berkas terlalu besar"), 413

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(datasets_bp)
    app.register_blueprint(preprocessing_bp)
    app.register_blueprint(admin_datasets_bp)
    app.register_blueprint(classification_bp)
    app.register_blueprint(testing_bp)
    app.cli.add_command(create_superadmin)

    @app.get("/health/db")
    def database_health():
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.warning("Database health check failed")
            return jsonify(status="unavailable"), 503
        return jsonify(status="ok"), 200

    app.logger.setLevel(logging.INFO)
    return app
