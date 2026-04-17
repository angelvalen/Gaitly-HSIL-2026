import math
import numpy as np

class ClinicalMetricsEngine:
    """
    Motor matemático avanzado para extracción de métricas clínicas y biomecánicas.
    Convierte biomarcadores brutos en índices interpretables de 0 a 100.
    """

    @staticmethod
    def _sigmoid(x):
        x = max(min(x, 10), -10)
        return 1 / (1 + math.exp(-x))

    @staticmethod
    def calculate_fall_risk(entropy, jerk):
        w_entropy = 1.2
        w_jerk = 1.5
        bias = 2.5 
        exponent = (w_entropy * entropy) + (w_jerk * jerk) - bias
        risk_prob = ClinicalMetricsEngine._sigmoid(exponent)
        return round(risk_prob * 100, 1)

    @staticmethod
    def normalize_to_radar(value, min_val, max_val):
        val_clamped = max(min(value, max_val), min_val)
        score = 10 * ((val_clamped - min_val) / (max_val - min_val))
        return round(score, 1)

    @staticmethod
    def calculate_degradation_trend(history):
        if not history or len(history) < 2:
            return 0.0
        n = len(history)
        t = np.arange(1, n + 1)
        y = np.array(history)
        numerador = (n * np.sum(t * y)) - (np.sum(t) * np.sum(y))
        denominador = (n * np.sum(t**2)) - (np.sum(t))**2
        if denominador == 0:
            return 0.0
        return round(float(numerador / denominador), 2)

    # --- NUEVAS MÉTRICAS BIOMECÁNICAS (SaaS PRO) ---

    @staticmethod
    def calculate_regularity(entropy):
        """
        Índice de Regularidad (0-100%).
        Asume una relación inversamente proporcional con la Entropía Espectral.
        Un sistema con entropía 0 (sin caos) es 100% regular.
        """
        # Penalización de 25 puntos por cada unidad de Z-score de entropía
        regularidad = 100.0 - (entropy * 25.0)
        return round(max(0.0, min(100.0, regularidad)), 1)

    @staticmethod
    def calculate_smoothness(jerk):
        """
        Índice de Suavidad Mecánica (0-100%).
        Decaimiento exponencial basado en el Jerk para penalizar fuertemente los espasmos.
        """
        # Usamos e^(-x) para que un Jerk alto desplome la suavidad rápidamente.
        suavidad = 100.0 * math.exp(-0.8 * max(0, jerk))
        return round(suavidad, 1)

    @staticmethod
    def calculate_energy_efficiency(wavelets):
        """
        Balance Energético (Eficiencia de Marcha 0-100%).
        La energía Wavelet de alta frecuencia representa el "ruido" o temblor parasitario.
        """
        # Asumimos que más de 5.0 en wavelets es 0% eficiencia (todo es temblor)
        ruido_pct = (wavelets / 5.0) * 100.0
        eficiencia = 100.0 - ruido_pct
        return round(max(0.0, min(100.0, eficiencia)), 1)

    @staticmethod
    def calculate_dynamic_fatigue(tendencia_m):
        """
        Indicador de Fatiga Acumulada (0-100%).
        Proyecta la pendiente de degradación hacia un índice de cansancio físico.
        """
        # Una pendiente de +4.0 (deterioro rápido) satura la fatiga al 100%
        fatiga = (tendencia_m / 4.0) * 100.0
        return round(max(0.0, min(100.0, fatiga)), 1)

    @classmethod
    def generate_full_report(cls, features_dict, prob_modelo, historial_paciente=None):
        if historial_paciente is None:
            historial_paciente = []

        # 1. Extracción de variables
        entropy = features_dict.get('spectral_entropy', 0)
        jerk = features_dict.get('acc_jerk_rms', 0)
        wavelets = features_dict.get('wv_tremor_energy', 0)

        # 2. Cálculos Base
        fall_risk = cls.calculate_fall_risk(entropy, jerk)
        historial_actualizado = historial_paciente + [prob_modelo * 100]
        tendencia_m = cls.calculate_degradation_trend(historial_actualizado)
        
        # 3. Cálculos Biomecánicos Avanzados
        idx_regularidad = cls.calculate_regularity(entropy)
        idx_suavidad = cls.calculate_smoothness(jerk)
        idx_eficiencia = cls.calculate_energy_efficiency(wavelets)
        idx_fatiga = cls.calculate_dynamic_fatigue(tendencia_m)

        estado_tendencia = "Stable"
        if tendencia_m > 3.0:
            estado_tendencia = "Warning: Fast Deterioration"
        elif tendencia_m < -1.0:
            estado_tendencia = "Improvemet / Positive Response"

        # 4. JSON Maestro para el Frontend
        return {
            "seguridad": {
                "riesgo_caida_pct": fall_risk,
                "tendencia_pendiente": tendencia_m,
                "estado_evolutivo": estado_tendencia
            },
            "radar_biomecanico": {
                "ritmo_caos": cls.normalize_to_radar(entropy, -1.0, 3.0),
                "control_motor": cls.normalize_to_radar(jerk, 0.0, 5.0),
                "micro_temblor": cls.normalize_to_radar(wavelets, 0.0, 10.0)
            },
            "analisis_avanzado": {
                "regularidad_paso_pct": idx_regularidad,
                "suavidad_mecanica_pct": idx_suavidad,
                "eficiencia_energetica_pct": idx_eficiencia,
                "fatiga_dinamica_pct": idx_fatiga
            }
        }