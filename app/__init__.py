import os
from flask import Flask, request
from dotenv import load_dotenv
from flask_jwt_extended import decode_token
from .config import Config
from .extensions import db, migrate, jwt

def create_app():
    # Project root: /.../rbac_app
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(base_dir, ".env")
    load_dotenv(env_path)

    app = Flask(__name__)
    app.config.from_object(Config)

    # ✅ read env AFTER load_dotenv
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-me")

    # ✅ ONE source of truth (absolute path)
    app.config["UPLOAD_FOLDER"] = os.path.join(base_dir, "app", "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError(f"DATABASE_URL is missing in {env_path}")

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    @app.context_processor
    def inject_csrf_token():
        token = request.cookies.get("access_token_cookie")
        if not token:
            return {"jwt_csrf": None}
        try:
            return {"jwt_csrf": decode_token(token).get("csrf")}
        except Exception:
            return {"jwt_csrf": None}

    from .auth.routes import auth_bp
    from .admin.routes import admin_bp
    from .user.routes import user_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(user_bp, url_prefix="/user")

    return app
