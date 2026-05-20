# Utiliser une image Python allégée pour des performances optimales
FROM python:3.9-slim-buster

# Définir le dossier de travail courant
WORKDIR /app

# Empêcher Python de générer des fichiers .pyc bytecode
ENV PYTHONDONTWRITEBYTECODE 1
# Ne pas bufferiser le stdout/stderr pour avoir les logs instantanément
ENV PYTHONUNBUFFERED 1

# Installer des dépendances système nécessaires, par exemple pour compiler XGBoost ou Pandas
# L'utilisation de --no-install-recommends réduit la taille de l'image
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer Requirements en premier pour bénéficier du cache des layers Docker
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copier l'intégralité du projet
COPY . .

# Exposer le port pour FastAPI
EXPOSE 8000

# Créer un utilisateur non root par soucis de sécurité (DevSecOps)
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Commande par défaut : lancer Uvicorn (Serveur ASGI)
CMD ["uvicorn", "api_predictions:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
