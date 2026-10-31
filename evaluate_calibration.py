import numpy as np
import pandas as pd
import tensorflow as tf
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss


# ==========================================
# 1. LOAD DATA
# ==========================================

print("Loading ENT dataset...")

df = pd.read_csv("ENT_Filtered_Dataset.csv")

X = df.drop(columns=["diseases"]).astype(np.float32)
y_raw = df["diseases"]

label_encoder = joblib.load("ent_label_encoder.joblib")
y_encoded = label_encoder.transform(y_raw)

print(f"Dataset shape: {X.shape}")
print(f"Number of classes: {len(label_encoder.classes_)}")


# ==========================================
# 2. RECREATE ORIGINAL DATA SPLIT
# ==========================================

X_train, X_temp, y_train, y_temp = train_test_split(
    X,
    y_encoded,
    test_size=0.30,
    random_state=42,
    stratify=y_encoded
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp,
    y_temp,
    test_size=0.50,
    random_state=42,
    stratify=y_temp
)

print(f"Validation samples: {len(X_val)}")
print(f"Test samples: {len(X_test)}")


# ==========================================
# 3. LOAD MODEL + CALIBRATION TEMPERATURE
# ==========================================

print("\nLoading trained model...")

model = tf.keras.models.load_model("ent_dl_model.keras")

temperature = float(
    joblib.load("calibration_temperature.joblib")
)

print(f"Loaded calibration temperature: {temperature:.4f}")


# ==========================================
# 4. GET TEST PREDICTIONS
# ==========================================

print("\nGenerating test predictions...")

test_probabilities = model.predict(
    X_test,
    verbose=0
)

epsilon = 1e-7

test_probabilities = np.clip(
    test_probabilities,
    epsilon,
    1.0
)

# Normalize after clipping
test_probabilities = (
    test_probabilities /
    test_probabilities.sum(axis=1, keepdims=True)
)


# ==========================================
# 5. APPLY TEMPERATURE SCALING
# ==========================================

test_logits = np.log(test_probabilities)

calibrated_logits = test_logits / temperature

calibrated_probabilities = tf.nn.softmax(
    calibrated_logits,
    axis=1
).numpy()


# ==========================================
# 6. PREDICTIONS
# ==========================================

raw_predictions = np.argmax(
    test_probabilities,
    axis=1
)

calibrated_predictions = np.argmax(
    calibrated_probabilities,
    axis=1
)


# ==========================================
# 7. EXPECTED CALIBRATION ERROR (ECE)
# ==========================================

def calculate_ece(probabilities, labels, n_bins=10):

    predictions = np.argmax(
        probabilities,
        axis=1
    )

    confidence = np.max(
        probabilities,
        axis=1
    )

    correctness = (
        predictions == labels
    ).astype(float)

    bin_edges = np.linspace(
        0.0,
        1.0,
        n_bins + 1
    )

    ece = 0.0

    print("\nCalibration Bins")
    print("-" * 65)
    print(
        f"{'Confidence Range':<20}"
        f"{'Count':<10}"
        f"{'Accuracy':<15}"
        f"{'Confidence':<15}"
    )
    print("-" * 65)

    for i in range(n_bins):

        lower = bin_edges[i]
        upper = bin_edges[i + 1]

        if i == n_bins - 1:
            mask = (
                (confidence >= lower) &
                (confidence <= upper)
            )
        else:
            mask = (
                (confidence >= lower) &
                (confidence < upper)
            )

        if np.sum(mask) == 0:
            continue

        bin_accuracy = np.mean(
            correctness[mask]
        )

        bin_confidence = np.mean(
            confidence[mask]
        )

        bin_count = np.sum(mask)

        bin_weight = (
            bin_count / len(labels)
        )

        ece += (
            bin_weight *
            abs(
                bin_accuracy -
                bin_confidence
            )
        )

        print(
            f"{lower:.1%} - {upper:.1%}"
            f"{'':<5}"
            f"{bin_count:<10}"
            f"{bin_accuracy:.2%}"
            f"{'':<7}"
            f"{bin_confidence:.2%}"
        )

    return ece


# ==========================================
# 8. BRIER SCORE
# ==========================================

def calculate_multiclass_brier(
    probabilities,
    labels
):

    one_hot_labels = np.eye(
        probabilities.shape[1]
    )[labels]

    return np.mean(
        np.sum(
            (
                probabilities -
                one_hot_labels
            ) ** 2,
            axis=1
        )
    )


# ==========================================
# 9. CALCULATE METRICS
# ==========================================

print("\nCalculating calibration metrics...")


raw_ece = calculate_ece(
    test_probabilities,
    y_test
)

calibrated_ece = calculate_ece(
    calibrated_probabilities,
    y_test
)


raw_nll = log_loss(
    y_test,
    test_probabilities,
    labels=np.arange(
        len(label_encoder.classes_)
    )
)

calibrated_nll = log_loss(
    y_test,
    calibrated_probabilities,
    labels=np.arange(
        len(label_encoder.classes_)
    )
)


raw_brier = calculate_multiclass_brier(
    test_probabilities,
    y_test
)

calibrated_brier = calculate_multiclass_brier(
    calibrated_probabilities,
    y_test
)


raw_accuracy = np.mean(
    raw_predictions == y_test
)

calibrated_accuracy = np.mean(
    calibrated_predictions == y_test
)


raw_confidence = np.max(
    test_probabilities,
    axis=1
)

calibrated_confidence = np.max(
    calibrated_probabilities,
    axis=1
)


# ==========================================
# 10. FINAL RESULTS
# ==========================================

print("\n")
print("=" * 60)
print("MODEL CALIBRATION EVALUATION")
print("=" * 60)

print(f"\nTemperature: {temperature:.4f}")

print("\nAccuracy")
print("-" * 30)
print(
    f"Raw:        {raw_accuracy * 100:.2f}%"
)
print(
    f"Calibrated: {calibrated_accuracy * 100:.2f}%"
)

print("\nAverage Confidence")
print("-" * 30)
print(
    f"Raw:        {np.mean(raw_confidence) * 100:.2f}%"
)
print(
    f"Calibrated: {np.mean(calibrated_confidence) * 100:.2f}%"
)

print("\nExpected Calibration Error (ECE)")
print("-" * 30)
print(
    f"Raw:        {raw_ece:.6f}"
)
print(
    f"Calibrated: {calibrated_ece:.6f}"
)

print("\nNegative Log-Likelihood (NLL)")
print("-" * 30)
print(
    f"Raw:        {raw_nll:.6f}"
)
print(
    f"Calibrated: {calibrated_nll:.6f}"
)

print("\nBrier Score")
print("-" * 30)
print(
    f"Raw:        {raw_brier:.6f}"
)
print(
    f"Calibrated: {calibrated_brier:.6f}"
)

print("\n")
print("=" * 60)


# ==========================================
# 11. AUTOMATIC INTERPRETATION
# ==========================================

print("\nCalibration Interpretation")
print("-" * 30)

if calibrated_ece < raw_ece:
    print("✓ ECE improved")
else:
    print("✗ ECE did not improve")

if calibrated_nll < raw_nll:
    print("✓ NLL improved")
else:
    print("✗ NLL did not improve")

if calibrated_brier < raw_brier:
    print("✓ Brier Score improved")
else:
    print("✗ Brier Score did not improve")

print("\nEvaluation completed successfully.")