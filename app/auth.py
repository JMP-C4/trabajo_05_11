# app/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from .models import User, db

auth_bp = Blueprint("auth", __name__)

# ---------------------------
# RUTA DE REGISTRO
# ---------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validaciones básicas
        if not username or not password:
            flash("Todos los campos son obligatorios", "danger")
            return render_template("register.html")
        if password != confirm_password:
            flash("Las contraseñas no coinciden", "danger")
            return render_template("register.html")

        # Verificar si usuario existe
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("El usuario ya existe", "danger")
            return render_template("register.html")

        # Crear usuario con contraseña hasheada (usar pbkdf2:sha256 para compatibilidad)
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Usuario registrado correctamente, ahora inicia sesión", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ---------------------------
# RUTA DE LOGIN
# ---------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if not user:
            flash("Usuario no encontrado", "danger")
        elif check_password_hash(user.password, password):
            login_user(user)
            flash("Bienvenido, " + username, "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Contraseña incorrecta", "danger")

    return render_template("login.html")


# ---------------------------
# RUTA DE LOGOUT
# ---------------------------
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Has cerrado sesión correctamente", "success")
    return redirect(url_for("auth.login"))
