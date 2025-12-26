import os
from flask import render_template, current_app, send_file, abort
from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)
from ..models import Document, ProjectAccess
from ..auth.guards import login_required
from . import user_bp


@user_bp.get("/")
@login_required
def home():
    verify_jwt_in_request()

    role = get_jwt().get("role")
    if role != "user":
        abort(403)

    user_id = int(get_jwt_identity())

    docs = (
        Document.query
        .join(ProjectAccess, ProjectAccess.project_id == Document.id)
        .filter(ProjectAccess.user_id == user_id)
        .order_by(Document.updated_at.desc())
        .all()
    )

    return render_template("user_home.html", docs=docs)


@user_bp.get("/doc/<int:doc_id>/download")
@login_required
def download(doc_id: int):
    verify_jwt_in_request()

    if get_jwt().get("role") != "user":
        abort(403)

    user_id = int(get_jwt_identity())

    allowed = ProjectAccess.query.filter_by(project_id=doc_id, user_id=user_id).first()
    if not allowed:
        abort(403)

    doc = Document.query.get_or_404(doc_id)

    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.stored_filename)
    if not os.path.exists(file_path):
        abort(404)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=doc.original_filename,
    )
