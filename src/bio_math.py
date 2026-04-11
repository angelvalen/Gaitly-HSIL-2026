import numpy as np
from scipy.signal import butter, filtfilt, find_peaks, welch

def apply_butterworth(signal, fs=100.0, cutoff=15.0): 
    """Filtro pasa-bajo para eliminar ruido de alta frecuencia manteniendo la biomecánica."""
    nyq = 0.5 * fs
    b, a = butter(4, cutoff / nyq, btype='low', analog=False)
    return filtfilt(b, a, signal)

def extract_features(acc_sig, gyr_sig, fs=100.0):
    """Extrae biomarcadores digitales de las señales de aceleración y giroscopio."""
    # Validación de longitud mínima (mínimo 2 segundos de datos)
    if len(acc_sig) < int(fs * 2): 
        return None

    # 1. PREPROCESAMIENTO: Limpieza y centrado de señales
    acc_clean = apply_butterworth(acc_sig, fs)
    acc_clean = acc_clean - np.mean(acc_clean)
    
    gyr_clean = apply_butterworth(gyr_sig, fs)
    gyr_clean = gyr_clean - np.mean(gyr_clean)
    
    feats = {}
    
    # 2. ACELERACIÓN (Fuerza e Impacto)
    feats['acc_std'] = np.std(acc_clean)
    # Jerk: Derivada de la aceleración (brusquedad) -> j = da/dt
    feats['acc_jerk'] = np.sqrt(np.mean((np.diff(acc_clean) * fs)**2))
    
    # Factor de cresta: Relación pico/RMS (calidad de la pisada)
    rms_acc = np.sqrt(np.mean(acc_clean**2))
    feats['crest_factor'] = np.max(np.abs(acc_clean)) / rms_acc if rms_acc > 0 else 0
    
    # 3. GIROSCÓPIO (Estabilidad y Balanceo)
    feats['gyr_std'] = np.std(gyr_clean)
    feats['gyr_jerk'] = np.sqrt(np.mean((np.diff(gyr_clean) * fs)**2))

    # 4. RITMICIDAD Y VARIABILIDAD
    # Autocorrelación para regularidad de la marcha
    autocorr = np.correlate(acc_clean, acc_clean, mode='full')[len(acc_clean)//2:]
    if np.max(autocorr) > 0:
        autocorr /= np.max(autocorr)
        peaks, _ = find_peaks(autocorr, distance=int(fs*0.4))
        feats['gait_regularity'] = autocorr[peaks[0]] if len(peaks) > 0 else 0
    else:
        feats['gait_regularity'] = 0
        
    # Variabilidad de paso (Coeficiente de Variación del tiempo entre picos)
    picos_zancada, _ = find_peaks(acc_clean, distance=fs*0.5, prominence=np.std(acc_clean)*0.5)
    if len(picos_zancada) > 2:
        inter_pasos = np.diff(picos_zancada) / fs
        feats['step_variability'] = (np.std(inter_pasos) / np.mean(inter_pasos)) * 100
    else:
        feats['step_variability'] = 0

    # 5. ANÁLISIS ESPECTRAL (Caos y Frecuencias)
    freqs, psd = welch(acc_clean, fs, nperseg=min(256, len(acc_clean)))
    psd_norm = psd / np.sum(psd)
    psd_nz = psd_norm[psd_norm > 0]
    # Entropía Espectral: Cuantifica el desorden de la marcha
    feats['spectral_entropy'] = -np.sum(psd_nz * np.log2(psd_nz))
    
    # Ratio Temblor (3-10Hz) vs Locomoción (0.5-3Hz)
    locomotion = np.sum(psd[(freqs >= 0.5) & (freqs <= 3.0)])
    tremor = np.sum(psd[(freqs > 3.0) & (freqs <= 10.0)])
    feats['tremor_locomotion_ratio'] = tremor / locomotion if locomotion > 0 else 0

    # 6. DINÁMICA DE FASES Y ENERGÍA
    min_len = min(len(acc_clean), len(gyr_clean))
    if min_len > 0:
        # Correlación cruzada: Sincronización entre impacto vertical y giro de cadera
        corr_matrix = np.corrcoef(acc_clean[:min_len], gyr_clean[:min_len])
        feats['cross_corr_acc_gyr'] = corr_matrix[0, 1]
        
        # SMA (Signal Magnitude Area): Medida de gasto energético normalizada
        feats['sma_acc'] = np.sum(np.abs(acc_clean)) / fs
        feats['sma_gyr'] = np.sum(np.abs(gyr_clean)) / fs
    else:
        feats['cross_corr_acc_gyr'] = 0
        feats['sma_acc'] = 0
        feats['sma_gyr'] = 0
    
    return feats