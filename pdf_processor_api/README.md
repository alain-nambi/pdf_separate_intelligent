# API de Traitement PDF Asynchrone

API Django REST avec Celery pour:
1. **Séparer** un PDF multi-pages en fichiers individuels
2. **Renommer** automatiquement chaque page avec OCR
3. **Traiter** en arrière-plan pour une meilleure UX

## 🎯 Fonctionnalités

- 📄 Séparation automatique des PDFs multi-pages
- 🔍 Reconnaissance OCR des informations (nom, matricule, période)
- 🏷️ Renommage intelligent: `Matricule_NOM_PRENOM_MOISANNEE.pdf`
- ⚡ Traitement asynchrone avec Celery & Redis
- 📊 Suivi en temps réel de la progression
- 📁 Téléchargement des fichiers traités

## 🚀 Installation Rapide

```bash
# 1. Cloner et naviguer
git clone <repo>
cd pdf_processor_api

# 2. Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos paramètres

# 3. Lancer avec Docker Compose
docker-compose up -d

# 4. Accéder à l'API
http://localhost:8000/api/