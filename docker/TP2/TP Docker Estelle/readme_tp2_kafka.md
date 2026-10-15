# TP 2 : Architecture Événementielle avec Apache Kafka et Docker

Ce projet met en œuvre une architecture microservices orientée événements (*Event-Driven Architecture*) en Python (Flask) conteneurisée avec Docker et orchestrée via Apache Kafka.

---

## 1. Contexte & Objectifs

Dans le TP précédent (TP 1), la communication entre microservices s'effectuait de manière **synchrone via des requêtes HTTP REST directes**, ce qui entraînait un fort couplage : une indisponibilité du service `clients` bloquait la transmission.

Ce TP 2 remplace cette communication directe par une approche **asynchrone à couplage lâche** grâce à un broker **Apache Kafka** :
* Le microservice `commandes` agit en tant que **Producteur** (*Producer*).
* Le microservice `clients` agit en tant que **Consommateur** (*Consumer*).
* Kafka gère la persistance et le routage des messages via le topic `commandes-creees`.

---

## 2. Architecture Globale

```
                  Réseau Docker : reseau-kafka
 ┌─────────────────────────────────────────────────────────────┐
 │                                                             │
 │  ┌─────────────────┐       publie       ┌────────────────┐  │
 │  │   commandes     │ ─────────────────> │  Apache Kafka  │  │
 │  │   (Flask / :8081)│                    │  topic:        │  │
 │  └─────────────────┘                    │  commandes-    │  │
 │         ▲                               │  creees        │  │
 │         │ POST /commandes               └────────────────┘  │
 │         │                                       │           │
 │  Utilisateur / Client                           │ consomme  │
 │         │                                       ▼           │
 │         │ GET /clients/<id>/total       ┌────────────────┐  │
 │         ▼                               │    clients     │  │
 │  ┌─────────────────┐                    │ (Flask / :8080)│  │
 │  │  Consultation   │                    └────────────────┘  │
 │  └─────────────────┘                                        │
 └─────────────────────────────────────────────────────────────┘
```

### Format d'un Événement (`commandes-creees`)
Lorsqu'une commande est créée, l'événement suivant est sérialisé en JSON et expédié au broker :
```json
{
  "commande_id": 4,
  "client_id": 2,
  "produit": "PC",
  "montant": 1200
}
```

---

## 3. Structure du Projet

```text
tp-microservices/
├── docker-compose.yml          # Déploiement du broker Kafka (mode KRaft)
├── commandes/
│   ├── Dockerfile
│   ├── requirements.txt        # flask, requests, kafka-python-ng
│   └── app.py                  # API REST + Producteur Kafka
└── clients/
    ├── Dockerfile
    ├── requirements.txt        # flask, kafka-python-ng
    └── app.py                  # API REST + Consommateur Kafka (Thread d'écoute)
```

---

## 4. Déploiement et Démarrage

### Étape 1 : Démarrer Kafka
Depuis la racine `tp-microservices` :
```powershell
docker compose up -d
```
*Vérification :*
```powershell
docker ps
```
Le conteneur `kafka` doit être affiché avec le statut `Up` et le port `9092` exposé.

---

### Étape 2 : Construire et Lancer le Microservice `commandes`
```powershell
cd commandes
docker build -t microservice-commandes .
docker run -d -p 8081:8080 --name commandes --network reseau-kafka microservice-commandes
cd ..
```

---

### Étape 3 : Construire et Lancer le Microservice `clients`
```powershell
cd clients
docker build -t microservice-clients .
docker run -d -p 8080:8080 --name clients --network reseau-kafka microservice-clients
cd ..
```

---

## 5. Validation et Scénarios de Test

### Test 1 : Émission d'une commande (Producteur)
Création d'une commande pour le client 2 (achat d'un PC à 1 200 €) :
```powershell
Invoke-RestMethod -Uri http://localhost:8081/commandes -Method Post -ContentType "application/json" -Body '{"client_id": 2, "produit": "PC", "montant": 1200}'
```
*Réponse attendue :*
```text
commande                                        message
--------                                        -------
@{client_id=2; id=4; montant=1200; produit=PC} Commande créée et événement publié
```

### Test 2 : Émission d'une seconde commande
Création d'une commande pour le client 1 (achat d'un Livre à 30 €) :
```powershell
Invoke-RestMethod -Uri http://localhost:8081/commandes -Method Post -ContentType "application/json" -Body '{"client_id": 1, "produit": "Livre", "montant": 30}'
```

### Test 3 : Vérification de la consommation et de l'agrégation
Interrogation du service `clients` sur les totaux calculés en tâche de fond :
```powershell
Invoke-RestMethod -Uri http://localhost:8080/clients/1/total -Method Get
Invoke-RestMethod -Uri http://localhost:8080/clients/2/total -Method Get
```
*Résultats :*
* Client 1 : `total_depense: 30`
* Client 2 : `total_depense: 1200`

---

## 6. Preuve de Résilience et Découplage Temporel (Section 1.6)

1. **Arrêt du consommateur :**
   ```powershell
   docker stop clients
   ```
2. **Production de messages hors-ligne :**
   Le service `commandes` continue d'accepter des commandes et de publier ses événements sans échec ni blocage HTTP. Les messages sont persistés par Kafka.
3. **Redémarrage du consommateur :**
   ```powershell
   docker start clients
   ```
4. Grâce à la configuration `auto_offset_reset='earliest'`, le consommateur relit l'historique non traité et met à jour les compteurs sans aucune perte d'information.

---

## 7. Nettoyage de l'Environnement

Pour arrêter et supprimer proprement l'ensemble des conteneurs et réseaux :
```powershell
docker stop clients commandes
docker rm clients commandes
docker compose down
```