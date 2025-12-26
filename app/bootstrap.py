import os
from werkzeug.security import generate_password_hash
from .extensions import db
from .models import User  # adjust if your model name differs

def ensure_default_admin():
    email = os.getenv("DEFAULT_ADMIN_EMAIL")
    password = os.getenv("DEFAULT_ADMIN_PASSWORD")

    if not email or not password:
        raise RuntimeError("Set DEFAULT_ADMIN_EMAIL and DEFAULT_ADMIN_PASSWORD in .env")

    existing = User.query.filter_by(email=email).first()
    if existing:
        # If exists but role isn't admin, enforce it
        if existing.role != "admin":
            existing.role = "admin"
            db.session.commit()
        return

    admin = User(
        email=email,
        password_hash=generate_password_hash(password),
        role="admin",
    )
    db.session.add(admin)
    db.session.commit()
