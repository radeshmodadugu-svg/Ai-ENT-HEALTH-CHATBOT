import numpy as np
import pandas as pd
import tensorflow as tf
import joblib

from sklearn.model_selection import train_test_split
from scipy.optimize import minimize_scalar


# ==========================================
# 1. LOAD DATA
# ==========================================

print("Loading ENT dataset...")

df = pd.read_csv("ENT_Filtered_Dataset.csv")

X = df.drop(columns=["diseases"]).astype(np.float32)
y_raw = df["diseases"]

# Load the same label encoder used by the model
label_encoder = joblib.load("ent_label_encoder.joblib")

y_encoded = label_encoder.transform(y_raw)

print(f"Dataset shape: {X.shape}")
print(f"Number of classes: {len(label_encoder.classes_)}")


# ==========================================
# 2. RECREATE THE ORIGINAL DATA SPLIT
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
# 3. LOAD EXISTING TRAINED MODEL
# ==========================================

print("\nLoading trained model...")

model = tf.keras.models.load_model("ent_dl_model.keras")

print("Model loaded successfully.")


# ==========================================
# 4. GET VALIDATION PREDICTIONS
# ==========================================

print("\nGenerating validation predictions...")

val_probabilities = model.predict(
    X_val,
    verbose=0
)

test_probabilities = model.predict(
    X_test,
    verbose=0
)


# ==========================================
# 5. CONVERT PROBABILITIES TO LOGITS
# ==========================================

# Avoid log(0)
epsilon = 1e-7

val_probabilities = np.clip(
    val_probabilities,
    epsilon,
    1.0
)

test_probabilities = np.clip(
    test_probabilities,
    epsilon,
    1.0
)

val_logits = np.log(val_probabilities)
test_logits = np.log(test_probabilities)


# ==========================================
# 6. CALCULATE NLL FOR A TEMPERATURE
# ==========================================

def temperature_nll(temperature):

    scaled_logits = val_logits / temperature

    log_probs = (
        scaled_logits
        - tf.reduce_logsumexp(
            scaled_logits,
            axis=1,
            keepdims=True
        ).numpy()
    )

    negative_log_likelihood = -np.mean(
        log_probs[
            np.arange(len(y_val)),
            y_val
        ]
    )

    return negative_log_likelihood


# ==========================================
# 7. FIND OPTIMAL TEMPERATURE
# ==========================================

print("\nFinding optimal temperature...")

result = minimize_scalar(
    temperature_nll,
    bounds=(0.05, 10.0),
    method="bounded"
)

temperature = float(result.x)

print(f"Optimal temperature: {temperature:.4f}")


# ==========================================
# 8. CALIBRATE TEST PREDICTIONS
# ==========================================

calibrated_test_logits = test_logits / temperature

calibrated_test_probabilities = tf.nn.softmax(
    calibrated_test_logits,
    axis=1
).numpy()


# ==========================================
# 9. RAW vs CALIBRATED CONFIDENCE
# ==========================================

raw_predictions = np.argmax(
    test_probabilities,
    axis=1
)

calibrated_predictions = np.argmax(
    calibrated_test_probabilities,
    axis=1
)

raw_confidence = np.max(
    test_probabilities,
    axis=1
)

calibrated_confidence = np.max(
    calibrated_test_probabilities,
    axis=1
)


# ==========================================
# 10. ACCURACY
# ==========================================

raw_accuracy = np.mean(
    raw_predictions == y_test
)

calibrated_accuracy = np.mean(
    calibrated_predictions == y_test
)


# ==========================================
# 11. PRINT RESULTS
# ==========================================

print("\n==========================================")
print("MODEL CALIBRATION RESULTS")
print("==========================================")

print(f"Optimal Temperature: {temperature:.4f}")

print(f"\nRaw Model Accuracy:")
print(f"{raw_accuracy * 100:.2f}%")

print(f"\nCalibrated Accuracy:")
print(f"{calibrated_accuracy * 100:.2f}%")

print(f"\nAverage Raw Confidence:")
print(f"{np.mean(raw_confidence) * 100:.2f}%")

print(f"\nAverage Calibrated Confidence:")
print(f"{np.mean(calibrated_confidence) * 100:.2f}%")

print("\n==========================================")
print("Example Predictions")
print("==========================================")

for i in range(min(10, len(y_test))):

    actual = label_encoder.inverse_transform(
        [y_test[i]]
    )[0]

    raw_prediction = label_encoder.inverse_transform(
        [raw_predictions[i]]
    )[0]

    calibrated_prediction = label_encoder.inverse_transform(
        [calibrated_predictions[i]]
    )[0]

    print("\nExample", i + 1)

    print("Actual:", actual)

    print(
        "Raw:",
        raw_prediction,
        f"({raw_confidence[i] * 100:.2f}%)"
    )

    print(
        "Calibrated:",
        calibrated_prediction,
        f"({calibrated_confidence[i] * 100:.2f}%)"
    )


# ==========================================
# 12. SAVE CALIBRATION TEMPERATURE
# ==========================================

joblib.dump(
    temperature,
    "calibration_temperature.joblib"
)

print("\nCalibration temperature saved to:")
print("calibration_temperature.joblib")

print("\nCalibration completed successfully.")