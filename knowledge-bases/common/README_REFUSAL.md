# Configuration des Réponses de Refus

Ce dossier contient les fichiers de configuration pour le système de refus du chatbot.

## Fichiers

### 1. `refusal_responses.json`
Contient les messages de refus en français et anglais.

**Structure :**
```json
{
  "fr": {
    "general_refusal": "Message de refus général",
    "minor_refusal": "Message pour les mineurs",
    "medication_refusal": "Message pour les questions sur médicaments",
    "emergency_refusal": "Message pour les situations d'urgence"
  },
  "en": { ... }
}
```

### 2. `refusal_patterns.json`
Contient les patterns regex pour détecter les questions à risque en français et anglais.

**Structure :**
```json
{
  "fr": {
    "clinical_condition": [...],
    "medication": [...],
    "personalized_request": [...],
    "meal_plan": [...],
    "numeric_targets": [...],
    "minor": [...],
    "possible_emergency": [...]
  },
  "en": { ... }
}
```

### 3. `prompts.json`
Contient les templates de prompts système pour le LLM.

**Structure :**
```json
{
  "fr": {
    "system_role": "...",
    "important_notice": "...",
    "communication_style": { ... },
    "absolute_rules": { ... },
    "behavioral_constraints": { ... },
    "template": "{system_role}\\n\\n..."
  },
  "en": { ... }
}
```

Le template utilise des placeholders :
- `{context}` : Le contexte RAG de ChromaDB
- `{question}` : La question de l'utilisateur
- `{history}` : L'historique de la conversation

## Utilisation

Les fichiers JSON sont chargés automatiquement par :
- `refusal_engine.py` : Pour les réponses et patterns de refus
- `query_chromadb.py` : Pour les prompts système

### Ajouter une nouvelle langue

1. Ajouter la section de langue dans chaque fichier JSON
2. Traduire tous les messages et patterns
3. La langue sera automatiquement supportée

### Modifier les patterns de détection

Éditer `refusal_patterns.json` et ajouter/modifier les expressions regex dans les catégories appropriées.

### Modifier les messages de refus

Éditer `refusal_responses.json` et ajuster les messages selon vos besoins.

## Exemples

### Test du système de refus

```python
from core.refusal_engine import validate_user_query

# En français
result = validate_user_query(
    question="Combien de calories pour moi?",
    context="",
    history_text="",
    llm_call_fn=None,
    language="fr"
)

# En anglais
result = validate_user_query(
    question="How many calories should I eat?",
    context="",
    history_text="",
    llm_call_fn=None,
    language="en"
)
```
