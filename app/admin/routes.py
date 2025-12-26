import os
import uuid
from flask import (
    render_template, request, redirect, url_for, flash, current_app, send_from_directory
)
from werkzeug.utils import secure_filename
from flask_jwt_extended import get_jwt_identity
from ..extensions import db
from ..models import Document, User
from ..auth.guards import admin_required
from . import admin_bp

@admin_bp.get("/")
@admin_required
def dashboard():
    docs = Document.query.order_by(Document.updated_at.desc()).all()
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_dashboard.html", docs=docs, users=users)

@admin_bp.get("/upload")
@admin_required
def upload_page():
    return render_template("admin_upload.html")

@admin_bp.post("/upload")
@admin_required
def upload_submit():
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    file = request.files.get("file")

    if not title:
        flash("Title is required", "error")
        return redirect(url_for("admin.upload_page"))

    if not file or file.filename == "":
        flash("Please choose a file", "error")
        return redirect(url_for("admin.upload_page"))

    orig = secure_filename(file.filename)
    stored = f"{uuid.uuid4().hex}_{orig}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored)
    file.save(path)

    doc = Document(
        title=title,
        description=description if description else None,
        stored_filename=stored,
        original_filename=orig,
        mime_type=file.mimetype,
        uploaded_by=int(get_jwt_identity()),
    )
    db.session.add(doc)
    db.session.commit()

    flash("Document uploaded!", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.get("/doc/<int:doc_id>/edit")
@admin_required
def edit_doc_page(doc_id: int):
    doc = Document.query.get_or_404(doc_id)
    return render_template("admin_edit_doc.html", doc=doc)

@admin_bp.post("/doc/<int:doc_id>/edit")
@admin_required
def edit_doc_submit(doc_id: int):
    doc = Document.query.get_or_404(doc_id)
    doc.title = (request.form.get("title") or doc.title).strip()
    doc.description = (request.form.get("description") or "").strip() or None
    db.session.commit()
    flash("Document updated.", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.post("/doc/<int:doc_id>/delete")
@admin_required
def delete_doc(doc_id: int):
    doc = Document.query.get_or_404(doc_id)

    # remove file from disk
    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.stored_filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(doc)
    db.session.commit()
    flash("Document deleted.", "success")
    return redirect(url_for("admin.dashboard"))

@admin_bp.get("/doc/<int:doc_id>/download")
@admin_required
def admin_download(doc_id: int):
    doc = Document.query.get_or_404(doc_id)
    return send_from_directory(
        directory=current_app.config["UPLOAD_FOLDER"],
        path=doc.stored_filename,
        as_attachment=True,
        download_name=doc.original_filename,
    )

@admin_bp.get("/users/new")
@admin_required
def add_user_page():
    return render_template("admin_add_user.html", creating_admin=False)

@admin_bp.post("/users/new")
@admin_required
def add_user_submit():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not email or not password:
        flash("Email and password required", "error")
        return redirect(url_for("admin.add_user_page"))

    if User.query.filter_by(email=email).first():
        flash("User already exists.", "error")
        return redirect(url_for("admin.add_user_page"))

    user = User(email=email, role="user")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash("User created.", "success")
    return redirect(url_for("admin.dashboard"))
