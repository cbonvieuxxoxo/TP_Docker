import os

import requests
from flask import Flask, jsonify

app = Flask(__name__)

commandes = [
    {"id": 1, "client_id": 1, "produit": "PC", "montant": 1200},
    {"id": 2, "client_id": 2, "produit": "Livre", "montant": 30},
    {"id": 3, "client_id": 1, "produit": "Casque", "montant": 80}
]

CLIENTS_URL = os.getenv("CLIENTS_URL", "http://localhost:8080")


@app.route("/commandes", methods=["GET"])
def get_commandes():
    return jsonify(commandes)


@app.route("/commandes/<int:commande_id>", methods=["GET"])
def get_commande(commande_id):
    commande = next((c for c in commandes if c["id"] == commande_id), None)

    if commande is None:
        return jsonify({"erreur": "Commande introuvable"}), 404

    try:
        response = requests.get(
            f"{CLIENTS_URL}/clients/{commande['client_id']}",
            timeout=3
        )
    except requests.exceptions.RequestException:
        return jsonify({
            "erreur": "Le microservice clients est indisponible"
        }), 503

    if response.status_code == 404:
        return jsonify({
            "erreur": "Client introuvable"
        }), 404

    if response.status_code != 200:
        return jsonify({
            "erreur": "Erreur lors de la communication avec le microservice clients"
        }), 502

    client = response.json()

    resultat = {
        "id": commande["id"],
        "produit": commande["produit"],
        "montant": commande["montant"],
        "client": client
    }

    return jsonify(resultat)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)