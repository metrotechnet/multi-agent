# Google Drive Pipeline Configuration

## Overview
Ce pipeline permet d'indexer automatiquement des documents depuis un dossier Google Drive partagé dans ChromaDB pour être utilisés par l'agent conversationnel.

## Types de documents supportés
- PDF (`.pdf`)
- Google Docs (exportés en PDF)
- Word Documents (`.docx`)
- Fichiers texte (`.txt`)

## Configuration

### 1. Créer un compte de service Google Cloud

1. Allez sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créez un nouveau projet ou sélectionnez un projet existant
3. Activez l'API Google Drive:
   - Allez dans "APIs & Services" > "Library"
   - Recherchez "Google Drive API"
   - Cliquez sur "Enable"

4. Créez un compte de service:
   - Allez dans "APIs & Services" > "Credentials"
   - Cliquez sur "Create Credentials" > "Service Account"
   - Donnez un nom au compte (ex: "gdrive-indexer")
   - Cliquez sur "Create and Continue"
   - Passez les permissions (optionnel pour Drive)
   - Cliquez sur "Done"

5. Créez une clé pour le compte de service:
   - Cliquez sur le compte de service créé
   - Allez dans l'onglet "Keys"
   - Cliquez sur "Add Key" > "Create new key"
   - Sélectionnez "JSON"
   - Le fichier de clé sera téléchargé automatiquement

### 2. Configurer l'accès au dossier Google Drive

1. Ouvrez le fichier JSON de clé téléchargé
2. Copiez l'adresse email du compte de service (champ `client_email`)
3. Allez sur Google Drive et ouvrez le dossier que vous voulez indexer
4. Cliquez sur "Partager" et ajoutez l'email du compte de service avec permission "Lecteur"
5. Copiez l'ID du dossier depuis l'URL:
   - URL format: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
   - L'ID est la partie après `/folders/`

### 3. Configurer l'application

1. Copiez le fichier de clé JSON dans le dossier `config/`:
   ```bash
   cp ~/Downloads/your-service-account-key.json ./config/gdrive_credentials.json
   ```

2. Mettez à jour le fichier `.env`:
   ```env
   # Google Drive Configuration
   GDRIVE_FOLDER_ID=votre_folder_id_ici
   GDRIVE_CREDENTIALS_PATH=./config/gdrive_credentials.json
   ```

## Utilisation

### Indexer les documents

```python
from core.pipeline_gdrive import run_pipeline

# Indexer tous les documents du dossier configuré
result = run_pipeline()

# Indexer seulement les 10 premiers documents
result = run_pipeline(limit=10)

# Indexer depuis un dossier spécifique
result = run_pipeline(folder_id="autre_folder_id")
```

### Vérifier le statut

```python
from core.pipeline_gdrive import get_gdrive_status, get_indexed_documents

# Vérifier l'authentification
status = get_gdrive_status()
print(status)

# Liste des documents indexés
docs = get_indexed_documents()
for doc in docs:
    print(f"{doc['source']}: {doc['chunks']} chunks")
```

### API Endpoint

Ajoutez dans `app.py`:

```python
from core.pipeline_gdrive import run_pipeline as run_gdrive_pipeline

@app.post("/update_gdrive")
def update_gdrive_pipeline(limit: int = None):
    result = run_gdrive_pipeline(limit=limit)
    return result
```

## Structure des données

Les documents sont indexés dans ChromaDB avec les métadonnées suivantes:
- `source`: Nom du fichier
- `file_id`: ID Google Drive du fichier
- `chunk`: Numéro du chunk
- `mime_type`: Type MIME du document
- `indexed_at`: Date et heure d'indexation

## Chunking

Les documents sont découpés en chunks de:
- **Taille**: 1000 caractères
- **Overlap**: 100 caractères (pour maintenir le contexte entre chunks)

## Dépannage

### Erreur d'authentification
- Vérifiez que le fichier de credentials existe
- Vérifiez que l'API Google Drive est activée
- Vérifiez que le compte de service a accès au dossier

### Aucun document trouvé
- Vérifiez l'ID du dossier
- Vérifiez les permissions de partage
- Vérifiez que les documents sont des types supportés

### Erreur d'extraction de texte
- Pour les PDFs: Certains PDFs scannés peuvent ne pas contenir de texte extractible
- Pour les DOCX: Vérifiez que le fichier n'est pas corrompu

## Dépendances requises

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client PyPDF2 python-docx
```
