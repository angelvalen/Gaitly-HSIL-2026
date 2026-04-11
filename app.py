import sqlite3
from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from src.pedictor_din import run_test
from flask import jsonify
from src.pedictor_din import (
    clear_measurement,
    start_measurement,
    get_live_preview,
    finalize_live_test,
)

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

    metrics = conn.execute("""
        SELECT
            date,
            target_prob,
            riesgo_caida_pct,
            micro_temblor,
            tendencia_pendiente,
            estado_evolutivo,
            ritmo_caos,
            control_motor,
            regularidad_paso_pct,
            suavidad_mecanica_pct,
            eficiencia_energetica_pct,
            fatiga_dinamica_pct,
            wv_tremor_energy,
            wv_gait_energy,
            acc_jerk_rms,
            spectral_entropy
        FROM tests
        WHERE user_id = ?
        ORDER BY date DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("index.html", user=user, metrics=metrics)


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
            flash("All fields are required.")
            return render_template("landing.html")

        if password != confirmation:
            flash("Passwords do not match.")
            return render_template("landing.html")

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        existing_user = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("E-mail or user already exists.")
            return render_template("landing.html")

        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        conn.close()

        flash("Registration completed. You can now log-in.")
        return redirect("/landing")

    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("You must enter both username and password")
            return render_template("landing.html")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Wrong username or password.")
            return render_template("landing.html")

        session["user_id"] = user["id"]
        flash("Log-in succesful.")
        return redirect("/")

    return render_template("landing.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged-out.")
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

    
    metrics = conn.execute(
        "SELECT * FROM tests WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("statistics.html", user=user, metrics=metrics)


@app.route("/test", methods=["GET", "POST"])
def test():
    if "user_id" not in session:
        return redirect("/landing")

    # Si el usuario hace clic en el botón de "Run Test" (POST)
    if request.method == "POST":
        
        
        # Obtener resultados
        results = run_test()
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_id = session["user_id"]

        # Insertar en DB
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO tests (
                user_id,
                date,
                wv_tremor_energy,
                wv_gait_energy,
                acc_jerk_rms,
                spectral_entropy,
                target_prob,
                riesgo_caida_pct,
                tendencia_pendiente,
                estado_evolutivo,
                ritmo_caos,
                control_motor,
                micro_temblor,
                regularidad_paso_pct,
                suavidad_mecanica_pct,
                eficiencia_energetica_pct,
                fatiga_dinamica_pct
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                date,
                results["wv_tremor_energy"],
                results["wv_gait_energy"],
                results["acc_jerk_rms"],
                results["spectral_entropy"],
                results["target_prob"],
                results["riesgo_caida_pct"],
                results["tendencia_pendiente"],
                results["estado_evolutivo"],
                results["ritmo_caos"],
                results["control_motor"],
                results["micro_temblor"],
                results["regularidad_paso_pct"],
                results["suavidad_mecanica_pct"],
                results["eficiencia_energetica_pct"],
                results["fatiga_dinamica_pct"]
            ))
        conn.commit()
        conn.close()

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

@app.post("/api/live-start")
def api_live_start():
    try:
        clear_measurement()
        start_measurement()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/live-preview")
def api_live_preview():
    try:
        payload = get_live_preview()
        return jsonify(payload)
    except Exception as e:
        return jsonify({
            "measuring": False,
            "acc_samples": 0,
            "gyro_samples": 0,
            "fs_est": "--",
            "labels": [],
            "acc_mag": [],
            "gyr_mag": [],
            "message": f"Error leyendo preview live: {str(e)}"
        }), 500


@app.post("/api/live-finish")
def api_live_finish():
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "User not autenticated"}), 401

    try:
        result = finalize_live_test()

        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_id = session["user_id"]

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO tests (
                user_id,
                date,
                wv_tremor_energy,
                wv_gait_energy,
                acc_jerk_rms,
                spectral_entropy,
                target_prob,
                riesgo_caida_pct,
                tendencia_pendiente,
                estado_evolutivo,
                ritmo_caos,
                control_motor,
                micro_temblor,
                regularidad_paso_pct,
                suavidad_mecanica_pct,
                eficiencia_energetica_pct,
                fatiga_dinamica_pct
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            date,
            result.get("wv_tremor_energy"),
            result.get("wv_gait_energy"),
            result.get("acc_jerk_rms"),
            result.get("spectral_entropy"),
            result.get("target_prob"),
            result.get("riesgo_caida_pct"),
            result.get("tendencia_pendiente"),
            result.get("estado_evolutivo"),
            result.get("ritmo_caos"),
            result.get("control_motor"),
            result.get("micro_temblor"),
            result.get("regularidad_paso_pct"),
            result.get("suavidad_mecanica_pct"),
            result.get("eficiencia_energetica_pct"),
            result.get("fatiga_dinamica_pct")
        ))
        conn.commit()
        conn.close()

        score = result.get("score", 0)

        return jsonify({
            "ok": True,
            "score": score,
            "prediction": result.get("prediction", 0),
            "redirect_url": "/",
            "result": result
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
if __name__ == "__main__":
    app.run(debug=True)