import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

# ---------------- Load synthetic dataset ----------------
df = pd.read_csv(r"C:\Users\BRV GOWTHAM\ai_mock\data\synthetic_readiness_dataset_v3.csv")

FEATURES = [
    "relevance",
    "technical_depth",
    "content_score",
    "visual_confidence",
    "visual_nervousness",
    "audio_confidence",
    "fluency_score",
]

X = df[FEATURES]
y = df["final_readiness_score"]

# ---------------- Split ----------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ---------------- Train RF ----------------
model = RandomForestRegressor(
    n_estimators=400,
    max_depth=14,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1,
)

model.fit(X_train, y_train)

# ---------------- Evaluate ----------------
preds = model.predict(X_test)

print("MAE:", round(mean_absolute_error(y_test, preds), 2))
print("R2 :", round(r2_score(y_test, preds), 3))

# ---------------- Feature importance ----------------
print("\nFeature Importances:")
for f, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
    print(f"{f:20s} {imp:.3f}")

# ---------------- Save model ----------------
joblib.dump(model, "readiness_rf_model.joblib")
print("\nModel saved as readiness_rf_model.joblib")
