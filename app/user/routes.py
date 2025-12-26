import os
from flask import (
    render_template,
    current_app,
    send_file,
    abort,
    request,
    redirect,
    url_for,
    flash,
)
from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)
from ..extensions import db
from ..models import Document, ProjectAccess
from ..auth.guards import login_required
from . import user_bp


def _require_user_role():
    verify_jwt_in_request()
    if get_jwt().get("role") != "user":
        abort(403)


def _get_perm_or_403(doc_id: int) -> ProjectAccess:
    user_id = int(get_jwt_identity())
    perm = ProjectAccess.query.filter_by(project_id=doc_id, user_id=user_id).first()
    if not perm or not perm.can_read:
        abort(403)
    return perm


@user_bp.get("/")
@login_required
def home():
    _require_user_role()
    user_id = int(get_jwt_identity())

    # ✅ only projects this user can read
    docs = (
        Document.query
        .join(ProjectAccess, ProjectAccess.project_id == Document.id)
        .filter(ProjectAccess.user_id == user_id, ProjectAccess.can_read.is_(True))
        .order_by(Document.updated_at.desc())
        .all()
    )
    perms = ProjectAccess.query.filter_by(user_id=user_id).all()
    perm_map = {p.project_id: p for p in perms}

    return render_template(
        "user_home.html",
        docs=docs,
        perm_map=perm_map
    )


@user_bp.get("/doc/<int:doc_id>/download")
@login_required
def download(doc_id: int):
    _require_user_role()

    # ✅ enforce read permission
    _get_perm_or_403(doc_id)

    doc = Document.query.get_or_404(doc_id)
    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.stored_filename)
    if not os.path.exists(file_path):
        abort(404)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=doc.original_filename,
    )


# -----------------------------
# USER EDIT (metadata only)
# -----------------------------
@user_bp.get("/doc/<int:doc_id>/edit")
@login_required
def edit_doc_page(doc_id: int):
    _require_user_role()
    perm = _get_perm_or_403(doc_id)

    if not perm.can_edit:
        abort(403)

    doc = Document.query.get_or_404(doc_id)
    return render_template("user_edit_doc.html", doc=doc)


@user_bp.post("/doc/<int:doc_id>/edit")
@login_required
def edit_doc_submit(doc_id: int):
    _require_user_role()
    perm = _get_perm_or_403(doc_id)

    if not perm.can_edit:
        abort(403)

    doc = Document.query.get_or_404(doc_id)

    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()

    if title:
        doc.title = title
    doc.description = description or None

    db.session.commit()
    flash("Project updated.", "success")
    return redirect(url_for("user.home"))


# -----------------------------
# USER DELETE
# -----------------------------
@user_bp.post("/doc/<int:doc_id>/delete")
@login_required
def delete_doc(doc_id: int):
    _require_user_role()
    perm = _get_perm_or_403(doc_id)

    if not perm.can_delete:
        abort(403)

    doc = Document.query.get_or_404(doc_id)

    # remove file from disk
    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.stored_filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # delete the project itself (ProjectAccess rows should be removed via FK cascade)
    db.session.delete(doc)
    db.session.commit()

    flash("Project deleted.", "success")
    return redirect(url_for("user.home"))
