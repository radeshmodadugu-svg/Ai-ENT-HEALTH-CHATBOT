
import numpy as np
import pandas as pd
import tensorflow as tf
import joblib
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix,
    ConfusionMatrixDisplay,
    classification_report,
    accuracy_score,
)

# ============================================================
# 1. LOAD THE EXISTING PROJECT FILES
# ============================================================

print("Loading dataset and model files...")

df = pd.read_csv("ENT_Filtered_Dataset.csv")
feature_names = joblib.load("ent_features.joblib")
label_encoder = joblib.load("ent_label_encoder.joblib")
temperature = float(joblib.load("calibration_temperature.joblib"))

# Preserve the exact feature order expected by the model.
missing_features = [
    feature for feature in feature_names
    if feature not in df.columns
]

if missing_features:
    raise ValueError(f"Missing dataset features: {missing_features}")

X = df[feature_names].astype(np.float32)
y = label_encoder.transform(df["diseases"])

class_names = label_encoder.classes_

print(f"Dataset records: {len(df)}")
print(f"Number of features: {len(feature_names)}")
print(f"Number of disease classes: {len(class_names)}")
print(f"Calibration temperature: {temperature:.6f}")

# ============================================================
# 2. RECREATE THE SAME TRAIN / VALIDATION / TEST SPLIT
# ============================================================

X_train, X_temp, y_train, y_temp = train_test_split(
    X,
    y,
    test_size=0.30,
    random_state=42,
    stratify=y,
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp,
    y_temp,
    test_size=0.50,
    random_state=42,
    stratify=y_temp,
)

print(f"Training records: {len(X_train)}")
print(f"Validation records: {len(X_val)}")
print(f"Test records: {len(X_test)}")

# ============================================================
# 3. LOAD THE TRAINED MODEL
# ============================================================

model = tf.keras.models.load_model("ent_dl_model.keras")

# ============================================================
# 4. PREDICT THE HELD-OUT TEST SET
# ============================================================

print("\nGenerating test predictions...")

raw_probabilities = model.predict(
    X_test,
    verbose=0,
)

# Match the probability calibration approach used by main.py.
epsilon = 1e-7

probabilities = np.clip(
    raw_probabilities,
    epsilon,
    1.0,
)

probabilities = probabilities / probabilities.sum(
    axis=1,
    keepdims=True,
)

logits = np.log(probabilities)
calibrated_logits = logits / temperature

# Numerically stable softmax.
calibrated_logits -= calibrated_logits.max(
    axis=1,
    keepdims=True,
)

exp_logits = np.exp(calibrated_logits)

calibrated_probabilities = exp_logits / exp_logits.sum(
    axis=1,
    keepdims=True,
)

y_pred = np.argmax(calibrated_probabilities, axis=1)

# ============================================================
# 5. CALCULATE METRICS
# ============================================================

accuracy = accuracy_score(y_test, y_pred)

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=np.arange(len(class_names)),
)

print("\n" + "=" * 60)
print("HELD-OUT TEST SET RESULTS")
print("=" * 60)
print(f"Test samples: {len(y_test)}")
print(f"Accuracy: {accuracy:.4%}")

print("\nClassification report:")
print(
    classification_report(
        y_test,
        y_pred,
        labels=np.arange(len(class_names)),
        target_names=class_names,
        digits=4,
        zero_division=0,
    )
)

# Save numerical results.
pd.DataFrame(
    cm,
    index=class_names,
    columns=class_names,
).to_csv("confusion_matrix_results.csv", index=True)

pd.DataFrame(
    classification_report(
        y_test,
        y_pred,
        labels=np.arange(len(class_names)),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
).transpose().to_csv("classification_report.csv")

# ============================================================
# 6. PLOT AND SAVE THE CONFUSION MATRIX
# ============================================================

fig, ax = plt.subplots(figsize=(13, 10))

display = ConfusionMatrixDisplay(
    confusion_matrix=cm,
    display_labels=class_names,
)

display.plot(
    ax=ax,
    cmap="Blues",
    values_format="d",
    colorbar=True,
    xticks_rotation=45,
)

ax.set_title(
    "Confusion Matrix — ENT Disease Classification",
    fontsize=16,
    pad=18,
)

ax.set_xlabel("Predicted Disease", fontsize=12)
ax.set_ylabel("True Disease", fontsize=12)

plt.tight_layout()

plt.savefig(
    "confusion_matrix.png",
    dpi=200,
    bbox_inches="tight",
)

plt.show()

print("\nFiles saved:")
print("  confusion_matrix.png")
print("  confusion_matrix_results.csv")
print("  classification_report.csv")

