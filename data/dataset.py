import numpy as np
import pandas as pd

np.random.seed(42)
N_SAMPLES = 5000


def clamp(x):
    return np.clip(x, 0, 100)


rows = []

for _ in range(N_SAMPLES):
    # ---------------- Content ----------------
    relevance = clamp(np.random.normal(72, 12))
    technical_depth = clamp(np.random.normal(68, 12))

    content_score = clamp(
        0.45 * relevance +
        0.45 * technical_depth +
        np.random.normal(0, 6)
    )

    # ---------------- Visual ----------------
    visual_confidence = clamp(np.random.normal(70, 10))
    visual_nervousness = clamp(
        100 - visual_confidence + np.random.normal(0, 8)
    )

    # ---------------- Audio ----------------
    audio_confidence = clamp(np.random.normal(68, 10))
    fluency_score = clamp(
        0.5 * audio_confidence +
        np.random.normal(35, 10)
    )

    # ---------------- Interaction terms ----------------
    communication_strength = (
        0.5 * visual_confidence +
        0.5 * audio_confidence
    )

    # ---------------- Final readiness ----------------
    final_readiness = clamp(
        0.27 * content_score +
        0.26 * relevance +
        0.21 * technical_depth +
        0.20 * communication_strength +
        0.15 * fluency_score +
        0.11 * (100 - visual_nervousness) +
        np.random.normal(0, 3)   # ✅ controlled noise
    )

    rows.append([
        relevance,
        technical_depth,
        content_score,
        visual_confidence,
        visual_nervousness,
        audio_confidence,
        fluency_score,
        final_readiness
    ])


df = pd.DataFrame(rows, columns=[
    "relevance",
    "technical_depth",
    "content_score",
    "visual_confidence",
    "visual_nervousness",
    "audio_confidence",
    "fluency_score",
    "final_readiness_score"
])

df.to_csv("synthetic_readiness_dataset_v3.csv", index=False)
print("Saved synthetic_readiness_dataset_v3.csv")
