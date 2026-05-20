#!/bin/bash

echo "=========================================================="
echo "    🚀 INSTALLATION DE L'ENVIRONNEMENT (LINUX/MAC) 🚀"
echo "=========================================================="

echo "[1/4] Vérification de Python 3..."
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

echo "[2/4] Création du Virtual Environment (venv)..."
python3 -m venv venv
source venv/bin/activate

echo "[3/4] Mise à jour de pip et installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[4/4] Initialisation Terminée !"
echo "=========================================================="
echo "Vous pouvez maintenant lancer le système."
echo "Pour simuler l'extraction de données et entraîner XGBoost :"
echo "python ecommerce_price_prediction.py"
echo ""
echo "Pour démarrer l'API FastAPI :"
echo "python -m uvicorn api_predictions:app --reload"
echo "L'API sera disponible sur : http://localhost:8000/docs"
echo "=========================================================="
