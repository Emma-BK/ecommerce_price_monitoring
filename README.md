# 🔮 Price Monitoring — Suivi & prédiction de prix e-commerce

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103.1-009688?logo=fastapi)
![XGBoost](https://img.shields.io/badge/XGBoost-1.7.6-orange)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)
![SQLite / PostgreSQL](https://img.shields.io/badge/DB-SQLite%20%7C%20PostgreSQL-4479A1)

API **production-ready** pour collecter, stocker et analyser l'historique des prix de produits e-commerce, puis prédire les prix à **7 jours** grâce au machine learning (XGBoost). Le projet expose une API REST FastAPI, un dashboard web et peut tourner en local ou via Docker.

---

## 📑 Sommaire

- [Fonctionnalités](#-fonctionnalités)
- [Stack technique](#-stack-technique)
- [Structure du projet](#-structure-du-projet)
- [Démarrage rapide](#-démarrage-rapide)
- [Configuration](#-configuration)
- [API REST](#-api-rest)
- [Machine Learning](#-machine-learning)
- [Dashboard web](#-dashboard-web)
- [Licence](#-licence)
- [Auteur & origine](#-auteur--origine)

---

## ✨ Fonctionnalités

- **Web scraping asynchrone** (`aiohttp` + `BeautifulSoup`) avec mode simulation si le site bloque les bots.
- **Base de données temporelle** via SQLAlchemy : SQLite par défaut (plug & play), PostgreSQL en production.
- **Ingénierie des features** : moyennes mobiles (3 et 7 jours), volatilité, codesPromo, encodage cyclique `sin/cos` de la semaine, etc.
- **Prédiction XGBoost** d'un horizon de 7 jours, avec validation par le MAPE (objectif ~6 %).
- **API REST FastAPI (16 endpoints)** : CRUD produits/historique, scraping, favoris, export, analytics, alertes et prédictions.
- **Documentation interactive** Swagger UI et ReDoc.
- **Dashboard web** statique (`static/`) servi directement par l'API.
- **Conteneurisation Docker** avec utilisateur non-root et configuration par variables d'environnement.

---

## 🧰 Stack technique

| Domaine | Technologies |
| --- | --- |
| API | FastAPI 0.103, Uvicorn, Pydantic 2 |
| Scraping | aiohttp, BeautifulSoup4, lxml |
| Data / ML | pandas, NumPy, XGBoost, scikit-learn |
| Stockage | SQLAlchemy 2, SQLite (ou PostgreSQL) |
| Viz | Matplotlib, Seaborn, Plotly |
| Ops | Docker, docker-compose, `schedule`, `python-dotenv` |

---

## 📁 Structure du projet

```text
.
├── api_predictions.py            # Application FastAPI, schémas et endpoints
├── ecommerce_price_prediction.py # Modèles SQLAlchemy, scraping et entraînement XGBoost
├── analysis_notebook.py          # Analyse exploratoire et visualisations
├── import_kaggle_data.py         # Import d'un jeu de données Kaggle
├── config.env                    # Template de configuration (à copier/adapter)
├── requirements.txt              # Dépendances Python figées
├── Dockerfile                    # Image de production (Python 3.9 slim)
├── docker-compose.yml            # Orchestration du service API
├── setup.bat / setup.sh          # Scripts d'installation automatique
├── static/                       # Dashboard web (index.html, style.css, app.js)
└── scratch/                      # Utilitaires de maintenance des images
```

---

## 🚀 Démarrage rapide

### Option 1 — Scripts automatiques (local, recommandé)

**Windows :**
```cmd
.\setup.bat
```

**Linux / macOS :**
```bash
chmod +x setup.sh
./setup.sh
```

Le script crée le virtualenv, installe les dépendances et affiche les commandes de lancement.

### Option 2 — Docker (recommandé en production)

```bash
docker-compose up --build -d
```

API disponible sur <http://localhost:8000>.

### Option 3 — Installation manuelle

```bash
python -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt

# Initialiser l'historique et entraîner le modèle
python ecommerce_price_prediction.py

# Lancer l'API
python -m uvicorn api_predictions:app --reload
```

---

## ⚙️ Configuration

Copiez/adaptez `config.env` (ou exportez les variables dans votre environnement) :

| Variable | Défaut | Description |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///ecommerce_prices.db` | Connexion SQLAlchemy (SQLite ou PostgreSQL) |
| `SCRAPER_API_KEY` | — | Clé d'un proxy type ScraperAPI / ZenRows (optionnel) |
| `USE_PROXY_ROTATION` | `False` | Active la rotation de proxies |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | Écoute du serveur |
| `API_DEBUG_MODE` | `True` | Mode debug FastAPI |
| `PREDICTION_HORIZON_DAYS` | `7` | Nombre de jours à prédire |
| `SCRAPING_INTERVAL_MINUTES` | `1440` | Fréquence de scraping |
| `MAPE_TARGET_THRESHOLD` | `0.06` | MAPE maximum accepté à l'entraînement |

> ⚠️ `config.env` est un **template** versionné : ne placez jamais de vraie clé secrète dedans. Utilisez un `.env` local (ignoré par Git).

---

## 🌐 API REST

Documentation interactive : **Swagger** <http://localhost:8000/docs> · **ReDoc** <http://localhost:8000/redoc>

| Méthode | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Dashboard web |
| `GET` | `/api/v1/health` | État de santé de l'API |
| `POST` | `/api/v1/products` | Créer un produit |
| `GET` | `/api/v1/products` | Liste des produits |
| `GET` | `/api/v1/products/{id}` | Détail d'un produit |
| `DELETE` | `/api/v1/products/{id}` | Supprimer un produit |
| `POST` | `/api/v1/products/{id}/scrape` | Déclencher un scraping |
| `POST` | `/api/v1/products/{id}/favorite` | Marquer comme favori |
| `GET` | `/api/v1/products/{id}/export` | Exporter l'historique |
| `POST` | `/api/v1/products/{id}/prices` | Ajouter un relevé de prix |
| `GET` | `/api/v1/products/{id}/prices` | Historique complet |
| `GET` | `/api/v1/products/{id}/prices/latest` | Dernier relevé |
| `POST` | `/api/v1/predict/train/{id}` | Entraîner le modèle |
| `GET` | `/api/v1/predict/{id}` | Prédictions sur 7 jours |
| `GET` | `/api/v1/analytics/{id}/volatility` | Volatilité d'un produit |
| `GET` | `/api/v1/analytics/categories` / `/analytics/global` / `/alerts` | Statistiques et alertes |

### Exemples

```bash
# Créer un produit
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"iPhone 15","url":"https://example.com/iphone15","category":"High-Tech"}'

# Entraîner le modèle puis récupérer les prédictions
curl -X POST http://localhost:8000/api/v1/predict/train/1
curl http://localhost:8000/api/v1/predict/1

# Vérifier la santé de l'API
curl http://localhost:8000/api/v1/health
```

---

## 🤖 Machine Learning

Le pipeline `ecommerce_price_prediction.py` construit un historique de prix, génère les features temporelles, entraîne **XGBoost** et n'accepte le modèle que si le MAPE respecte le seuil configuré. Les prédictions sont ensuite servies par l'API et affichées dans le dashboard.

---

## 🖥️ Dashboard web

L'interface statique dans `static/` est servie par l'API sur <http://localhost:8000> (CSS et JS inclus). Elle permet de consulter les produits, l'historique, les alertes et les prévisions.

---

## 📄 Licence

Le projet d'origine est annoncé sous licence **MIT**. Aucun fichier `LICENSE` n'étant fourni, ajoutez-en un si vous souhaitez redistribuer ce dépôt.

---

## 👤 Auteur & origine

- Maintenu par **Emma-BK** — <https://github.com/Emma-BK>
- Projet d'origine : [jaouheraya12-create/Projetecommerce_price_monitoring](https://github.com/jaouheraya12-create/Projetecommerce_price_monitoring)

⭐ N'hésitez pas à star le dépôt si vous le trouvez utile !
