import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier

rng = np.random.default_rng(42)
n = 2000
df = pd.DataFrame({
    "age": rng.integers(18, 70, n),
    "anciennete": rng.integers(0, 15, n),
    "nombre_commandes": rng.integers(0, 40, n),
    "montant_total": rng.uniform(0, 5000, n),
    "jours_depuis_derniere_commande": rng.integers(0, 365, n),
})
df["montant_moyen"] = df["montant_total"] / df["nombre_commandes"].clip(lower=1)

score = (df["nombre_commandes"] / 40) - (df["jours_depuis_derniere_commande"] / 365) + rng.normal(0, 0.2, n)
y = (score > 0).astype(int)

FEATURES = ["age", "anciennete", "nombre_commandes", "montant_total",
            "montant_moyen", "jours_depuis_derniere_commande"]
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(df[FEATURES], y)
joblib.dump(model, "modele_commande.pkl")
print("Modèle sauvegardé")