from personalized_guidance import get_personalized_guidance


def test_guidance(disease, symptoms):

    print("\n" + "=" * 60)
    print("DISEASE:", disease)
    print("=" * 60)

    print("\nSymptoms:")
    for symptom in symptoms:
        print("-", symptom)

    guidance = get_personalized_guidance(
        disease,
        symptoms
    )

    print("\nDO:")
    for item in guidance["do"]:
        print("-", item)

    print("\nDON'T:")
    for item in guidance["dont"]:
        print("-", item)

    print("\nMONITOR:")
    for item in guidance["monitor"]:
        print("-", item)


# -------------------------------------------------
# TEST CASE 1
# -------------------------------------------------

test_guidance(
    "laryngitis",
    [
        "sore throat",
        "fever",
        "hoarse voice"
    ]
)


# -------------------------------------------------
# TEST CASE 2
# -------------------------------------------------

test_guidance(
    "acute sinusitis",
    [
        "facial pain",
        "sinus congestion",
        "frontal headache"
    ]
)


# -------------------------------------------------
# TEST CASE 3
# -------------------------------------------------

test_guidance(
    "otitis externa (swimmer's ear)",
    [
        "ear pain",
        "diminished hearing"
    ]
)
