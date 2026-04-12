import traceback
import pandas as pd
import numpy as np
import os
import json
from data_loader import build_data_index
from bio_math import extract_features

def segment_signal(signal, window_size=400, step=200):
    windows = []
    for i in range(0, len(signal) - window_size, step):
        windows.append(signal[i : i + window_size])
    return windows

def run_pipeline():
    # 1. Indexación de archivos
    df_index = build_data_index()
    if df_index.empty: 
        print("❌ Error: No se encontraron archivos para procesar.")
        return

    results = []
    print(f"🚀 Iniciando extracción: {len(df_index)} sujetos detectados.")

    for i, row in df_index.iterrows():
        try:
            # Verificación de existencia de señal bruta
            lb_path = str(row['lb_path']).replace('\\', '/')
            if not os.path.exists(lb_path):
                print(f"⚠️ Salto: Señal no encontrada en {lb_path}")
                continue

            # --- BLOQUE DE METADATOS BLINDADO ---
            # Valores por defecto (Fallback)
            age, gender = 60, 0
            
            # Limpieza y normalización de ruta del JSON
            meta_path = str(row['meta_path']).replace('\\', '/')
            
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        
                        # Búsqueda de Edad (insensible a mayúsculas/minúsculas)
                        age_val = meta.get('Age', meta.get('age', meta.get('AGE')))
                        if age_val is not None:
                            age = int(float(age_val)) # Soporta "65" y "65.0"
                        
                        # Búsqueda de Género y normalización semántica
                        g_raw = str(meta.get('Gender', meta.get('gender', 'F'))).strip().upper()
                        # Mapeo: 1 para Masculino, 0 para Femenino
                        gender = 1 if g_raw in ['M', 'MALE', 'HOMBRE', '1'] else 0
                        
                except Exception as e:
                    print(f"❌ Error leyendo metadatos en {meta_path}: {e}")
            else:
                # Si entras aquí frecuentemente, revisa la estructura de carpetas
                print(f"⚠️ Metadatos ausentes para {row['trial_id']} (Buscado en: {meta_path})")

            # --- PROCESAMIENTO DE SEÑAL ---
            df_sig = pd.read_csv(lb_path, sep='\t')
            cols_acc = ['Acc_X', 'Acc_Y', 'Acc_Z']
            if not all(c in df_sig.columns for c in cols_acc): 
                print(f"⚠️ Columnas incompletas en {lb_path}")
                continue

            # Magnitud Vectorial (Invariante a la orientación del sensor)
            mag_acc = np.linalg.norm(df_sig[cols_acc].values, axis=1)
            
            # Segmentación en ventanas de 4 segundos (a 100Hz)
            ventanas = segment_signal(mag_acc)
            
            for v_idx, v_data in enumerate(ventanas):
                # Extracción de biomarcadores (Wavelets, Entropía, Jerk)
                f = extract_features(v_data)
                
                if f is not None:
                    # Inyección de metadatos y etiquetas
                    f.update({
                        'label': row['label'], 
                        'trial_id': f"{row['trial_id']}_w{v_idx}", 
                        'age': age, 
                        'gender': gender
                    })
                    results.append(f)
                    
        except Exception as e:
            print(f"🔥 Error crítico en sujeto {row['trial_id']}:")
            traceback.print_exc()

    # Guardado de la matriz de características final
    if results:
        df_final = pd.DataFrame(results)
        df_final.to_csv("features_master.csv", index=False)
        print(f"\n✅ Generadas {len(results)} muestras en 'features_master.csv'.")
    else:
        print("❌ No se generó ninguna muestra válida.")

if __name__ == "__main__":
    run_pipeline()