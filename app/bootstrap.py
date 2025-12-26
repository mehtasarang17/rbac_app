import os
from sqlalchemy import text
from werkzeug.security import generate_password_hash

from .extensions import db


def ensure_default_admin():
    email = (os.getenv("DEFAULT_ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("DEFAULT_ADMIN_PASSWORD") or ""

    # Don't crash during migrations/startup
    if not email or not password:
        return

    try:
        with db.engine.begin() as conn:
            # 1) If users table doesn't exist yet, skip
            users_table_exists = conn.execute(text("""
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.tables
                  WHERE table_schema='public' AND table_name='users'
                )
            """)).scalar()

            if not users_table_exists:
                return

            # 2) Check if admin user exists (ONLY select existing columns!)
            row = conn.execute(
                text("SELECT id, role FROM users WHERE email = :email LIMIT 1"),
                {"email": email},
            ).fetchone()

            if row:
                # enforce role admin
                if row.role != "admin":
                    conn.execute(
                        text("UPDATE users SET role = 'admin' WHERE id = :id"),
                        {"id": row.id},
                    )

                # 3) If new column exists after migration, optionally set it
                col_exists = conn.execute(text("""
                    SELECT EXISTS (
                      SELECT 1
                      FROM information_schema.columns
                      WHERE table_schema='public'
                        AND table_name='users'
                        AND column_name='can_create_projects'
                    )
                """)).scalar()

                if col_exists:
                    conn.execute(
                        text("UPDATE users SET can_create_projects = TRUE WHERE id = :id"),
                        {"id": row.id},
                    )

                return

            # 4) Insert default admin (columns that definitely exist in your old schema)
            password_hash = generate_password_hash(password)
            conn.execute(
                text("""
                    INSERT INTO users (email, password_hash, role)
                    VALUES (:email, :password_hash, 'admin')
                """),
                {"email": email, "password_hash": password_hash},
            )

            # If column exists (after migration), set it too
            col_exists = conn.execute(text("""
                SELECT EXISTS (
                  SELECT 1
                  FROM information_schema.columns
                  WHERE table_schema='public'
                    AND table_name='users'
                    AND column_name='can_create_projects'
                )
            """)).scalar()

            if col_exists:
                conn.execute(
                    text("UPDATE users SET can_create_projects = TRUE WHERE email = :email"),
                    {"email": email},
                )

    except Exception:
        # DB might be unreachable or in flux during migration; don't block app startup
        return
