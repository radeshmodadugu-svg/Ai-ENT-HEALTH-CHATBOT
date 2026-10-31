from red_flags import check_red_flags

symptoms = [
    "sore throat",
    "fever",
    "difficulty breathing"
]

flags = check_red_flags(symptoms)

print("Detected red flags:")
print(flags)