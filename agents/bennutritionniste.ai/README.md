# Ben Boulanger AI Agent 🧠

An intelligent personal AI assistant that processes transcripts and documents, providing expert nutritional and wellness guidance through advanced RAG (Retrieval Augmented Generation) technology. Supports both ChromaDB (local) and Vertex AI Vector Search (cloud) backends.

## 🚀 Features

- 📄 **Document Processing**: Extract and index content from Word documents and transcripts
- 🔍 **Dual Vector Database Support**: ChromaDB (local) and Vertex AI Vector Search (cloud)
- 🤖 **AI-Powered Responses**: GPT-4o-mini and Gemini integration with Ben Boulanger's expertise
- 🌐 **Multilingual Support**: French and English interface and responses
- ⚡ **Real-time Streaming**: FastAPI with Server-Sent Events for responsive chat
- 🎨 **Modern UI**: Clean, responsive web interface
- 🎬 **Instagram Integration**: Automatic video transcription and indexing
- ☁️ **Cloud Ready**: Deploy to Google Cloud Run with one command
- 🔒 **Secure Configuration**: Environment-based secrets management

## 📁 Project Structure

```
bennutritionniste.ai/
├── app.py                          # FastAPI application
├── core/
│   ├── query_chromadb.py          # ChromaDB query functions
│   ├── query_vertexaidb.py        # Vertex AI query functions
│   └── pipeline.py                 # Instagram scraping pipeline
├── scripts/
│   ├── index_chromadb.py          # Index to ChromaDB
│   ├── index_vertex_ai.py         # Index to Vertex AI
│   ├── deploy_vertex_index.py     # Deploy existing Vertex AI index
│   └── test_vertex_query.py       # Test Vertex AI queries
├── static/                         # Frontend assets
├── templates/                      # HTML templates
├── config/                         # Configuration files
│   ├── style_guides.json          # Ben's communication style
│   ├── system_prompts.json        # AI system prompts
│   ├── translations.json          # UI translations
├── transcripts/                    # Transcript files (.txt)
├── chroma_db/                      # ChromaDB storage
├── videos/                         # Downloaded Instagram videos
├── .env                            # Environment variables (create this)
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker configuration
├── build.bat                       # Build script
├── deploy.bat                      # Deploy script
└── start_server.ps1               # Local server startup
```

## ⚙️ Setup

### 1. Environment Setup

This project uses a shared virtual environment at the parent level.

```bash
# Activate the shared virtual environment
& C:\Users\denis\OneDrive\Documents\Projets\agent-factory\.venv\Scripts\Activate.ps1  # Windows PowerShell

# Or navigate to project root and activate
cd C:\Users\denis\OneDrive\Documents\Projets\agent-factory
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

Dependencies should be installed at the parent level virtual environment:

```bash
# Make sure you're in the project root with venv activated
cd C:\Users\denis\OneDrive\Documents\Projets\agent-factory
pip install -r agents\bennutritionniste.ai\requirements.txt
```

### 3. Configuration
Create a `.env` file in the project root:

```env
# API Keys
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key

# Instagram Configuration
INSTAGRAM_USER=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
INSTAGRAM_TARGET_ACCOUNT=bennutritionniste

# GCP Configuration
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-east4
GCP_SERVICE_NAME=bennutritioniste-ai
GCP_IMAGE_NAME=gcr.io/your-project/bennutritioniste-ai

# Deployment Configuration
MEMORY=1Gi
TIMEOUT=300

# Vertex AI Configuration (optional - only if using Vertex AI)
VERTEX_INDEX_ID=projects/PROJECT_NUMBER/locations/REGION/indexes/INDEX_ID
VERTEX_ENDPOINT_ID=projects/PROJECT_NUMBER/locations/REGION/indexEndpoints/ENDPOINT_ID
VERTEX_DEPLOYED_INDEX_ID=your_deployed_index_id
```

### 4. Add Transcripts
Place your transcript files (.txt) in the `transcripts/` directory

## 🛠️ Usage

### Option 1: Index to ChromaDB (Local Development)

```bash
# Activate virtual environment first
& C:\Users\denis\OneDrive\Documents\Projets\agent-factory\.venv\Scripts\Activate.ps1

# Navigate to the agent directory
cd C:\Users\denis\OneDrive\Documents\Projets\agent-factory\agents\bennutritionniste.ai

# Index transcripts to local ChromaDB
python scripts/index_chromadb.py
```

This will process transcripts from the `transcripts/` directory and create a local vector database in `chroma_db/`.

### Option 2: Index to Vertex AI (Production)

```bash
# Create and deploy Vertex AI index
python scripts/index_vertex_ai.py
```

**Note**: Deployment takes 15-30 minutes. Check status with:
```bash
gcloud ai index-endpoints describe ENDPOINT_ID --region=us-east4
```

After deployment completes, update your `.env` with the index and endpoint IDs.

### Option 3: Instagram Video Pipeline

```bash
# Scrape, transcribe, and index Instagram videos
python -c "from core.pipeline import run_pipeline; run_pipeline(limit=10)"
```

Or via API:
```bash
curl -X POST http://localhost:8080/update?limit=10
```

### Run the Application

```bash
# Navigate to agent directory
cd ...\Projets\agent-factory\agents\Bibliosense

# Use PowerShell script (automatically activates venv)
.\start_server.ps1

# Or manually with venv activated
python app.py
```

Access the application at **http://localhost:8080**

### Test Vertex AI Queries

```bash
python scripts/test_vertex_query.py
```

## 🎯 Key Features

### Vector Database Options

**ChromaDB (Local)**
- Fast local queries
- No cloud costs
- Easy setup
- Best for: Development, testing, small datasets

**Vertex AI Vector Search (Cloud)**
- Scalable to millions of vectors
- Production-ready
- Distributed queries
- Best for: Production, large datasets

### LLM Support

- **OpenAI GPT-4o-mini**: Primary model
- **Google Gemini 1.5 Flash**: Alternative option

### Additional Features

- **🧠 Expert AI Persona**: Configured with Ben Boulanger's nutritional expertise
- **🌍 Multilingual**: Seamless French/English support
- **📊 Smart Indexing**: Chunked and embedded transcripts
- **⚡ Fast Responses**: Streaming responses with SSE
- **🔐 Production Ready**: Secure environment-based configuration
- **📱 Responsive Design**: Works on desktop and mobile devices

## 🔧 Technical Stack

- **Backend**: FastAPI, Python 3.9+
- **AI/ML**: OpenAI GPT-4o-mini, Google Gemini 1.5 Flash
- **Vector DB**: ChromaDB (local) or Vertex AI Vector Search (cloud)
- **Embeddings**: OpenAI text-embedding-3-large (3072 dimensions)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Video Processing**: moviepy, OpenAI Whisper
- **Instagram**: instagrapi for video scraping
- **Cloud**: Google Cloud Run, GCS, Vertex AI
- **Configuration**: Environment variables (.env)

## 🚀 Deployment to Google Cloud Run

### Step 1: Build Docker Image

```bash
.\build.bat
```

This will use Cloud Build to create and push the Docker image.

### Step 2: Deploy to Cloud Run

```bash
.\deploy.bat
```

This will:
- Load configuration from `.env`
- Deploy with all environment variables
- Configure memory, timeout, and scaling
- Output the service URL

**Configuration**:
- Memory: 1Gi (configurable in `.env`)
- Timeout: 300s (5 minutes)
- Min instances: 1
- Max instances: 10
- CPU: 1

## 📊 Switching Between Vector Databases

### Use ChromaDB (Default for Local)

In `app.py`, import from `query_chromadb`:

```python
from core.query_chromadb import ask_question_stream, ask_question_stream_gemini
```

### Use Vertex AI

In `app.py`, import from `query_vertexaidb`:

```python
from core.query_vertexaidb import ask_question_stream_vertex, ask_question_stream_vertex_gemini
```

Then update the endpoint to use `ask_question_stream_vertex` or `ask_question_stream_vertex_gemini`.

## 🔐 Security

- Environment-based secrets management
- No API keys in code or config files
- `.env` file excluded from version control
- Secure Cloud Run deployment with IAM
- Protected configuration in separate directory

## 📝 Requirements

- **Python**: 3.9 or higher
- **Memory**: 2GB+ recommended
- **Storage**: 1GB for transcripts and database
- **APIs**: OpenAI API key required, Gemini API key optional
- **GCP**: Google Cloud Project with billing enabled (for Vertex AI and Cloud Run)

## 🐛 Troubleshooting

### ChromaDB Issues
```bash
# Re-index transcripts
python scripts/index_chromadb.py
```

### Vertex AI Permission Errors
```bash
# Refresh credentials
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/aiplatform.admin"
```

### Deployment Fails
- Check `.env` file exists and has all required variables
- Verify Cloud Build API is enabled
- Ensure billing is enabled on GCP project
- Check IAM permissions for Cloud Build service account

## 💰 Cost Estimation

**Vertex AI** (~$150-200/month):
- Index storage: ~$0.30/GB
- Queries: ~$0.05 per 1000 queries
- Endpoint: ~$0.20/hour (n1-standard-16)

**Cloud Run** (~$20-50/month):
- CPU: $0.00002400/vCPU-second
- Memory: $0.00000250/GiB-second
- Free tier: 2M requests/month

**OpenAI API** (~$10-30/month):
- text-embedding-3-large: $0.13/1M tokens
- gpt-4o-mini: $0.15/1M input, $0.60/1M output
