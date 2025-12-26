from flask import render_template, request, redirect, url_for, flash
from flask_jwt_extended import (
    create_access_token,
    set_access_cookies,
    unset_jwt_cookies,
    get_jwt,
    verify_jwt_in_request,
)
from ..extensions import db
from ..models import User
from . import auth_bp
from ..models import ProjectAccess
from flask_jwt_extended import get_csrf_token, decode_token
from flask import request

def get_csrf_from_jwt_cookie():
    token = request.cookies.get("access_token_cookie")
    if not token:
        return None
    decoded = decode_token(token)
    return decoded.get("csrf")


def _redirect_by_role(role: str):
    return redirect(url_for("admin.dashboard") if role == "admin" else url_for("user.home"))

@auth_bp.get("/")
def root():
    # app runs -> common login page
    return redirect(url_for("auth.login_page"))

@auth_bp.get("/login")
def login_page():
    return render_template("login.html")

@auth_bp.post("/login")
def login_submit():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        flash("Invalid email or password", "error")
        return redirect(url_for("auth.login_page"))

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "email": user.email},
    )
    resp = _redirect_by_role(user.role)
    set_access_cookies(resp, access_token)
    return resp

@auth_bp.get("/admin-signup")
def admin_signup_page():
    # public page to create FIRST admin (or additional admin if you want)
    return render_template("admin_add_user.html", creating_admin=True)

@auth_bp.post("/admin-signup")
def admin_signup_submit():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    if not email or not password:
        flash("Email and password required", "error")
        return redirect(url_for("auth.admin_signup_page"))

    if User.query.filter_by(email=email).first():
        flash("User already exists. Please login.", "error")
        return redirect(url_for("auth.login_page"))

    admin = User(email=email, role="admin")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    flash("Admin account created. Please login.", "success")
    return redirect(url_for("auth.login_page"))

@auth_bp.post("/logout")
def logout():
    resp = redirect(url_for("auth.login_page"))
    unset_jwt_cookies(resp)
    return resp

# Small helper for templates/redirect guarding
def current_user_role():
    verify_jwt_in_request()
    return get_jwt().get("role")
