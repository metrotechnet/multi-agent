# Dok2u Multi-Agent 🧠

A multi-agent AI assistant platform by [Dok2U](https://dok2u.com). Features a **Document Assistant** powered by RAG (Retrieval-Augmented Generation) over your documents, and a **Translation Agent** with speech-to-text via OpenAI Whisper. Built with FastAPI, ChromaDB, and OpenAI GPT-4o-mini.

## ✨ Features

- **🤖 Multi-Agent Architecture**: Switch between agents from a unified interface
  - **Assistant Nutrition**: RAG-based Q&A over indexed documents and transcripts
  - **Traducteur**: Real-time text & audio translation across 27 languages
- **🎬 Automated Content Pipeline**: Process files from Google Drive — download, transcribe (Whisper), extract, chunk, and index
- **🔍 Vector Search**: ChromaDB for semantic retrieval over chunked documents
- **🎙️ Speech-to-Text**: OpenAI Whisper integration for audio transcription and translation
- **🌍 Bilingual UI**: Full French/English interface with i18n via `config.json`
- **⚡ Streaming Responses**: Real-time answers using Server-Sent Events (SSE)
- **📱 Responsive Design**: Mobile-first UI with breakpoints at 768px and 380px
- **🔐 Secure**: Environment-based secrets, no API keys in code
- **🛡️ Refusal Engine**: Configurable pattern-based refusal for out-of-scope questions

## 📁 Project Structure

```
dok2u-agent/
├── app.py                    # FastAPI application (chat + translation endpoints)
├── core/
│   ├── query_chromadb.py     # ChromaDB vector search + LLM streaming
│   ├── translate.py          # Translation module (text + audio via Whisper/GPT)
│   ├── pipeline_gdrive.py    # Pipeline: Google Drive → transcribe → index
│   ├── refusal_engine.py     # Pattern-based refusal for off-topic questions
│   └── __init__.py           # Core module init
├── scripts/
│   ├── index_chromadb.py     # Index transcripts/documents to ChromaDB
│   ├── create_knowledge_base.ps1  # Create new knowledge base structure
│   └── __init__.py           # Scripts module init
├── config/
│   └── config.json           # Shared UI translations (FR/EN) for all agents
├── knowledge-bases/          # All knowledge bases and agent configs
│   ├── common/              # Shared refusal engine configs
│   │   ├── refusal_patterns.json  # Patterns to detect off-topic questions
│   │   ├── refusal_responses.json # Canned refusal responses
│   │   └── README_REFUSAL.md      # Refusal engine documentation
│   ├── nutria/              # Nutrition knowledge base
│   │   ├── config.json      # Nutrition agent-specific UI config
│   │   ├── prompts.json     # Agent-specific system prompts
│   │   ├── transcripts/     # Transcript .txt files
│   │   ├── documents/       # Source documents
│   │   ├── extracted_texts/ # Extracted text files
│   │   └── chroma_db/       # Vector database
│   ├── translator/          # Translator agent
│   │   ├── config.json      # Translator agent-specific UI config
│   │   └── prompts.json     # Translator system prompts (FR/EN)
│   └── README.md            # Knowledge base documentation
├── videos/                   # Downloaded videos (shared)
├── templates/
│   └── index.html            # Main UI template (agent cards, selectors)
├── static/
│   ├── script.js             # Frontend JS (agent switching, translation, SSE)
│   ├── style.css             # Styles (pill selectors, responsive, dark theme)
│   ├── config.js             # Backend URL configuration (generated)
│   ├── logo-dok2u.png        # Dok2U logo
│   └── favicon.ico           # Favicon
├── tests/
│   ├── test_questions.json   # Test questions for validation
│   └── __init__.py           # Tests module init
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container config
├── firebase.json             # Firebase Hosting configuration
├── .firebaserc               # Firebase project reference
├── build.bat                 # Cloud Build script (Docker image)
├── deploy-backend.bat        # Cloud Run deployment (calls build.bat)
├── deploy-frontend.bat       # Firebase Hosting deployment
├── setup_scheduler.ps1       # Cloud Scheduler configuration
├── start_server.ps1          # Start both backend + frontend (PowerShell)
├── start_backend.ps1         # Start backend only (PowerShell)
├── start_frontend.ps1        # Start frontend only (PowerShell)
├── serve_frontend.py         # Custom frontend server (serves index.html at root)
├── startup.sh                # Container startup script
├── .env                      # Environment variables (not in git)
└── README.md                 # This file
```

## ⚙️ Setup

### 1. Clone and Navigate

```bash
cd c:\dev\agent-factory\agents\dok2u-agent
```

### 2. Create Virtual Environment

```powershell
# From the agent-factory root
cd c:\dev\agent-factory
python -m venv .venv
.\.venv\Scripts\Activate.ps1
cd agents\dok2u-agent
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file with:

```env
OPENAI_API_KEY=your-openai-api-key
KNOWLEDGE_BASE=nutria               # Name of the knowledge base to use
GCP_PROJECT_ID=your-gcp-project-id  # For Google Drive pipeline
GCS_BUCKET_NAME=your-bucket-name
GCS_REGION=us-east4
CLOUD_RUN_MEMORY=1Gi
CLOUD_RUN_TIMEOUT=300
```

### 4. Set Up Knowledge Base

The project uses a modular knowledge base system located in `knowledge-bases/`. By default, the `nutria` knowledge base is included.

**To create a new knowledge base**:

```powershell
# Using the helper script
.\scripts\create_knowledge_base.ps1 -Name "my-kb"

# Or manually create the structure
mkdir knowledge-bases\my-kb
mkdir knowledge-bases\my-kb\transcripts
mkdir knowledge-bases\my-kb\documents
mkdir knowledge-bases\my-kb\extracted_texts
```

See [knowledge-bases/README.md](knowledge-bases/README.md) for complete documentation.

### 5. Add Documents

### 5. Add Documents

Place your files in the appropriate knowledge base folder:
- Transcript files (`.txt`) in `knowledge-bases/nutria/transcripts/`
- Document files (`.json`) in `knowledge-bases/nutria/documents/`
- Extracted text files (`.txt`) in `knowledge-bases/nutria/extracted_texts/`

## 🛠️ Usage

### Index Documents to ChromaDB

```powershell
# Activate virtual environment first
& c:\dev\agent-factory\.venv\Scripts\Activate.ps1

# Navigate to the agent directory
cd c:\dev\agent-factory\agents\dok2u-agent

# Index the default knowledge base (nutria)
python scripts/index_chromadb.py

# Index a specific knowledge base
python scripts/index_chromadb.py my-kb extracted_texts

# Index transcripts folder instead
python scripts/index_chromadb.py nutria transcripts
```

This will process files from the specified knowledge base folder, creating a vector database in `knowledge-bases/{kb-name}/chroma_db/`.

### Google Drive Pipeline

```powershell
# Download, transcribe, and index content from Google Drive
python -c "from core.pipeline_gdrive import run_pipeline; run_pipeline()"
```

Or via API:

```bash
curl -X POST http://localhost:8080/update?limit=10
```

See [GDRIVE_SETUP.md](GDRIVE_SETUP.md) for Google Drive service account configuration.

### Run the Application

#### Option 1: Start Both Servers (Recommended)

```powershell
# Use PowerShell script to start both backend and frontend
.\start_server.ps1
```

This will start:
- **Backend API** at `http://localhost:8080`
- **Frontend UI** at `http://localhost:3000`

Access the application at **http://localhost:3000**

#### Option 2: Start Servers Separately

For development, you may want to start servers independently:

```powershell
# Terminal 1: Start backend only
.\start_backend.ps1

# Terminal 2: Start frontend only
.\start_frontend.ps1
```

This is useful when you need to:
- Restart one server without affecting the other
- Debug backend or frontend independently
- Run only the backend for API testing

#### Option 3: Start Backend Only

```powershell
# Manually with venv activated
python app.py
```

Access the API at **http://localhost:8080** (no UI, API only)


## 🤖 Agents

### Assistant Nutrition (dok2u)

RAG-based assistant that answers questions using indexed documents and transcripts. Uses ChromaDB for semantic search and GPT-4o-mini for response generation with source citations.

**Endpoints:**
- `POST /ask` — Streaming chat with SSE (supports conversation history)

### Traducteur (translator)

Real-time translation agent supporting 27 languages. Accepts both text and audio input.

**Endpoints:**
- `GET /api/languages` — List supported languages
- `POST /api/translate` — Translate text (streaming SSE)
- `POST /api/translate_audio` — Transcribe & translate audio file (Whisper + GPT-4o-mini)

**Supported Languages:** French, English, Spanish, German, Italian, Portuguese, Chinese, Japanese, Korean, Arabic, Russian, Hindi, Dutch, Polish, Swedish, Turkish, Vietnamese, Thai, Indonesian, Czech, Romanian, Hungarian, Greek, Hebrew, Danish, Finnish, Norwegian.

## 📚 Knowledge Base System

The application uses a modular knowledge base system that allows you to:
- Maintain multiple separate knowledge bases
- Switch between knowledge bases by changing `.env`
- Create domain-specific agents with different document sets

### Structure

Each knowledge base is a self-contained folder in `knowledge-bases/`:

```
knowledge-bases/
├── nutria/                     # Default: Nutrition knowledge base
│   ├── transcripts/           # Audio transcriptions
│   ├── documents/             # Source documents
│   ├── extracted_texts/       # Processed texts
│   └── chroma_db/             # Vector database
└── other-domain/              # Example: Another knowledge base
    ├── transcripts/
    ├── documents/
    ├── extracted_texts/
    └── chroma_db/
```

### Creating a New Knowledge Base

**Using the helper script**:
```powershell
.\scripts\create_knowledge_base.ps1 -Name "medical-kb"
```

**Manual creation**:
```bash
mkdir knowledge-bases/medical-kb
mkdir knowledge-bases/medical-kb/{transcripts,documents,extracted_texts}
```

### Indexing a Knowledge Base

```bash
# Index specific knowledge base
python scripts/index_chromadb.py medical-kb extracted_texts
```

### Switching Knowledge Bases

Update `.env`:
```env
KNOWLEDGE_BASE=medical-kb
```

Then restart the application. The agent will automatically use the specified knowledge base.

### Management

See [knowledge-bases/README.md](knowledge-bases/README.md) for complete documentation including:
- Creating and managing knowledge bases
- Reindexing and clearing databases
- Backup and restore procedures
- Troubleshooting tips

## ⚙️ Configuration System

The application uses a **layered configuration system** that separates shared UI elements from agent-specific customizations. This allows each agent to have its own branding, suggestions, and interface elements while maintaining consistent legal disclaimers and privacy policies.

### Configuration Files

1. **Shared Config** (`config/config.json`)
   - Application branding (title, description)
   - Header and sidebar navigation
   - Cookie consent banner
   - Legal disclaimers and warnings
   - Privacy policy
   - About page
   - Language translations (27 languages)
   - Common message strings

2. **Agent-Specific Configs**
   - **Nutrition Agent**: `knowledge-bases/nutria/config.json`
     - Custom app title: "Nutria | Agent Nutritionniste"
     - Nutrition-focused suggestions (🥗 nutrition, 💊 supplements, 🏋️ training, 💡 health)
     - Domain-specific disclaimers
   - **Translator Agent**: `knowledge-bases/translator/config.json`
     - Custom app title: "Traducteur IA | Agent Multilingue"
     - Translation-specific UI (sourceLabel, targetLabel)
     - Translation suggestions (📝 text, 🎤 audio)

### How It Works

When the frontend requests configuration via `/api/get_config?agent=nutria`, the backend:
1. Loads the shared configuration
2. Loads the agent-specific configuration
3. Merges them (agent config overrides shared config)
4. Returns the merged configuration

```javascript
// Example: Frontend config loading
const config = await fetch('/api/get_config?agent=nutria').then(r => r.json());
// config now contains merged shared + agent-specific values
```

### Adding New Agents

To create a new agent with custom UI:

1. Create agent-specific config:
   ```bash
   cp knowledge-bases/nutria/config.json knowledge-bases/my-agent/config.json
   ```

2. Customize the config:
   - Update `app.title` with agent branding
   - Modify `suggestions` with relevant actions
   - Customize `input.placeholder` and disclaimers

3. Update backend to recognize the new agent in `app.py`

## 🎯 Key Features

### Multi-Agent UI

- **Agent Selector**: Pill-styled dropdown in the header to switch between agents
- **Agent Cards**: Intro page with clickable cards for each agent
- **Chat Clearing**: Conversation resets when switching agents
- **Welcome Messages**: Each agent displays a localized welcome message on selection
- **Dynamic Placeholders**: Input placeholder and disclaimer update per agent

### Internationalization (i18n)

All UI text is stored in `config/config.json` under `fr` and `en` sections. The language toggle in the header switches between French and English. Agent names, welcome messages, suggestions, and disclaimers are all translatable.

### Vector Search (ChromaDB)

- Semantic search over chunked documents
- OpenAI text-embedding-3-large (3072 dimensions)
- Fast local queries, no cloud costs
- Source citation with document references

### Refusal Engine

Configurable pattern matching to detect and refuse off-topic questions gracefully. Patterns and responses are defined in `knowledge-bases/common/refusal_patterns.json` and `knowledge-bases/common/refusal_responses.json`.

See [knowledge-bases/common/README_REFUSAL.md](knowledge-bases/common/README_REFUSAL.md) for detailed documentation on the refusal engine.

## 🔧 Technical Stack

- **Backend**: FastAPI, Python 3.11+
- **AI/ML**: OpenAI GPT-4o-mini (chat + translation), OpenAI Whisper (transcription)
- **Vector DB**: ChromaDB (local)
- **Embeddings**: OpenAI text-embedding-3-large (3072 dimensions)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **i18n**: JSON-based config with `data-i18n` attributes
- **Cloud**: Google Cloud Run, Google Drive API
- **Configuration**: Environment variables (`.env`) + `config/config.json`

## 🚀 Deployment

### Backend Deployment (Google Cloud Run)

```bash
.\deploy-backend.bat
```

This will:
1. Automatically build the Docker image using Cloud Build
2. Load configuration from `.env`
3. Deploy to Cloud Run with all environment variables
4. Configure CORS for Firebase hosting domain
5. Output the service URL

**Configuration** (via `.env`):
- Memory: 1Gi
- Timeout: 300s (5 minutes)
- Min instances: 1
- Max instances: 10
- CPU: 1

### Frontend Deployment (Firebase Hosting)

```bash
.\deploy-frontend.bat
```

This will:
1. Copy frontend files from `templates/` and `static/` to `public/`
2. Update file paths for Firebase hosting
3. Create config.js with backend URL
4. Deploy to Firebase Hosting

**CORS Configuration**: The backend is configured to allow requests from:
- `https://dok2u-agent.web.app`
- `https://dok2u-agent.firebaseapp.com`
- `http://localhost:3000` (local frontend development)
- `http://localhost:8080` (local backend-only development)

See [FIREBASE_DEPLOYMENT.md](FIREBASE_DEPLOYMENT.md) for detailed Firebase setup.

## 🔐 Security

- Environment-based secrets management
- No API keys in code or config files
- `.env` file excluded from version control
- Secure Cloud Run deployment with IAM
- Refusal engine for out-of-scope question handling

## 📝 Requirements

- **Python**: 3.11 or higher
- **Memory**: 2GB+ recommended
- **Storage**: 1GB for transcripts and database
- **APIs**: OpenAI API key required
- **GCP**: Google Cloud Project (optional, for Cloud Run deployment and Google Drive pipeline)

## 🐛 Troubleshooting

### ChromaDB Issues

```bash
# Re-index transcripts
python scripts/index_chromadb.py
```

### Server Won't Start

- Ensure `.env` file exists with `OPENAI_API_KEY`
- Verify Python 3.11+ is installed: `python --version`
- Check venv is activated: `.\.venv\Scripts\Activate.ps1`
- Install dependencies: `pip install -r requirements.txt`

### Translation Not Working

- Verify `OPENAI_API_KEY` is set (used for both Whisper and GPT-4o-mini)
- Check audio file format (supports mp3, wav, m4a, webm)

### Deployment Fails

- Check `.env` file exists and has all required variables
- Verify Cloud Build API is enabled
- Ensure billing is enabled on GCP project
- Check IAM permissions for Cloud Build service account

### CORS Errors

- Verify backend allows your frontend domain in CORS middleware
- Check backend URL in `static/config.js`
- Ensure backend is deployed and accessible

## 💰 Cost Estimation

**Cloud Run** (~$20-50/month):
- CPU: $0.00002400/vCPU-second
- Memory: $0.00000250/GiB-second
- Free tier: 2M requests/month

**OpenAI API** (~$10-30/month):
- text-embedding-3-large: $0.13/1M tokens
- gpt-4o-mini: $0.15/1M input, $0.60/1M output
- Whisper: $0.006/minute of audio
