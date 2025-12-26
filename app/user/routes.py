import os
from flask import render_template, current_app, send_file, send_from_directory, abort
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from ..models import Document
from ..auth.guards import login_required
from . import user_bp

@user_bp.get("/")
@login_required
def home():
    role = get_jwt().get("role")
    if role != "user":
        # admins shouldn't use user home
        return abort(403)

    docs = Document.query.order_by(Document.updated_at.desc()).all()
    return render_template("user_home.html", docs=docs)

@user_bp.get("/doc/<int:doc_id>/download")
@login_required
def download(doc_id: int):
    verify_jwt_in_request()
    if get_jwt().get("role") != "user":
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
    
    
