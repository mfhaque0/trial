from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from app.routes.common import current_user, csrf_token, valid_csrf
from app.services.auth import authenticate, register

auth = Blueprint("auth", __name__)

@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user(): return redirect(url_for("workspace.dashboard"))
    if request.method == "POST":
        if not valid_csrf(request.form.get("csrf_token")): flash("Your form expired. Please try again.", "error")
        else:
            try:
                user_id = register(current_app.config["DATABASE"], request.form.get("display_name", ""), request.form.get("email", ""), request.form.get("password", ""))
                session.clear(); session["user_id"] = user_id; csrf_token(); return redirect(url_for("workspace.dashboard"))
            except ValueError as error: flash(str(error), "error")
    return render_template("auth.html", mode="signup", csrf_token=csrf_token())

@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user(): return redirect(url_for("workspace.dashboard"))
    if request.method == "POST":
        if not valid_csrf(request.form.get("csrf_token")): flash("Your form expired. Please try again.", "error")
        else:
            user = authenticate(current_app.config["DATABASE"], request.form.get("email", ""), request.form.get("password", ""))
            if user: session.clear(); session["user_id"] = user["id"]; csrf_token(); return redirect(url_for("workspace.dashboard"))
            flash("Email or password was not recognised.", "error")
    return render_template("auth.html", mode="login", csrf_token=csrf_token())

@auth.post("/logout")
def logout():
    if valid_csrf(request.form.get("csrf_token")): session.clear()
    return redirect(url_for("main.home"))
