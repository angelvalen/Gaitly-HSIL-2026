import sqlite3

def main():
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    )
    """)

    # TESTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        wv_tremor_energy REAL,
        wv_gait_energy REAL,
        acc_jerk_rms REAL,
        spectral_entropy REAL,
        target_prob REAL,
        riesgo_caida_pct REAL,
        tendencia_pendiente REAL,
        estado_evolutivo TEXT,
        ritmo_caos REAL,
        control_motor REAL,
        micro_temblor REAL,
        regularidad_paso_pct REAL,
        suavidad_mecanica_pct REAL,
        eficiencia_energetica_pct REAL,
        fatiga_dinamica_ptc REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

    return 0

if __name__ == "__main__":
    print("Initializing database")
    main()
    
