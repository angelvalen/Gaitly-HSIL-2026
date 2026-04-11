import time
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests

from src.create_features import generate_features
from src.clinical_metrics import ClinicalMetricsEngine

# =========================
# CONFIGURACIÓN
# =========================
PHYPHOX_BASE_URL = "http://10.178.99.34"
MODEL_PATH = Path("./model/cipn_final_model.pkl")
POLL_EVERY = 0.5
TARGET_SAMPLES = 1500


# =========================
# PHYPhox
# =========================
def start_measurement():
    r = requests.get(f"{PHYPHOX_BASE_URL}/control?cmd=start", timeout=5)
    r.raise_for_status()


def stop_measurement():
    r = requests.get(f"{PHYPHOX_BASE_URL}/control?cmd=stop", timeout=5)
    r.raise_for_status()


def clear_measurement():
    r = requests.get(f"{PHYPHOX_BASE_URL}/control?cmd=clear", timeout=5)
    r.raise_for_status()


def get_full_buffers():
    url = (
        f"{PHYPHOX_BASE_URL}/get?"
        "acc_time=full&accX=full&accY=full&accZ=full&"
        "gyro_time=full&gyroX=full&gyroY=full&gyroZ=full"
    )
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    payload = r.json()

    if "buffer" not in payload:
        raise ValueError(f"Respuesta inesperada de phyphox: {payload}")

    return payload["buffer"], payload.get("status", {})


# =========================
# CONVERSIÓN A CSV TEMPORAL
# =========================
def buffers_to_dataframes(buffers):
    df_acc = pd.DataFrame({
        "Time (s)": buffers["acc_time"]["buffer"],
        "X (m/s^2)": buffers["accX"]["buffer"],
        "Y (m/s^2)": buffers["accY"]["buffer"],
        "Z (m/s^2)": buffers["accZ"]["buffer"],
    })

    df_gyr = pd.DataFrame({
        "Time (s)": buffers["gyro_time"]["buffer"],
        "X (rad/s)": buffers["gyroX"]["buffer"],
        "Y (rad/s)": buffers["gyroY"]["buffer"],
        "Z (rad/s)": buffers["gyroZ"]["buffer"],
    })

    return df_acc, df_gyr


def generate_features_from_live_buffers(buffers):
    df_acc, df_gyr = buffers_to_dataframes(buffers)

    if df_acc.empty:
        raise ValueError("El acelerómetro está vacío.")
    if df_gyr.empty:
        raise ValueError("El giroscopio está vacío.")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        acc_csv = tmpdir / "Accelerometer.csv"
        gyr_csv = tmpdir / "Gyroscope.csv"

        df_acc.to_csv(acc_csv, index=False)
        df_gyr.to_csv(gyr_csv, index=False)

        df_features = generate_features(tmpdir)

    return df_features


# =========================
# PREDICCIÓN
# =========================
def predict_from_feature_df(df):
    if df.empty:
        raise ValueError("No se generaron features")

    cols_to_drop = ["trial_id", "label"]
    X = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

    model = joblib.load(MODEL_PATH)

    if hasattr(model, "feature_names_in_"):
        expected_cols = list(model.feature_names_in_)
        X = X[expected_cols]

    probs = model.predict_proba(X)[:, 1]
    mean_prob = np.mean(probs)
    prediction = 1 if mean_prob >= 0.4 else 0

    return prediction, mean_prob


# =========================
# FLUJO PRINCIPAL
# =========================
def run_test():

    clear_measurement()
    start_measurement()
    print(f"Midiendo hasta {TARGET_SAMPLES} muestras...")

    while True:
        buffers, status = get_full_buffers()

        acc_n = len(buffers["accX"]["buffer"])
        gyro_n = len(buffers["gyroX"]["buffer"])
        measuring = status.get("measuring", False)

        print(
            f"\rACC: {acc_n:5d} muestras | GYRO: {gyro_n:5d} muestras | measuring={measuring}",
            end="",
            flush=True,
        )

        if acc_n >= TARGET_SAMPLES and gyro_n >= TARGET_SAMPLES:
            break

        time.sleep(POLL_EVERY)

    print("\nParando medición...")
    stop_measurement()

    buffers, _ = get_full_buffers()

    # recorte exacto a 1500 por si una lectura se pasó
    for key in ["acc_time", "accX", "accY", "accZ", "gyro_time", "gyroX", "gyroY", "gyroZ"]:
        buffers[key]["buffer"] = buffers[key]["buffer"][:TARGET_SAMPLES]

    df_features = generate_features_from_live_buffers(buffers)
    prediction, mean_prob = predict_from_feature_df(df_features)

    print("\n--- RESULTADO ---")
    print(f"Ventanas generadas: {len(df_features)}")
    print(f"Probabilidad media CIPN: {mean_prob:.4f}")
    print(f"Predicción final: {'CIPN (1)' if prediction == 1 else 'SANO (0)'}")

    # --- MÉTRICAS CLÍNICAS ---
    # Obtenemos promedios de las features para el reporte clínico
    features_avg = {
        "wv_tremor_energy": float(df_features["wv_tremor_energy"].mean()),
        "wv_gait_energy": float(df_features["wv_gait_energy"].mean()),
        "acc_jerk_rms": float(df_features["acc_jerk_rms"].mean()),
        "spectral_entropy": float(df_features["spectral_entropy"].mean())
    }

    # Generamos el reporte anidado
    reporte_anidado = ClinicalMetricsEngine.generate_full_report(features_avg, mean_prob)

    # Aplanamos el reporte para el retorno final
    resultado_final = {
        **features_avg,
        "target_prob": float(mean_prob)
    }

    # Recorremos el reporte anidado y aplanamos sus niveles
    for categoria in reporte_anidado.values():
        if isinstance(categoria, dict):
            resultado_final.update(categoria)

    return resultado_final


if __name__ == "__main__":
    run_test()

def _safe_mag(x, y, z):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    n = min(len(x), len(y), len(z))
    if n == 0:
        return np.array([])
    return np.sqrt(x[:n]**2 + y[:n]**2 + z[:n]**2)


def get_live_preview(preview_len=80):
    buffers, status = get_full_buffers()

    acc_mag = _safe_mag(
        buffers["accX"]["buffer"],
        buffers["accY"]["buffer"],
        buffers["accZ"]["buffer"],
    )

    gyr_mag = _safe_mag(
        buffers["gyroX"]["buffer"],
        buffers["gyroY"]["buffer"],
        buffers["gyroZ"]["buffer"],
    )

    acc_tail = acc_mag[-preview_len:].tolist() if len(acc_mag) else []
    gyr_tail = gyr_mag[-preview_len:].tolist() if len(gyr_mag) else []

    acc_n = len(buffers["accX"]["buffer"])
    gyro_n = len(buffers["gyroX"]["buffer"])

    return {
        "measuring": bool(status.get("measuring", False)),
        "acc_samples": acc_n,
        "gyro_samples": gyro_n,
        "fs_est": 100,
        "labels": list(range(max(len(acc_tail), len(gyr_tail)))),
        "acc_mag": acc_tail,
        "gyr_mag": gyr_tail,
        "message": f"ACC {acc_n} / GYRO {gyro_n} muestras recibidas"
    }


def finalize_live_test():
    stop_measurement()
    buffers, _ = get_full_buffers()

    for key in [
        "acc_time", "accX", "accY", "accZ",
        "gyro_time", "gyroX", "gyroY", "gyroZ"
    ]:
        buffers[key]["buffer"] = buffers[key]["buffer"][:TARGET_SAMPLES]

    df_features = generate_features_from_live_buffers(buffers)
    prediction, mean_prob = predict_from_feature_df(df_features)

    features_avg = {
        "wv_tremor_energy": float(df_features["wv_tremor_energy"].mean()),
        "wv_gait_energy": float(df_features["wv_gait_energy"].mean()),
        "acc_jerk_rms": float(df_features["acc_jerk_rms"].mean()),
        "spectral_entropy": float(df_features["spectral_entropy"].mean())
    }

    reporte_anidado = ClinicalMetricsEngine.generate_full_report(features_avg, mean_prob)

    resultado_final = {
        **features_avg,
        "target_prob": float(mean_prob),
        "prediction": int(prediction),
        "score": round(float(mean_prob) * 100)
    }

    for categoria in reporte_anidado.values():
        if isinstance(categoria, dict):
            resultado_final.update(categoria)

    return resultado_final