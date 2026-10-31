from uncertainty import classify_confidence

test_values = [0.95, 0.75, 0.45]

for value in test_values:
    result = classify_confidence(value)

    print(
        f"Score: {value * 100:.2f}% "
        f"→ {result}"
    )
    