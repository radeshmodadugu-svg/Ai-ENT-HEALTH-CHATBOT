import tensorflow as tf
import joblib
import numpy as np
from explainability import get_feature_contributions


model = tf.keras.models.load_model("ent_dl_model.keras")
feature_names = joblib.load("ent_features.joblib")


# Test symptoms
test_symptoms = [
    "sore throat",
    "fever"
]


input_data = np.zeros(
    len(feature_names),
    dtype=np.float32
)


for symptom in test_symptoms:
    symptom = symptom.lower().strip()

    if symptom in feature_names:
        index = feature_names.index(symptom)
        input_data[index] = 1.0


contributions = get_feature_contributions(
    model,
    input_data,
    feature_names
)


print("\nMODEL FEATURE CONTRIBUTIONS")
print("----------------------------")

for item in contributions:
    print(
        f"{item['symptom']}: "
        f"{item['contribution']:.4f}"
    )