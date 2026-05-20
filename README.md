# 🔮 E-commerce Price Monitoring & Prediction API

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103.1-009688.svg?logo=fastapi)
![XGBoost](https://img.shields.io/badge/XGBoost-1.7.6-blue)
![Docker](https://img.shields.io/badge/Docker-Enabled-brightgreen?logo=docker)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Un projet de qualité production ("Production-Ready") conçu pour extraire de la donnée e-commerce, en assurer la gestion temporelle (Time-Series) et générer des prédictions à 7 jours grâce au machine learning (XGBoost).

---

## 🚀 Démarrage Rapide (En 5 min)

### Option 1 : Scripts Automatisés (Recommandé en local)
Le projet contient des scripts plug-and-play qui créent un environnement virtuel, installent les dépendances, et démarrent l'API :

**Sous Windows :**
```cmd
.\setup.bat
```

**Sous Linux / MacOS :**
```bash
chmod +x setup.sh
./setup.sh
```

### Option 2 : Docker (Recommandé pour la Production)
Le projet est entièrement conteneurisé.
```bash
docker-compose up --build -d
```
L'API sera disponible sur `http://localhost:8000`.

### Option 3 : Installation Manuelle
```bash
# 1. Créer le venv
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sous Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Récolter la donnée primaire & entraîner le modèle
python ecommerce_price_prediction.py

# 4. Lancer l'API
python -m uvicorn api_predictions:app --reload
```

---

## ✨ Features ML Principales
- **Web Scraping Asynchrone :** Géré via `aiohttp` et `BeautifulSoup` (avec mode simulation si blocage anti-bot).
- **Time-Series Database :** Prise en charge native de SQLite et PostgreSQL via SQLAlchemy.
- **Ingénierie des Caractéristiques (15+ Features) :** Volatilité, moyennes mobiles (3, 7 jours), encodage temporel cyclique (sin/cos de la semaine).
- **Modèle IA (XGBoost) :** Optimisé pour l'historique des prix, évalué via l'erreur MAPE (~6%).
- **Endpoints FastAPI (15+) :** Accès CRUD aux produits et génération sécurisée des prédictions.

## 📖 Interface API (Swagger & ReDoc)
Une fois le serveur lancé, vous avez accès à une interface interactive pour tester les requêtes :
- **Swagger UI** : `http://localhost:8000/docs`
- **ReDoc** : `http://localhost:8000/redoc`

Pour plus de détails architecturaux, ouvrez le fichier `GUIDE_PROJET_ECOMMERCE.md`.
