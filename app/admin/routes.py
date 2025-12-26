import os
import uuid
from flask import (
    render_template, request, redirect, url_for, flash, current_app, send_from_directory
)
from werkzeug.utils import secure_filename
from flask_jwt_extended import get_jwt_identity
from ..extensions import db
from ..models import Document, ProjectAccess, User
from ..auth.guards import admin_required
from . import admin_bp

@admin_bp.get("/")
@admin_required
def dashboard():
    tab = (request.args.get("tab") or "projects").lower()  
    edit_id = request.args.get("edit")

    docs = Document.query.order_by(Document.updated_at.desc()).all()
    users = User.query.order_by(User.created_at.desc()).all()

    access_map = {}
    for row in ProjectAccess.query.all():
        access_map.setdefault(row.project_id, set()).add(row.user_id)

    edit_doc = None
    if tab == "projects" and edit_id and edit_id.isdigit():
        edit_doc = Document.query.get(int(edit_id))

    return render_template(
        "admin_portal.html",
        tab=tab,
        docs=docs,
        users=users,
        edit_doc=edit_doc,
        access_map=access_map, 
    )



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
        return redirect(url_for("admin.upload_page", tab="projects"))

    if not file or file.filename == "":
        flash("Please choose a file", "error")
        return redirect(url_for("admin.upload_page", tab="projects"))

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
    return redirect(url_for("admin.dashboard", tab="projects"))

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
    return redirect(url_for("admin.dashboard", tab="projects"))

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
    return redirect(url_for("admin.dashboard", tab="projects"))

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
    
@admin_bp.post("/projects/<int:doc_id>/access/grant")
@admin_required
def grant_project_access(doc_id: int):
    user_id = request.form.get("user_id", "").strip()

    if not user_id.isdigit():
        flash("Invalid user.", "error")
        return redirect(url_for("admin.dashboard", tab="projects"))

    user_id = int(user_id)

    # ensure project + user exist
    Document.query.get_or_404(doc_id)
    User.query.get_or_404(user_id)

    exists = ProjectAccess.query.filter_by(project_id=doc_id, user_id=user_id).first()
    if exists:
        flash("Access already exists.", "info")
        return redirect(url_for("admin.dashboard", tab="projects"))

    db.session.add(ProjectAccess(project_id=doc_id, user_id=user_id))
    db.session.commit()

    flash("Access granted.", "success")
    return redirect(url_for("admin.dashboard", tab="projects"))


@admin_bp.post("/projects/<int:doc_id>/access/revoke")
@admin_required
def revoke_project_access(doc_id: int):
    user_id = request.form.get("user_id", "").strip()
    if not user_id.isdigit():
        flash("Invalid user.", "error")
        return redirect(url_for("admin.dashboard", tab="projects"))

    user_id = int(user_id)

    row = ProjectAccess.query.filter_by(project_id=doc_id, user_id=user_id).first()
    if not row:
        flash("Access not found.", "error")
        return redirect(url_for("admin.dashboard", tab="projects"))

    db.session.delete(row)
    db.session.commit()

    flash("Access revoked.", "success")
    return redirect(url_for("admin.dashboard", tab="projects"))


@admin_bp.get("/users/new")
@admin_required
def add_user_page():
    return render_template("admin_add_user.html")

@admin_bp.post("/users/new")
@admin_required
def add_user_submit():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    
    if not email or not password:
        flash("Email and password required", "error")
        return redirect(url_for("admin.dashboard", tab="users"))

    if User.query.filter_by(email=email).first():
        flash("User already exists.", "error")
        return redirect(url_for("admin.dashboard", tab="users"))
    
    requested_role = (request.form.get("role") or "user").strip().lower()
    if requested_role == "admin":
        flash("Admin creation is disabled.", "error")
        return redirect(url_for("admin.dashboard", tab="users"))
    role = "user"

    user = User(email=email, role=role)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    flash("User created.", "success")
    return redirect(url_for("admin.dashboard", tab="users"))


@admin_bp.post("/users/<int:user_id>/delete")
@admin_required
def delete_user(user_id: int):
    current_admin_id = int(get_jwt_identity())

    user = User.query.get_or_404(user_id)

    fixed_admin_email = (os.getenv("DEFAULT_ADMIN_EMAIL") or "").strip().lower()
    if fixed_admin_email and user.email.lower() == fixed_admin_email:
        flash("Default admin cannot be deleted.", "error")
        return redirect(url_for("admin.dashboard", tab="users"))

    if user.id == current_admin_id:
        flash("You cannot delete the account you're currently logged in with.", "error")
        return redirect(url_for("admin.dashboard", tab="users"))

    docs_count = Document.query.filter_by(uploaded_by=user.id).count()
    if docs_count > 0:
        flash("Cannot delete user: they have uploaded documents. Delete/reassign documents first.", "error")
        return redirect(url_for("admin.dashboard", tab="users"))

    db.session.delete(user)
    db.session.commit()

    flash("User deleted.", "success")
    return redirect(url_for("admin.dashboard", tab="users"))

