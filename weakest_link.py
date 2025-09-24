import numpy as np

# Old script

def get_risk_ratings():
    ratings = []
    for i in range(6):
        while True:
            try:
                rating = float(input(f"Inserisci il rating di rischio {i + 1}: "))
                ratings.append(rating)
                break
            except ValueError:
                print("Per favore, inserisci un numero valido.")
    return ratings

def calculate_weights(ratings):
    ratings = np.array(ratings)  # Convertire la lista in array NumPy
    n = len(ratings)
    base_weight = 1 / n
    weights = np.full(n, base_weight)

    # Amplificare i pesi basati sui rating usando una funzione logaritmica
    max_rating = np.max(ratings)
    amplified_weights = weights * (1 + np.log1p(ratings / max_rating))

    # Normalizzare i pesi
    normalized_weights = amplified_weights / np.sum(amplified_weights)
    return normalized_weights

def calculate_weighted_average(ratings, weights):
    weighted_average = np.sum(ratings * weights)
    return weighted_average

def main():
    ratings = get_risk_ratings()
    weights = calculate_weights(ratings)
    weighted_average = calculate_weighted_average(ratings, weights)
    print(f"I rating di rischio inseriti sono: {ratings}")
    print(f"I pesi calcolati sono: {weights}")
    print(f"La media ponderata dei rating di rischio è: {weighted_average}")

if __name__ == "__main__":
    main()