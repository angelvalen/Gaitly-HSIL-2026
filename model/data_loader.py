import os
from pathlib import Path
import pandas as pd

def build_data_index(base_path_str=None):
    if base_path_str is None:
        root_path = Path(__file__).resolve().parent.parent
        base_path = root_path / "dataset" / "data"
    else:
        base_path = Path(base_path_str).resolve()
    
    records = []
    print(f"--- Buscando datos en: {base_path} ---")
    
    if not base_path.exists():
        print(f"ERROR: No se encuentra la carpeta en {base_path}")
        return pd.DataFrame()

    # 1. Buscar CIPN
    cipn_files = list(base_path.rglob("neuro/CIPN/**/*_meta.json"))
    for p in cipn_files:
        sensor_path = str(p).replace('_meta.json', '_raw_data_LB.txt')
        
        records.append({
            'trial_id': p.stem.replace('_meta', ''),
            'meta_path': str(p),
            'lb_path': sensor_path,
            'label': 1
        })
    print(f"-> Encontrados {len(cipn_files)} archivos de metadatos CIPN.")

    # 2. Buscar Healthy
    healthy_files = list(base_path.rglob("healthy/**/*_meta.json"))
    healthy_files = healthy_files[:len(cipn_files)]
    
    for p in healthy_files:
        sensor_path = str(p).replace('_meta.json', '_raw_data_LB.txt')
        
        records.append({
            'trial_id': p.stem.replace('_meta', ''),
            'meta_path': str(p),
            'lb_path': sensor_path,
            'label': 0
        })
    print(f"-> Encontrados {len(healthy_files)} archivos de metadatos Healthy.")
    
    df = pd.DataFrame(records)
    
    # Debug rápido: verificar si el primer archivo existe de verdad
    if not df.empty:
        first_file = df.iloc[0]['lb_path']
        if os.path.exists(first_file):
            print(f"CONFIRMADO: El archivo de sensor existe: {first_file}")
        else:
            print(f"ALERTA: El archivo calculado NO existe: {first_file}")
            
    return df

if __name__ == "__main__":
    df_index = build_data_index()
    if not df_index.empty:
        print(f"\n Indexación terminada.")