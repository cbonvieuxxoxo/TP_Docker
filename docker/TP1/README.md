# TP1 — Communication entre microservices avec Docker

## Présentation

Deux microservices Python communiquent par une API REST :
- **Clients** fournit les informations des clients.
- Commandes fournit les commandes et appelle Clients pour récupérer le client associé.

Exemple : `GET /commandes/1` retourne le PC à 1200 avec les informations d’Alice.
La communication est synchrone : Commandes attend la réponse de Clients.

## Organisation du projet

```text
tp-microservices/
├── README.md
├── clients/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
└── commandes/
    ├── app.py
    ├── requirements.txt
    └── Dockerfile
```

| Fichier ou outil | Rôle |
|---|---|
| `app.py` | Données, routes Flask et traitement des requêtes |
| `requirements.txt` | Liste des dépendances Python |
| `Dockerfile` | Recette de construction de l’image |
| Flask | Recevoir les requêtes HTTP et retourner du JSON |
| Requests | Envoyer les requêtes HTTP vers Clients |
| Docker Desktop / WSL 2 | Exécuter les conteneurs Linux sous Windows |

Les données sont stockées dans des listes Python, sans base de données.

## Configuration

`clients/requirements.txt` :
```text
flask
```

`commandes/requirements.txt` :
```text
flask
requests
```

Dans les deux `app.py`, le bloc de démarrage doit être :
```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
```

Dans Commandes, l’adresse de Clients est configurable :
```python
CLIENTS_URL = os.getenv("CLIENTS_URL", "http://localhost:8080")
```

## Dockerfile

Les deux services utilisent la même recette :
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8080
CMD ["python", "app.py"]
```

- `FROM` : environnement de base avec Python 3.12.
- `WORKDIR` : dossier de travail dans l’image.
- `COPY requirements.txt` : copie la liste des dépendances.
- `RUN pip install` : installe les bibliothèques pendant la construction.
- `--no-cache-dir` : ne conserve pas le cache pip.
- `COPY app.py` : copie le programme dans l’image.
- `EXPOSE` : documente le port ; ne le publie pas sur Windows.
- `CMD` : lance le programme au démarrage du conteneur.

Une image est un modèle ; un conteneur est une instance de ce modèle en cours d’exécution.
Le Python et les dépendances des conteneurs sont indépendants du `.venv` Windows.

## Démarrage avec Docker

Prérequis : Docker Desktop installé et démarré, backend WSL 2 fonctionnel, ports 8080 et 8081 libres.
Arrêter les serveurs Python locaux s’ils occupent ces ports.

Exécuter les commandes dans le dossier `tp-microservices` :
```powershell
# Vérifier que le client et le moteur Docker fonctionnent
docker --version
docker info

# Construire les images
docker build -t microservice-clients ./clients
docker build -t microservice-commandes ./commandes

# Créer le réseau commun
docker network create reseau-microservices

# Démarrer les conteneurs
docker run -d --name clients --network reseau-microservices -p 8080:8080 microservice-clients
docker run -d --name commandes --network reseau-microservices -p 8081:8080 -e CLIENTS_URL=http://clients:8080 microservice-commandes

# Vérifier le résultat
docker ps
```

Ces commandes de création supposent que les conteneurs et le réseau n’existent pas déjà.

| Option | Signification |
|---|---|
| `build -t` | Construire une image et lui donner un nom |
| `./clients` / `./commandes` | Dossier utilisé comme contexte de construction |
| `-d` | Exécution en arrière-plan |
| `--name` | Nom du conteneur |
| `--network` | Réseau du conteneur |
| `-p` | Mapping `PORT_WINDOWS:PORT_CONTENEUR` |
| `-e` | Définition d’une variable d’environnement |

### Ports et communication

| Service | Depuis Windows | Dans Docker |
|---|---|---|
| Clients | `http://localhost:8080` | `http://clients:8080` |
| Commandes | `http://localhost:8081` | Port interne 8080 |

Le réseau personnalisé permet à Commandes de joindre Clients par son nom.
Dans un conteneur, `localhost` désigne ce conteneur lui-même.
Les mappings utilisés publient les ports sur les interfaces de Windows ; l’accès distant dépend notamment du pare-feu.

## API et tests

| Route | Réponse |
|---|---|
| `GET /clients` | Tous les clients |
| `GET /clients/<id>` | Un client |
| `GET /commandes` | Toutes les commandes, avec leur `client_id` |
| `GET /commandes/<id>` | Une commande enrichie avec son client |

```powershell
curl.exe -i http://localhost:8080/clients
curl.exe -i http://localhost:8080/clients/1
curl.exe -i http://localhost:8081/commandes
curl.exe -i http://localhost:8081/commandes/1
```

`curl.exe` évite un éventuel alias PowerShell ; `-i` affiche les en-têtes et le statut HTTP.

Réponse attendue pour `/commandes/1` :
```json
{
  "id": 1,
  "produit": "PC",
  "montant": 1200,
  "client": {"id": 1, "nom": "Alice", "pays": "France"}
}
```

### Gestion des erreurs

| Statut | Situation prévue dans le code |
|---|---|
| 404 | Client ou commande introuvable |
| 503 | Exception de communication avec Clients, notamment connexion impossible ou timeout |
| 502 | Clients retourne un statut autre que 200 ou 404 |

```powershell
# Ressources inexistantes : réponse attendue 404
curl.exe -i http://localhost:8080/clients/100
curl.exe -i http://localhost:8081/commandes/100

# Clients indisponible : réponse attendue 503
docker stop clients
curl.exe -i http://localhost:8081/commandes/1

# Rétablir le service, attendre quelques secondes puis retester : 200
docker start clients
curl.exe -i http://localhost:8081/commandes/1
```

La route `/commandes` reste disponible lorsque Clients est arrêté : elle n’effectue pas d’appel externe.
Le cas 502 n’est pas déclenché par l’arrêt de Clients ; il nécessite une réponse HTTP inattendue du service.

## Commandes utiles

```powershell
# Images et conteneurs, y compris ceux arrêtés
docker images
docker ps -a

# Journaux des applications
docker logs clients
docker logs commandes

# Réseau et conteneurs connectés
docker network inspect reseau-microservices

# Arrêter puis reprendre les conteneurs existants
docker stop clients commandes
docker start clients commandes

# Nettoyage facultatif : arrêter avant de supprimer
docker stop clients commandes
docker rm clients commandes
docker network rm reseau-microservices
```

Après un appel à `/commandes/1`, les logs de Clients doivent montrer `GET /clients/1`.

## Modifier le code

Le code est copié dans l’image : une modification sur Windows n’est pas automatiquement appliquée au conteneur.
Exemple pour Commandes :
```powershell
docker stop commandes
docker rm commandes
docker build -t microservice-commandes ./commandes
docker run -d --name commandes --network reseau-microservices -p 8081:8080 -e CLIENTS_URL=http://clients:8080 microservice-commandes
```

Un simple `docker restart` ne met pas à jour l’image ni le code embarqué.

## Dépannage rapide

| Problème | Vérification ou solution |
|---|---|
| Docker non reconnu | Installer Docker Desktop puis rouvrir PyCharm |
| Moteur inaccessible | Démarrer Docker Desktop et vérifier `docker info` |
| Port occupé | Arrêter les serveurs locaux ou identifier le conteneur qui utilise le port |
| Nom de conteneur déjà utilisé | Vérifier `docker ps -a`, puis reprendre ou supprimer l’existant |
| Requests introuvable en local | Installer et exécuter avec le même Python du `.venv` |
| Flask démarre sur 5000 | Éviter une configuration `flask run` non configurée ; lancer directement le script |
| Commandes retourne 503 | Vérifier Clients, le réseau commun et `CLIENTS_URL=http://clients:8080` |

## Limites et rendu

- Données en mémoire et API uniquement en lecture.
- Serveur de développement Flask : pas une configuration de production.
- Absence d’authentification et de HTTPS.
- Dépendances non figées.
- Dépendance synchrone de la commande enrichie envers Clients.
- Une réponse 200 de Clients contenant un JSON invalide n’est pas explicitement gérée dans cette version.

À fournir pour le TP : les sources, les deux Dockerfile, les deux requirements.txt, les commandes utilisées, une capture des deux conteneurs actifs et une capture de l’appel REST enrichi.
