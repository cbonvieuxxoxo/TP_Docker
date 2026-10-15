import json
import os
import time
import joblib
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer

BROKER = os.environ.get("KAFKA_BROKER", "kafka:9092")
TOPIC_IN = "prediction_request"
TOPIC_OUT = "prediction_result"
FEATURES = ["age", "anciennete", "nombre_commandes", "montant_total",
            "montant_moyen", "jours_depuis_derniere_commande"]

model = joblib.load("modele_commande.pkl")

consumer = producer = None
for _ in range(10):
    try:
        consumer = KafkaConsumer(
            TOPIC_IN,
            bootstrap_servers=[BROKER],
            group_id="prediction-group",
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        producer = KafkaProducer(
            bootstrap_servers=[BROKER],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        print("Connecté à Kafka.", flush=True)
        break
    except Exception as e:
        print(f"En attente de Kafka ({e})...", flush=True)
        time.sleep(3)

print("Service prediction en attente...", flush=True)
for message in consumer:
    data = message.value
    X = pd.DataFrame([{f: data[f] for f in FEATURES}])
    prediction = model.predict(X)[0]
    probabilite = model.predict_proba(X)[0][1]

    print("Client :", data["client_id"])
    print("Prediction :", prediction)
    print("Probabilite :", probabilite, flush=True)

    resultat = {
        "client_id": data["client_id"],
        "prediction": int(prediction),
        "probabilite_commande": float(probabilite),
    }
    producer.send(TOPIC_OUT, value=resultat)
    producer.flush()