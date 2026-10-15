import json
import os
import threading
import time
from flask import Flask, jsonify
from kafka import KafkaConsumer

app = Flask(__name__)

# Base statique des clients imposée par le TP
clients = [
    {"id": 1, "nom": "Alice", "pays": "France"},
    {"id": 2, "nom": "Alex", "pays": "Belgique"},
    {"id": 3, "nom": "Madeleine", "pays": "France"}
]

# Dictionnaire en mémoire pour accumuler les montants totaux par client
totaux_clients = {}

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "kafka:9092")
TOPIC_NAME = "commandes-creees"

def consommer_evenements():
    """Fonction exécutée en arrière-plan pour écouter Kafka."""
    consumer = None
    for _ in range(10):
        try:
            consumer = KafkaConsumer(
                TOPIC_NAME,
                bootstrap_servers=[KAFKA_BROKER],
                auto_offset_reset='earliest',  # Lit depuis le début pour récupérer les messages déjà envoyés
                enable_auto_commit=True,
                group_id='groupe-clients',
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            print("Consommateur connecté à Kafka.")
            break
        except Exception as e:
            print(f"En attente de Kafka ({e})...")
            time.sleep(3)

    if not consumer:
        print("Impossible de se connecter au broker Kafka.")
        return

    # Boucle de lecture infinie des messages
    for message in consumer:
        evenement = message.value
        client_id = evenement.get("client_id")
        montant = evenement.get("montant", 0)

        # Mise à jour du total cumulé pour le client
        totaux_clients[client_id] = totaux_clients.get(client_id, 0) + montant

        # Affichage demandé dans la consigne du TP
        print(f"\n[ÉVÉNEMENT REÇU] Commande #{evenement.get('commande_id')}")
        print(f" -> Client {client_id} a commandé '{evenement.get('produit')}' pour un montant de {montant}€")
        print(f" -> Total dépensé par le client {client_id} : {totaux_clients[client_id]}€\n")

# Lancement du consommateur Kafka dans un thread séparé
thread = threading.Thread(target=consommer_evenements, daemon=True)
thread.start()

@app.route('/clients', methods=['GET'])
def get_clients():
    return jsonify(clients), 200

@app.route('/clients/<int:client_id>', methods=['GET'])
def get_client(client_id):
    client = next((c for c in clients if c["id"] == client_id), None)
    if client:
        return jsonify(client), 200
    return jsonify({"erreur": "Client introuvable"}), 404

# Route pour consulter les montants cumulés calculés via les événements Kafka
@app.route('/clients/<int:client_id>/total', methods=['GET'])
def get_total_client(client_id):
    total = totaux_clients.get(client_id, 0)
    return jsonify({"client_id": client_id, "total_depense": total}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)