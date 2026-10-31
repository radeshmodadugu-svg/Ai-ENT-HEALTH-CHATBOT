from followup_engine import get_best_followup


def test_case(name, symptoms):

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    print("\nSymptoms:")
    for symptom in symptoms:
        print("-", symptom)

    result = get_best_followup(symptoms)

    if result is None:
        print("\nNo suitable follow-up question found.")
        return

    print("\nCurrent Confidence:")
    print(f"{result['current_confidence'] * 100:.2f}%")

    print("\nRecommended Follow-Up:")
    print(result["question"])

    print("\nTarget Symptom:")
    print(result["symptom"])

    print("\nPrediction Change:")
    print(f"{result['change']:.4f}")

    print("\nDisease Class Change:")
    print(result["disease_change"])

    print("\nInformation Score:")
    print(f"{result['information_score']:.4f}")

    print("\nInformation Gain:")
    print(f"{result['information_gain']:.4f}")

    print("\nRelevance Score:")
    print(f"{result['relevance_score']:.4f}")

    print("\nCandidate Group:")
    print(result["candidate_group"])

    print("\nSelected Disease After Simulation:")
    print(result["disease"])


# -------------------------------------------------
# TEST CASE 1
# -------------------------------------------------

test_case(
    "CASE 1 - Common Respiratory Symptoms",
    [
        "sore throat",
        "cough",
        "nasal congestion",
        "fever"
    ]
)


# -------------------------------------------------
# TEST CASE 2
# -------------------------------------------------

test_case(
    "CASE 2 - Ear Symptoms",
    [
        "ear pain",
        "diminished hearing"
    ]
)


# -------------------------------------------------
# TEST CASE 3
# -------------------------------------------------

test_case(
    "CASE 3 - Sinus Symptoms",
    [
        "facial pain",
        "sinus congestion",
        "frontal headache"
    ]
)