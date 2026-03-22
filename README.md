# 🛰️ Thread GPS Tracking Platform

## ▶️ Lancer le projet (5 commandes)

```bash
## ▶️ Lancer le projet

Suivez ces étapes simples pour démarrer le projet en local :

```bash
# Créer un dossier pour le projet
mkdir GPS-Tracking

# Entrer dans le dossier
cd GPS-Tracking

# Cloner le dépôt GitHub
git clone https://github.com/ELMOUWAHID-AYOUB/IoT-live-monitoring.git

# Entrer dans le projet cloné
cd IoT-live-monitoring

# Lancer l'application avec Docker
docker-compose up --build
```

Puis ouvrir : **http://localhost:3000**

---

## 📁 Structure

```

---

## 🔌 Services

| Service | URL | Rôle |
|---------|-----|------|
| WebUI | http://localhost:3000 | Interface utilisateur |
| API + Docs | http://localhost:8000/docs | FastAPI Swagger |
| PostgreSQL | localhost:5432 | Base de données |
| MQTT | localhost:1883 | Broker Mosquitto |

<img width="945" height="370" alt="Image" src="https://github.com/user-attachments/assets/4299631a-53a0-4ae8-8765-b5cace0c686f" />

<img width="945" height="450" alt="Image" src="https://github.com/user-attachments/assets/bc3c7b05-46ab-4373-80d0-2cbc84df99a8" />


<img width="945" height="303" alt="Image" src="https://github.com/user-attachments/assets/37079517-6265-44e1-a0a0-64f3fc473e7a" />
---

## 🌐 Réseau Thread IPv6 simulé

| Rôle | Adresse IPv6 | Ressource CoAP |
|------|-------------|----------------|
| Leader | fd00:db8::1 | — |
| Router | fd00:db8::2 | — |
| End Device GPS | fd00:db8::10 | coap://[fd00:db8::10]:5683/gps |
| End Device Batterie | fd00:db8::11 | coap://[fd00:db8::11]:5683/battery |
| End Device Température | fd00:db8::12 | coap://[fd00:db8::12]:5683/temperature |


<img width="945" height="505" alt="Image" src="https://github.com/user-attachments/assets/41d0d035-891e-4e73-80c2-6c88e207b6ae" />


---

## 📊 Flux de données

```
Flux 1 : WebUI → POST /api/runners → FastAPI → PostgreSQL
Flux 2 : FastAPI → GET coap://[fd00:db8::10]:5683/gps (simulé)
Flux 3 : FastAPI → MQTT /tracking/{id}/gps → Mosquitto
```

---

## ✅ Validation des plages

| Capteur | Plage |
|---------|-------|
| GPS Latitude | [-90, 90]° |
| GPS Longitude | [-180, 180]° |
| Batterie | [0, 100]% |
| Température | [-40, 40]°C |

<img width="945" height="197" alt="Image" src="https://github.com/user-attachments/assets/fb8c8e33-8cb0-45cd-97a7-148c28d72a57" />

---

## 🧪 Tests rapides

```bash
# Health check
curl http://localhost:8000/health

# Créer un coureur
curl -X POST http://localhost:8000/api/runners \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@test.com"}'

# Démarrer une session
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"runner_id":1}'

# Poll CoAP (simule lecture des 3 noeuds Thread)
curl -X POST http://localhost:8000/api/coap/poll/1

<img width="945" height="330" alt="Image" src="https://github.com/user-attachments/assets/877968c9-f9c0-4b07-a49e-8d23e684fd04" />


```
├───docker-compose.yml
├───README.md
│
├───docker
│   ├───mosquitto.conf
│
├───src
│   ├───backend
│   │   │   Dockerfile
│   │   │   main.py
│   │   │   requirements.txt
│   │   │
│   │   └───app
│   │       │   database.py
│   │       │   main.py
│   │       │   requirements.txt
│   │       │
│   │       ├───routers
│   │       │       measurements.py
│   │       │       network.py
│   │       │       runners.py
│   │       │       sessions.py
│   │       │
│   │       └───services
│   │               coap_service.py
│   │               haversine.py
│   │               mqtt_service.py
│   │               polling_service.py
│   │               validation.py
│   │
│   ├───docker
│   │   └───mosquitto.conf
│   ├───frontend
│   │       Dockerfile
│   │       index.html
│   │
│   └───thread_nodes
│       ├───battery
│       │       Dockerfile
│       │       node_battery.py
│       │       requirements.txt
│       │
│       ├───gps
│       │       Dockerfile
│       │       node_gps.py
│       │       requirements.txt
│       │
│       ├───leader
│       │       Dockerfile
│       │       node_leader.py
│       │       requirements.txt
│       │
│       ├───router
│       │       Dockerfile
│       │       node_router.py
│       │       requirements.txt
│       │
│       └───temperature
│               Dockerfile
│               node_temperature.py
│               requirements.txt
│
└───tests
        test_all.py
---

## 🏗️ Justification PostgreSQL

- Les données sont bien organisées : chaque coureur est lié à ses sessions, et chaque session contient ses mesures (grâce aux relations entre tables).
- La base garantit la fiabilité des données (ACID) : aucune perte ou duplication des informations GPS.
- Elle permet de faire facilement des analyses avancées, comme calculer la distance totale ou consulter l’historique d’une session.


