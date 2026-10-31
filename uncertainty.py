def classify_confidence(confidence):
    """
    Convert the model's maximum softmax score into
    a simple confidence category.
    
    Note:
    This is a heuristic classification of model score,
    not a calibrated medical probability.
    """

    if confidence >= 0.80:
        return "High Confidence"

    elif confidence >= 0.60:
        return "Moderate Confidence"

    else:
        return "Low Confidence"