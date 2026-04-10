import sqlite3
from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cambia_esto_por_una_clave_secreta"

DB_PATH = "users.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    user = None

    if "user_id" in session:
        conn = get_db_connection()
        user = conn.execute(
            "SELECT id, username, email FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()
        conn.close()

    return render_template("index.html", user=user)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not username or not email or not password or not confirmation:
            flash("Todos los campos son obligatorios.")
            return render_template("register.html")

        if password != confirmation:
            flash("Las contraseñas no coinciden.")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        existing_user = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("Ese usuario o email ya existe.")
            return render_template("register.html")

        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        conn.close()

        flash("Registro completado. Ya puedes iniciar sesión.")
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Debes completar usuario y contraseña.")
            return render_template("login.html")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Usuario o contraseña incorrectos.")
            return render_template("login.html")

        session["user_id"] = user["id"]
        flash("Sesión iniciada correctamente.")
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión.")
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)