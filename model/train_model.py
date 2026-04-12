import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import accuracy_score, classification_report
import joblib

# 1. Preparación
df = pd.read_csv("features_master.csv")
X = df.drop(['label', 'trial_id'], axis=1)
y = df['label']
groups = df['trial_id'].apply(lambda x: x.split('_')[0] + "_" + x.split('_')[1])

# 2. Validación LOSO
logo = LeaveOneGroupOut()
y_true_all, y_pred_all = [], []

print("Validando modelo contra sujetos desconocidos...")

for train_idx, test_idx in logo.split(X, y, groups=groups):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    
    model = XGBClassifier(
        n_estimators=150,
        learning_rate=0.04,
        max_depth=4,
        reg_alpha=0.1,  # Regularización para evitar ruido
        reg_lambda=1.0, 
        scale_pos_weight=1.8, # Prioridad al Recall de CIPN
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # Decisión por paciente (media de probabilidades)
    probs = model.predict_proba(X_test)[:, 1]
    y_pred_all.append(1 if np.mean(probs) >= 0.38 else 0)
    y_true_all.append(y_test.iloc[0])

print(f"\n🚀 ACCURACY LOSO: {accuracy_score(y_true_all, y_pred_all)*100:.2f}%")
print(classification_report(y_true_all, y_pred_all))

# 3. Guardar para el Frontend
model.fit(X, y)
joblib.dump(model, "cipn_final_model.pkl")
print("✅ Modelo 'cipn_final_model.pkl' generado.")