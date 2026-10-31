import tensorflow as tf
import joblib
import numpy as np
import pandas as pd

from followup_questions import (
    get_followup_question,
    get_multilingual_followup_question,
    get_symptom_group
)

from red_flags import RED_FLAG_SYMPTOMS


# ============================================================
# LOAD MODEL
# ============================================================

model = tf.keras.models.load_model(
    "ent_dl_model.keras"
)

feature_names = joblib.load(
    "ent_features.joblib"
)

label_encoder = joblib.load(
    "ent_label_encoder.joblib"
)


# ============================================================
# ENTROPY
# ============================================================

def calculate_entropy(probabilities):

    probabilities = np.asarray(
        probabilities,
        dtype=np.float64
    )

    probabilities = np.clip(
        probabilities,
        1e-10,
        1.0
    )

    return float(
        -np.sum(
            probabilities *
            np.log(probabilities)
        )
    )


# ============================================================
# ADAPTIVE FOLLOW-UP ENGINE
# ============================================================

def get_best_followup(
    current_symptoms,
    asked_questions=None,
    language="English"
):
    """
    Adaptive Follow-Up Question Engine.

    Candidate selection is based on:

    1. Information gain
    2. Disease-class change
    3. Symptom-group relevance
    4. Previously asked question filtering

    Red-flag symptoms are excluded from normal
    adaptive questioning because they are handled
    by the independent safety layer.
    """

    # --------------------------------------------------------
    # Previously asked questions
    # --------------------------------------------------------

    if asked_questions is None:
        asked_questions = []

    asked_questions_normalized = {
        question.strip().lower()
        for question in asked_questions
        if question
    }

    # --------------------------------------------------------
    # Current symptoms
    # --------------------------------------------------------

    normalized_symptoms = {
        symptom.strip().lower()
        for symptom in current_symptoms
        if symptom
    }

    # --------------------------------------------------------
    # Current feature vector
    # --------------------------------------------------------

    input_data = np.zeros(
        len(feature_names),
        dtype=np.float32
    )

    for symptom in normalized_symptoms:

        if symptom in feature_names:

            index = feature_names.index(
                symptom
            )

            input_data[index] = 1.0

    # --------------------------------------------------------
    # Determine user's symptom groups
    # --------------------------------------------------------

    user_groups = set()

    for symptom in normalized_symptoms:

        group = get_symptom_group(
            symptom
        )

        if group is not None:
            user_groups.add(group)

    # --------------------------------------------------------
    # Current model prediction
    # --------------------------------------------------------

    input_df = pd.DataFrame(
        [input_data],
        columns=feature_names
    )

    predictions = model.predict(
        input_df,
        verbose=0
    )[0]

    current_index = int(
        np.argmax(predictions)
    )

    current_confidence = float(
        predictions[current_index]
    )

    current_entropy = calculate_entropy(
        predictions
    )

    results = []

    # ========================================================
    # TEST EVERY POSSIBLE CANDIDATE
    # ========================================================

    for i, symptom in enumerate(feature_names):

        symptom_normalized = (
            symptom.strip().lower()
        )

        # ----------------------------------------------------
        # Skip already reported symptoms
        # ----------------------------------------------------

        if input_data[i] == 1.0:
            continue

        # ----------------------------------------------------
        # Skip RED-FLAG symptoms
        #
        # These are handled by red_flags.py instead.
        # ----------------------------------------------------

        if symptom_normalized in RED_FLAG_SYMPTOMS:
            continue

        # ----------------------------------------------------
        # Get question
        # ----------------------------------------------------

        question = get_multilingual_followup_question(
            symptom, language
        )

        if question is None:
            continue

        # ----------------------------------------------------
        # Skip previously asked questions
        # ----------------------------------------------------

        if (
            question.strip().lower()
            in asked_questions_normalized
        ):
            continue

        # ----------------------------------------------------
        # Candidate symptom group
        # ----------------------------------------------------

        candidate_group = get_symptom_group(
            symptom
        )

        # ----------------------------------------------------
        # Clinical-group relevance
        # ----------------------------------------------------

        if candidate_group in user_groups:
            relevance_score = 1.0
        else:
            relevance_score = 0.0

        # ----------------------------------------------------
        # Simulate candidate symptom
        # ----------------------------------------------------

        test_input = input_data.copy()

        test_input[i] = 1.0

        test_df = pd.DataFrame(
            [test_input],
            columns=feature_names
        )

        test_predictions = model.predict(
            test_df,
            verbose=0
        )[0]

        # ----------------------------------------------------
        # Simulated disease
        # ----------------------------------------------------

        test_index = int(
            np.argmax(test_predictions)
        )

        test_confidence = float(
            test_predictions[test_index]
        )

        test_disease = (
            label_encoder
            .inverse_transform(
                [test_index]
            )[0]
        )

        # ----------------------------------------------------
        # Simulated entropy
        # ----------------------------------------------------

        test_entropy = calculate_entropy(
            test_predictions
        )

        # ----------------------------------------------------
        # Information gain
        # ----------------------------------------------------

        information_gain = (
            current_entropy
            - test_entropy
        )

        # ----------------------------------------------------
        # Disease class change
        # ----------------------------------------------------

        disease_change = (
            1.0
            if test_index != current_index
            else 0.0
        )

        # ----------------------------------------------------
        # Prediction change
        # ----------------------------------------------------

        prediction_change = abs(
            test_predictions[current_index]
            - predictions[current_index]
        )

        # ----------------------------------------------------
        # Final information score
        # ----------------------------------------------------

        information_score = (
            information_gain
            + (0.10 * disease_change)
            + (0.25 * relevance_score)
        )

        results.append({

            "symptom":
                symptom,

            "question":
                question,

            "disease":
                str(test_disease),

            "confidence":
                float(test_confidence),

            "change":
                float(prediction_change),

            "disease_change":
                float(disease_change),

            "current_entropy":
                float(current_entropy),

            "test_entropy":
                float(test_entropy),

            "information_gain":
                float(information_gain),

            "relevance_score":
                float(relevance_score),

            "candidate_group":
                candidate_group,

            "information_score":
                float(information_score),

            "current_confidence":
                float(current_confidence)
        })

    # ========================================================
    # NO QUESTION AVAILABLE
    # ========================================================

    if not results:
        return None

    # ========================================================
    # SORT BY INFORMATION SCORE
    # ========================================================

    results.sort(
        key=lambda x: x["information_score"],
        reverse=True
    )

    return results[0]