from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

class ProjectAccess(db.Model):
    __tablename__ = "project_access"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("project_id", "user_id", name="uq_project_user_access"),
    )

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(30), nullable=False)  # "admin" or "user"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    project_access = db.relationship("ProjectAccess", backref="user", cascade="all, delete-orphan")


class Document(db.Model):
    __tablename__ = "documents"
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    stored_filename = db.Column(db.String(500), nullable=False)   # uuid_original.ext
    original_filename = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(200), nullable=True)

    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    access_list = db.relationship("ProjectAccess", backref="project", cascade="all, delete-orphan")
