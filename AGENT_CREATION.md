# Agent Creation Guide

This guide explains how to create a new AI agent using the automated creation script.

## Overview

The agent creation script (`core/create_agent.py`) automates the entire process of setting up a new agent:

1. ✅ Creates agent folder structure from template
2. ✅ Copies and processes documents (PDF, DOCX, TXT, JSON)
3. ✅ Creates transcripts from all document files automatically
4. ✅ Transcribes audio files using Whisper
5. ✅ Indexes all content to ChromaDB
6. ✅ Registers agent in agents.json

## Quick Start

### 1. Create Configuration File

Copy the example configuration:

```bash
cp agent-config.example.json my-agent-config.json
```

### 2. Edit Configuration

Open `my-agent-config.json` and customize:

```json
{
  "agent": {
    "id": "my-agent",
    "name": "My Custom Agent",
    "description": "A specialized AI agent for my domain",
    "logo": "/static/logos/logo-my-agent.png",
    "accessKey": "secure-key-123"
  },
  "model": {
    "supplier": "openai",
    "name": "gpt-4o-mini"
  },
  "documents": {
    "files": [
      "path/to/document1.pdf",
      "path/to/document2.docx"
    ],
    "audio_files": [
      {
        "path": "path/to/recording.mp3",
        "language": "fr",
        "output_name": "Recording Transcript.txt"
      }
    ]
  },
  "prompts": { ... },
  "config": { ... }
}
```

### 3. Run Creation Script

```bash
python core/create_agent.py my-agent-config.json
```

### 4. Add Logo (Optional)

Place your agent logo in:
```
static/logos/logo-my-agent.png
```

### 5. Test Your Agent

1. Restart the backend server
2. Open the web interface
3. Select your agent from the agents menu
4. Start chatting!

## Configuration Reference

### Agent Metadata

```json
"agent": {
  "id": "my-agent",           // Unique identifier (alphanumeric, hyphens, underscores)
  "name": "My Agent",         // Display name
  "description": "...",       // Short description
  "logo": "/static/...",      // Logo path (optional)
  "accessKey": "..."          // Access key for security (optional)
}
```

### Model Configuration

```json
"model": {
  "supplier": "openai",       // "openai" or "gemini"
  "name": "gpt-4o-mini"       // Model name
}
```

### Documents

#### Regular Documents

```json
"documents": {
  "files": [
    "path/to/file1.pdf",      // Absolute or relative path
    "path/to/file2.docx",
    "path/to/file3.txt"
  ]
}
```

Supported formats:
- **PDF** (`.pdf`) - Text is extracted and transcript is created
- **Word** (`.docx`) - Text is extracted and transcript is created
- **Text** (`.txt`) - Content is copied to transcripts
- **JSON** (`.json`) - Data is converted to readable text format and transcript is created

**Note:** All document files are automatically processed and transcripts are created in the `transcripts/` folder.

#### Audio Files

```json
"audio_files": [
  {
    "path": "path/to/audio.mp3",
    "language": "fr",                    // Optional: ISO-639-1 code (en, fr, es, etc.)
    "output_name": "My Transcript.txt"   // Output filename
  }
]
```

Supported formats:
- MP3 (`.mp3`)
- M4A (`.m4a`)
- WAV (`.wav`)
- MP4 (`.mp4`)
- WEBM (`.webm`)

**Note:** Audio transcription uses OpenAI Whisper API ($0.006/minute).

### Prompts Configuration

Define system prompts and rules for each language:

```json
"prompts": {
  "fr": {
    "system_role": "Tu es un assistant spécialisé...",
    "important_notice": "...",
    "communication_style": {
      "title": "TON STYLE DE COMMUNICATION",
      "tone_and_voice": {
        "characteristics": [
          "Ton conversationnel",
          "Approche pédagogique"
        ]
      }
    },
    "absolute_rules": {
      "title": "RÈGLES ABSOLUES",
      "rules": [
        "Règle 1",
        "Règle 2"
      ]
    }
  },
  "en": { ... }
}
```

### UI Configuration

Configure the web interface:

```json
"config": {
  "fr": {
    "app": {
      "title": "Mon Agent",
      "description": "Description"
    },
    "intro": {
      "title": "Bienvenue",
      "description": "...",
      "disclaimer": "...",
      "profileImage": "/static/logos/logo-my-agent.png"
    },
    "suggestions": [
      {
        "id": "topic1",
        "title": "📚 Sujet 1",
        "description": "...",
        "color": "#fff9c4"
      }
    ],
    "components": {
      "inputArea": {
        "placeholder": "Pose une question...",
        "sendButton": "Envoyer"
      }
    }
  },
  "en": { ... }
}
```

## What Gets Created

When you run the script, it creates:

```
knowledge-bases/
└── my-agent/
    ├── config.json              # UI configuration
    ├── prompts.json             # Model and prompt configuration
    ├── documents/               # Original documents
    │   ├── document1.pdf
    │   ├── document2.docx
    │   └── data.json
    ├── extracted_texts/         # Extracted text from documents (for indexing)
    │   ├── document1.txt
    │   ├── document2.txt
    │   └── data.txt
    ├── transcripts/             # Transcripts from documents AND audio
    │   ├── document1.txt        # Auto-generated from PDF
    │   ├── document2.txt        # Auto-generated from DOCX
    │   ├── data.txt             # Auto-generated from JSON
    │   └── Recording Transcript.txt  # From Whisper audio transcription
    └── chroma_db/               # Vector database
        └── ...
```

And updates:
```
knowledge-bases/
└── agents.json                  # Agent registry
```

## Advanced Usage

### Custom Processing

You can also use the functions programmatically:

```python
from core.create_agent import create_agent_from_config

success = create_agent_from_config("my-config.json")
```

### Updating Agent Data

To add more documents to an existing agent:

1. Add files to `knowledge-bases/my-agent/documents/`
2. Run the update endpoint:
   ```bash
   curl -X POST http://localhost:8080/update?agent=my-agent
   ```

### Re-creating an Agent

The script will ask for confirmation if the agent already exists:

```bash
python core/create_agent.py my-agent-config.json
# ⚠️ Agent 'my-agent' already exists. Overwrite? (y/N):
```

## Troubleshooting

### File Not Found

If documents aren't found:
- Use absolute paths: `/home/user/docs/file.pdf`
- Or paths relative to where you run the script
- Use `~/` for home directory: `~/Documents/file.pdf`

### Audio Transcription Fails

Common issues:
- **Unsupported format**: Convert to MP3, WAV, or M4A
- **File too large**: Whisper has a 25MB limit
- **No API key**: Set `OPENAI_API_KEY` in `.env`

### Agent Not Showing in UI

After creating an agent:
1. Check `knowledge-bases/agents.json` was updated
2. Restart the backend server
3. Clear browser cache

### ChromaDB Errors

If indexing fails:
- Check `OPENAI_API_KEY` is set (needed for embeddings)
- Ensure no other process is using ChromaDB
- Delete `chroma_db/` folder and re-run

## Example Workflow

Complete example for creating a fitness coach agent:

```bash
# 1. Create configuration
cat > fitness-coach-config.json << 'EOF'
{
  "agent": {
    "id": "fitness-coach",
    "name": "Fitness Coach",
    "description": "Personal fitness and nutrition guidance",
    "logo": "/static/logos/logo-fitness.png",
    "accessKey": "fitness-key-2024"
  },
  "model": {
    "supplier": "openai",
    "name": "gpt-4o-mini"
  },
  "documents": {
    "files": [
      "~/Documents/fitness-guide.pdf",
      "~/Documents/nutrition-basics.docx"
    ],
    "audio_files": [
      {
        "path": "~/Media/workout-lecture.mp3",
        "language": "en",
        "output_name": "Workout Fundamentals.txt"
      }
    ]
  },
  "prompts": { ... },
  "config": { ... }
}
EOF

# 2. Create agent
python core/create_agent.py fitness-coach-config.json

# 3. Add logo
cp ~/Images/fitness-logo.png static/logos/logo-fitness.png

# 4. Restart server
# (Press Ctrl+C in terminal running the server, then restart)

# 5. Test in browser
# Open http://localhost:3000
```

## See Also

- [Main README](../README.md) - Project overview
- [KNOWLEDGE_BASE_MIGRATION.md](../KNOWLEDGE_BASE_MIGRATION.md) - Knowledge base system
- [GDRIVE_SETUP.md](../GDRIVE_SETUP.md) - Google Drive integration
- [agent-config.example.json](../agent-config.example.json) - Full configuration template
