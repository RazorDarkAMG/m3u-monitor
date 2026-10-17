FROM python:3.12-alpine

WORKDIR /app

# Installation des dépendances système si nécessaire
RUN apk add --no-cache tzdata

# Copie des fichiers de dépendances et installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source de l'application
COPY app.py .

# Création du dossier de données persistantes
RUN mkdir -p /data

EXPOSE 5000

# Lancement via Gunicorn (2 workers)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
