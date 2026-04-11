import sqlite3
from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "cambia_esto_por_una_clave_secreta"

DB_PATH = "app.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect("/landing")
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, username, email FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    return render_template("index.html", user=user)

@app.route("/landing")
def landing():
    return render_template("landing.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not username or not email or not password or not confirmation:
            flash("Todos los campos son obligatorios.")
            return render_template("landing.html")

        if password != confirmation:
            flash("Las contraseñas no coinciden.")
            return render_template("landing.html")

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        existing_user = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("Ese usuario o email ya existe.")
            return render_template("landing.html")

        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        conn.close()

        flash("Registro completado. Ya puedes iniciar sesión.")
        return redirect("/landing")

    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Debes completar usuario y contraseña.")
            return render_template("landing.html")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Usuario o contraseña incorrectos.")
            return render_template("landing.html")

        session["user_id"] = user["id"]
        flash("Sesión iniciada correctamente.")
        return redirect("/")

    return render_template("landing.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión.")
    return redirect("/")


@app.route("/statistics")
def statistics():
    if "user_id" not in session:
        return redirect("/landing")

    conn = get_db_connection()

    user = conn.execute(
        "SELECT id, username, email FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    """ Example: replace with your real stats queries
    stats = conn.execute(
        "SELECT * FROM user_statistics WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()
"""
    conn.close()

    return render_template("statistics.html", user=user)


@app.route("/test", methods=["GET", "POST"])
def test():
    if "user_id" not in session:
        return redirect("/landing")

    # Si el usuario hace clic en el botón de "Analyze" (POST)
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("No se ha seleccionado ningún archivo.")
            return redirect("/test")
        
        # Obtener resultados
        resultado = 72.5  # ejemplo (lo que calcule tu modelo)
        notas = "Patrón de marcha con ligera asimetría"  # ejemplo
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_id = session["user_id"]

        # Insertar en DB
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO tests (user_id, fecha, resultado, notas)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, fecha, resultado, notas)
        )
        conn.commit()
        conn.close()

        # Lógica de procesamiento aquí... --------------------------------------------
        flash("Análisis completado con éxito.")
        return redirect("/")

    # Si el usuario solo entra a ver la página (GET)
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, username, email FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    return render_template("test.html", user=user)


if __name__ == "__main__":
    app.run(debug=True)