from functools import wraps
import secrets
from flask import abort, current_app, g, session, request, redirect, url_for
from app.services.auth import get_user


def current_user():
    if "user_id" not in session: return None
    if not hasattr(g, "current_user"): g.current_user = get_user(current_app.config["DATABASE"], session["user_id"])
    return g.current_user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/") or request.is_json:
                return abort(401)

            return redirect(
                url_for(
                    "auth.login",
                    next=request.full_path
                )
            )

        return view(*args, **kwargs)

    return wrapped


def csrf_token():
    return session.setdefault("csrf_token", secrets.token_urlsafe(24))


def valid_csrf(token): return token and secrets.compare_digest(token, session.get("csrf_token", ""))