import os

class Config:
    SECRET_KEY = "dev-secret"

    # ✅ MUST be set or app should crash with a clear error
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me")

    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_ACCESS_COOKIE_PATH = "/"
    JWT_CSRF_CHECK_FORM = True
    JWT_CSRF_METHODS = ["POST", "PUT", "PATCH", "DELETE"]

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "app/uploads")
