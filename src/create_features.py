import os
from pathlib import Path
import numpy as np
import pandas as pd
from pathlib import Path
import zipfile
import shutil
from src.bio_math import extract_features

# =========================
# CONFIGURACIÓN
# =========================
FS = 100.0
CLIP_SECONDS_START = 0.0
CLIP_SECONDS_END = 0.0
WINDOW_SIZE = 1500
STEP = 1500

DEFAULT_AGE = 60
DEFAULT_GENDER = 0  # 0=F, 1=M

PATH_TO_ZIP = r"C:\Users\Manolo\Desktop\codigo\codigo\HACKATHON 2026-04-11 03-23-07"  # TODO: Cambiar a la ruta real de la carpeta del hackathon

def segment_signal(signal, window_size=WINDOW_SIZE, step=STEP):
    windows = []
    for i in range(0, len(signal) - window_size + 1, step):
        windows.append(signal[i:i + window_size])
    return windows



def unzip_hackathon_data(zip_path, extract_dir=None, overwrite=True):
    """
    Descomprime un ZIP y devuelve la ruta de la carpeta donde quedó extraído.

    Parámetros
    ----------
    zip_path : str o Path
        Ruta al archivo .zip
    extract_dir : str o Path o None
        Carpeta destino. Si es None, extrae junto al zip en una carpeta con su mismo nombre.
    overwrite : bool
        Si True y la carpeta destino existe, la borra antes de extraer.

    Devuelve
    --------
    Path
        Ruta de la carpeta donde se extrajo el contenido.
    """
    zip_path = Path(zip_path)

    if not zip_path.exists():
        raise FileNotFoundError(f"No existe el ZIP: {zip_path}")

    if zip_path.suffix.lower() != ".zip":
        raise ValueError(f"El archivo no es un .zip: {zip_path}")

    if extract_dir is None:
        extract_dir = zip_path.with_suffix("")
    else:
        extract_dir = Path(extract_dir)

    if extract_dir.exists():
        if overwrite:
            shutil.rmtree(extract_dir)
        else:
            raise FileExistsError(f"La carpeta destino ya existe: {extract_dir}")

    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    return extract_dir

def _normalize_name(name: str) -> str:
    return (
        name.strip()
        .lower()
        .replace(" ", "")
        .replace("-", "")
        .replace(".", "")
        .replace("(", "")
        .replace(")", "")
        .replace('"', "")
    )


def find_time_column(df: pd.DataFrame):
    normalized = {_normalize_name(c): c for c in df.columns}
    candidates = [
        "time", "timestamp", "timestamps", "timems", "times", "seconds",
        "elapsedtime", "elapsedseconds"
    ]
    for cand in candidates:
        if cand in normalized:
            return normalized[cand]
    return None


def estimate_fs_from_time(df: pd.DataFrame, fallback=FS):
    time_col = find_time_column(df)
    if time_col is None:
        return fallback

    t = pd.to_numeric(df[time_col], errors="coerce").dropna().values
    if len(t) < 5:
        return fallback

    dt = np.diff(t)
    dt = dt[np.isfinite(dt) & (dt > 0)]
    if len(dt) == 0:
        return fallback

    median_dt = np.median(dt)

    # Si está en ms
    if median_dt > 1:
        median_dt = median_dt / 1000.0

    if median_dt <= 0:
        return fallback

    fs_est = 1.0 / median_dt
    if 10 <= fs_est <= 1000:
        return float(fs_est)

    return fallback


def find_xyz_columns(df, sensor_type="acc"):
    cols = list(df.columns)

    def norm(s):
        return str(s).strip().lower().replace('"', '')

    norm_map = {c: norm(c) for c in cols}

    exact_candidates = [
        ("acc_x", "acc_y", "acc_z"),
        ("gyr_x", "gyr_y", "gyr_z"),
        ("x", "y", "z"),
        ("x (m/s^2)", "y (m/s^2)", "z (m/s^2)"),
        ("x (rad/s)", "y (rad/s)", "z (rad/s)"),
    ]

    for xk, yk, zk in exact_candidates:
        inv = {v: k for k, v in norm_map.items()}
        if xk in inv and yk in inv and zk in inv:
            return inv[xk], inv[yk], inv[zk]

    def axis_match(axis):
        matches = []
        for original, n in norm_map.items():
            if "time" in n:
                continue
            if n == axis or n.startswith(axis + " ") or n.startswith(axis + "("):
                matches.append(original)
                continue
            if n.endswith("_" + axis):
                matches.append(original)
                continue
        return matches

    x_matches = axis_match("x")
    y_matches = axis_match("y")
    z_matches = axis_match("z")

    if x_matches and y_matches and z_matches:
        return x_matches[0], y_matches[0], z_matches[0]

    raise ValueError(
        f"No se pudieron detectar columnas XYZ para {sensor_type}. "
        f"Columnas disponibles: {cols}"
    )


def load_sensor_csv(csv_path: Path):
    df = pd.read_csv(csv_path)
    df = df.dropna(axis=1, how="all")
    return df


def compute_magnitude(df: pd.DataFrame, sensor_type: str):
    x_col, y_col, z_col = find_xyz_columns(df, sensor_type)
    vals = df[[x_col, y_col, z_col]].apply(pd.to_numeric, errors="coerce").values
    vals = np.asarray(vals, dtype=float)
    valid = np.all(np.isfinite(vals), axis=1)
    vals = vals[valid]

    if len(vals) == 0:
        raise ValueError(f"Tras limpiar NaNs, {sensor_type} se quedó sin datos válidos.")

    mag = np.linalg.norm(vals, axis=1)
    return mag


def clip_signal(signal: np.ndarray, fs: float, clip_start_s=CLIP_SECONDS_START, clip_end_s=CLIP_SECONDS_END):
    start_idx = int(round(clip_start_s * fs))
    end_trim = int(round(clip_end_s * fs))

    if len(signal) <= start_idx + end_trim:
        raise ValueError(
            f"La señal es demasiado corta para recortar {clip_start_s}s al inicio "
            f"y {clip_end_s}s al final."
        )

    end_idx = len(signal) - end_trim
    return signal[start_idx:end_idx]


def map_features_for_model(raw_feats: dict, age: int, gender: int):
    """
    OJO:
    El modelo espera columnas que bio_math.extract_features NO genera.
    Aquí se hace una aproximación para poder construir el input esperado.
    """
    mapped = {
        "wv_tremor_energy": raw_feats.get("tremor_locomotion_ratio", 0.0),
        "wv_gait_energy": raw_feats.get("gait_regularity", 0.0),
        "acc_jerk_rms": raw_feats.get("acc_jerk", 0.0),
        "spectral_entropy": raw_feats.get("spectral_entropy", 0.0),
        "age": age,
        "gender": gender,
    }
    return mapped


def build_feature_dataframe(acc_csv: Path, gyr_csv: Path, age=DEFAULT_AGE, gender=DEFAULT_GENDER):
    df_acc = load_sensor_csv(acc_csv)
    df_gyr = load_sensor_csv(gyr_csv)

    fs_acc = estimate_fs_from_time(df_acc, fallback=FS)
    fs_gyr = estimate_fs_from_time(df_gyr, fallback=FS)
    fs_use = min(fs_acc, fs_gyr)

    mag_acc = compute_magnitude(df_acc, "acc")
    mag_gyr = compute_magnitude(df_gyr, "gyr")

    mag_acc = clip_signal(mag_acc, fs_use)
    mag_gyr = clip_signal(mag_gyr, fs_use)

    min_len = min(len(mag_acc), len(mag_gyr))
    mag_acc = mag_acc[:min_len]
    mag_gyr = mag_gyr[:min_len]

    windows_acc = segment_signal(mag_acc, window_size=WINDOW_SIZE, step=STEP)
    windows_gyr = segment_signal(mag_gyr, window_size=WINDOW_SIZE, step=STEP)

    results = []
    base_trial_id = acc_csv.parent.name

    for i, (w_acc, w_gyr) in enumerate(zip(windows_acc, windows_gyr)):
        raw_feats = extract_features(w_acc, w_gyr, fs=fs_use)
        if raw_feats is None:
            continue

        feats = map_features_for_model(raw_feats, age=age, gender=gender)
        feats["trial_id"] = f"{base_trial_id}_w{i}"
        results.append(feats)

    if not results:
        raise ValueError("No se generó ninguna ventana válida de features.")

    df_features = pd.DataFrame(results)

    ordered_cols = [
        "trial_id",
        "wv_tremor_energy",
        "wv_gait_energy",
        "acc_jerk_rms",
        "spectral_entropy",
        "age",
        "gender",
    ]
    return df_features[ordered_cols], fs_use, len(mag_acc)


def generate_features(hackathon_dir, age=DEFAULT_AGE, gender=DEFAULT_GENDER):
    hackathon_dir = Path(hackathon_dir)
    acc_csv = hackathon_dir / "Accelerometer.csv"
    gyr_csv = hackathon_dir / "Gyroscope.csv"

    if not acc_csv.exists():
        raise FileNotFoundError(f"No existe: {acc_csv}")
    if not gyr_csv.exists():
        raise FileNotFoundError(f"No existe: {gyr_csv}")

    df_features, fs_used, n_samples = build_feature_dataframe(
        acc_csv=acc_csv,
        gyr_csv=gyr_csv,
        age=age,
        gender=gender,
    )

    output_csv = hackathon_dir / "features_vector.csv"
    df_features.to_csv(output_csv, index=False)
    print(f"Features generados y guardados en: {output_csv}")

    return df_features


if __name__ == "__main__":
    generate_features()