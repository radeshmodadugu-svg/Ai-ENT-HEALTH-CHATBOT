from followup_engine import get_best_followup


current_symptoms = [
    "sore throat",
    "fever"
]


result = get_best_followup(current_symptoms)


print("\nBEST FOLLOW-UP QUESTION")
print("-----------------------")

if result:
    print("Symptom:", result["symptom"])
    print("Question:", result["question"])
    print("Importance:", result["change"])
else:
    print("No follow-up question found.")