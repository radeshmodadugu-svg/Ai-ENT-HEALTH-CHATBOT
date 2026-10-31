import numpy as np
import pandas as pd

from red_flags import check_red_flags, RED_FLAG_MESSAGE


def run_what_if_prediction(
    model,
    feature_names,
    label_encoder,
    current_symptoms,
    added_symptoms=None,
    removed_symptoms=None,
    calibrate_fn=None
):
    """
    Run a what-if prediction by adding or removing symptoms
    from the current symptom set.

    This does not retrain the model.
    """

    added_symptoms = added_symptoms or []
    removed_symptoms = removed_symptoms or []

    # Normalize symptoms
    current = {
        symptom.strip().lower()
        for symptom in current_symptoms
    }

    added = {
        symptom.strip().lower()
        for symptom in added_symptoms
    }

    removed = {
        symptom.strip().lower()
        for symptom in removed_symptoms
    }

    # Create modified symptom set
    modified_symptoms = (
        current
        | added
    ) - removed

    # Safety check before running the ML prediction
    red_flags = check_red_flags(
        list(modified_symptoms)
    )

    if red_flags:
        return {
            "symptoms": sorted(
                modified_symptoms
            ),
            "prediction": "Medical Attention Recommended",
            "confidence": None,
            "red_flag": True,
            "message": RED_FLAG_MESSAGE
        }

    # Create feature vector
    input_data = np.zeros(
        len(feature_names),
        dtype=np.float32
    )

    for symptom in modified_symptoms:

        if symptom in feature_names:

            index = feature_names.index(
                symptom
            )

            input_data[index] = 1.0

    # Convert to model input
    input_df = pd.DataFrame(
        [input_data],
        columns=feature_names
    )

    # Run model
    raw_predictions = model.predict(
        input_df,
        verbose=0
    )

    # Apply probability calibration
    if calibrate_fn is not None:
        predictions = calibrate_fn(
            raw_predictions
        )[0]
    else:
        predictions = raw_predictions[0]

    # Get predicted class
    predicted_index = int(
        np.argmax(predictions)
    )

    # Get calibrated confidence
    confidence = float(
        np.max(predictions)
    )

    # Convert class index to disease name
    predicted_disease = (
        label_encoder
        .inverse_transform(
            [predicted_index]
        )[0]
    )

    return {
        "symptoms": sorted(
            modified_symptoms
        ),
        "prediction": predicted_disease,
        "confidence": round(
            confidence * 100,
            2
        )
    }