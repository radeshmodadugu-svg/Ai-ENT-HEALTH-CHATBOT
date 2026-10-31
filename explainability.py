import numpy as np


def get_feature_contributions(model, input_data, feature_names):
    """
    Estimate feature contributions by measuring how much the
    predicted class score changes when each active symptom
    is removed from the input.

    This is a model-based contribution score, not a causal
    medical explanation.
    """

    input_data = np.asarray(input_data, dtype=np.float32)

    # Original prediction
    original_prediction = model.predict(
        input_data.reshape(1, -1),
        verbose=0
    )[0]

    predicted_class = int(np.argmax(original_prediction))
    original_score = float(original_prediction[predicted_class])

    contributions = []

    # Only evaluate symptoms that are currently active
    active_indices = np.where(input_data > 0)[0]

    for index in active_indices:
        modified_input = input_data.copy()

        # Remove this symptom
        modified_input[index] = 0.0

        modified_prediction = model.predict(
            modified_input.reshape(1, -1),
            verbose=0
        )[0]

        modified_score = float(
            modified_prediction[predicted_class]
        )

        contribution = original_score - modified_score

        contributions.append({
            "symptom": feature_names[index],
            "contribution": float(contribution)
        })

    # Highest contribution first
    contributions.sort(
        key=lambda x: x["contribution"],
        reverse=True
    )

    return contributions