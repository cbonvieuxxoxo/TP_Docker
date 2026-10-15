import json
import os
import time
from flask import Flask, jsonify, request
import threading
from datetime import datetime, timedelta
from kafka import KafkaProducer, KafkaConsumer


app = Flask(__name__)


# Données statiques de base
commandes = [
    {"id": 1, "client_id": 1, "produit": "PC", "montant": 1200},
    {"id": 2, "client_id": 2, "produit": "Livre", "montant": 30},
    {"id": 3, "client_id": 1, "produit": "Casque", "montant": 80}
]


KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "kafka:9092")
TOPIC_NAME = "commandes-creees"
TOPIC_PRED_REQUEST = "prediction_request"
TOPIC_PRED_RESULT = "prediction_result"

# Infos clients nécessaires au modèle (absentes du service clients)
PROFILS = {
    1: {"age": 32, "anciennete": 3},
    2: {"age": 28, "anciennete": 1},
    3: {"age": 45, "anciennete": 5},
}
maintenant = datetime.now()
derniere_commande = {1: maintenant - timedelta(days=12),
                     2: maintenant - timedelta(days=30)}


# Connexion avec retry pour attendre que Kafka soit prêt au démarrage
producer = None
for _ in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("Connecté au broker Kafka.")
        break
    except Exception as e:
        print(f"En attente de Kafka ({e})...")
        time.sleep(3)


def consommer_predictions():
    consumer = None
    for _ in range(10):
        try:
            consumer = KafkaConsumer(
                TOPIC_PRED_RESULT,
                bootstrap_servers=[KAFKA_BROKER],
                group_id="groupe-commandes-prediction",
                auto_offset_reset="earliest",
                value_deserializer=lambda m: json.loads(m.decode("utf-8"))
            )
            break
        except Exception as e:
            print(f"En attente de Kafka ({e})...")
            time.sleep(3)
    if not consumer:
        return
    for message in consumer:
        r = message.value
        print(f"\n[PRÉDICTION REÇUE] Client {r['client_id']} : "
              f"prediction={r['prediction']}, "
              f"probabilité de commande={r['probabilite_commande']:.2f}\n", flush=True)


threading.Thread(target=consommer_predictions, daemon=True).start()


def construire_evenement_prediction(client_id):
    cmds = [c for c in commandes if c["client_id"] == client_id]
    nombre = len(cmds)
    total = sum(c["montant"] for c in cmds)
    maintenant = datetime.now()
    precedente = derniere_commande.get(client_id)
    jours = (maintenant - precedente).days if precedente else 0
    derniere_commande[client_id] = maintenant
    profil = PROFILS.get(client_id, {"age": 30, "anciennete": 1})
    return {
        "client_id": client_id,
        "age": profil["age"],
        "anciennete": profil["anciennete"],
        "nombre_commandes": nombre,
        "montant_total": total,
        "montant_moyen": round(total / nombre, 2),
        "jours_depuis_derniere_commande": jours
    }


@app.route('/commandes', methods=['GET'])
def get_commandes():
    return jsonify(commandes), 200


# Route POST demandée : créer une commande et publier l'événement dans Kafka
@app.route('/commandes', methods=['POST'])
def creer_commande():
    data = request.get_json()
    if not data or not all(k in data for k in ("client_id", "produit", "montant")):
        return jsonify({"erreur": "Données incomplètes (client_id, produit, montant requis)"}), 400


    nouvelle_commande = {
        "id": len(commandes) + 1,
        "client_id": data["client_id"],
        "produit": data["produit"],
        "montant": data["montant"]
    }
    commandes.append(nouvelle_commande)


    # Structure de l'événement demandée dans le TP (Section 1.2)
    evenement = {
        "commande_id": nouvelle_commande["id"],
        "client_id": nouvelle_commande["client_id"],
        "produit": nouvelle_commande["produit"],
        "montant": nouvelle_commande["montant"]
    }


    # Publication de l'événement dans le topic Kafka
    if producer:
        producer.send(TOPIC_NAME, value=evenement)
        producer.flush()
        print(f"Événement envoyé dans Kafka : {evenement}")

        # TP3 : demande de prédiction pour ce client
        evt_pred = construire_evenement_prediction(nouvelle_commande["client_id"])
        producer.send(TOPIC_PRED_REQUEST, value=evt_pred)
        producer.flush()
        print(f"Demande de prédiction envoyée : {evt_pred}")


    return jsonify({"message": "Commande créée et événement publié", "commande": nouvelle_commande}), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)