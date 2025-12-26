from functools import wraps
from flask import abort
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper
