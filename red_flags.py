RED_FLAG_SYMPTOMS = {
    "difficulty breathing",
    "shortness of breath",
    "severe breathing difficulty",
    "difficulty swallowing",
    "unable to swallow",
    "throat feels tight",
    "severe throat swelling",
    "coughing up blood",
    "blood in sputum",
    "chest pain",
    "loss of consciousness",
    "fainting",
}

RED_FLAG_MESSAGE = (
    "Some of the symptoms you reported may require prompt medical attention. "
    "Please seek medical care, especially if the symptoms are severe, worsening, "
    "or affecting your breathing or ability to swallow."
)


def check_red_flags(symptoms):
    """
    Check whether any reported symptoms match predefined red-flag symptoms.
    Returns True if a red flag is detected.
    """

    normalized_symptoms = {
        symptom.strip().lower()
        for symptom in symptoms
    }

    detected_flags = normalized_symptoms.intersection(RED_FLAG_SYMPTOMS)

    return list(detected_flags)