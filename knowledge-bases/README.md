# Knowledge Bases

This directory contains all knowledge bases for the IMX Multi-Agent system. Each knowledge base is a separate folder containing documents, transcripts, and the corresponding ChromaDB vector database.

## Quick Start: Create New Agent

The fastest way to create a new agent:

```bash
# 1. Copy example configuration
cp ../agent-config.example.json my-agent-config.json

# 2. Edit configuration with your agent details
nano my-agent-config.json

# 3. Run creation script
python ../core/create_agent.py my-agent-config.json
```

**📖 See [AGENT_CREATION.md](../AGENT_CREATION.md) for complete guide.**

## Structure

```
knowledge-bases/
├── nutria/                     # Nutrition knowledge base (RAG-based agent)
│   ├── transcripts/           # Transcript .txt files
│   ├── documents/             # Source documents (JSON, PDF, etc.)
│   ├── extracted_texts/       # Extracted text files
│   ├── chroma_db/             # ChromaDB vector database
│   ├── prompts.json           # Knowledge base-specific prompts and instructions
│   └── config.json            # Agent-specific UI configuration
├── translator/                # Translator agent (standalone, no KB)
│   ├── config.json            # Translator agent-specific UI configuration
│   └── prompts.json           # Translator system prompts (FR/EN)
├── another-kb/                # Example of another knowledge base
│   ├── transcripts/
│   ├── documents/
│   ├── extracted_texts/
│   ├── chroma_db/
│   ├── prompts.json           # Different prompts for this KB
│   └── config.json            # Agent-specific UI configuration (optional)
└── README.md                  # This file
```

## Agent Types

### RAG-Based Agents (Document Knowledge Bases)
Agents like `nutria` that answer questions using indexed documents. These require:
- Document folders (`transcripts/`, `documents/`, `extracted_texts/`)
- Vector database (`chroma_db/`)
- Optional `prompts.json` for system instructions
- Optional `config.json` for agent-specific UI customization

### Standalone Agents
Agents like `translator` that don't require document indexing. These only need:
- `config.json` for agent-specific UI customization
- Optional `prompts.json` for system prompts and instructions

## Structure

## Creating a New Knowledge Base

### Method 1: Manual Creation

1. **Create the folder structure**:
   ```bash
   cd knowledge-bases
   mkdir my-new-kb
   cd my-new-kb
   mkdir transcripts documents extracted_texts
   ```

2. **Add your documents**:
   - Place transcript .txt files in `transcripts/`
   - Place source documents in `documents/`
   - Place extracted text files in `extracted_texts/`

3. **Index the documents**:
   ```bash
   # From the imx-multi-agent root directory
   python scripts/index_chromadb.py my-new-kb extracted_texts
   
   # Or index transcripts:
   python scripts/index_chromadb.py my-new-kb transcripts
   ```

4. **Configure the application**:
   Update `.env` file:
   ```env
   KNOWLEDGE_BASE=my-new-kb
   ```

5. **Restart the application** to use the new knowledge base.

## Customizing Knowledge Base Behavior

Each knowledge base can have its own `prompts.json` file that defines:
- System prompts and instructions
- Communication style
- Behavioral constraints
- Absolute rules
- How the AI should respond
- **Model Configuration**:
  - `model_supplier`: "openai" or "gemini"
  - `model_name`: "gpt-4o-mini", "gemini-2.0-flash-exp", etc.

### Creating Custom Prompts

When creating a new knowledge base, you can:

1. **Copy existing prompts**:
   ```powershell
   Copy-Item knowledge-bases\nutria\prompts.json knowledge-bases\my-new-kb\prompts.json
   ```

2. **Customize the prompts** to match your knowledge base's domain:
   - Edit tone and voice characteristics
   - Add domain-specific rules
   - Customize response style
   - **Set model configuration**:
     ```json
     {
       "model_supplier": "openai",
       "model_name": "gpt-4o-mini",
       "fr": { ... },
       "en": { ... }
     }
     ```
   - Add language-specific instructions

3. **The application automatically loads** the prompts from the active knowledge base folder

**Note**: If `prompts.json` is not found in the knowledge base folder, the application will fall back to `config/prompts.json` for backward compatibility.

## Switching Between Knowledge Bases

```powershell
# Create a new knowledge base
.\scripts\create_knowledge_base.ps1 -Name "my-new-kb"
```

## Switching Between Knowledge Bases

To switch which knowledge base the application uses:

1. **Update .env file**:
   ```env
   KNOWLEDGE_BASE=nutria  # or any other knowledge base name
   ```

2. **Restart the application**

The application will automatically load the specified knowledge base on startup.

## Knowledge Base Management

### Listing Knowledge Bases

```powershell
Get-ChildItem knowledge-bases -Directory | Select-Object Name
```

### Checking Knowledge Base Size

```powershell
# Get the count of indexed documents
python -c "from core.query_chromadb import get_collection; col = get_collection('nutria'); print(f'Documents: {col.count()}')"
```

### Reindexing a Knowledge Base

```bash
# This will add new documents and update existing ones
python scripts/index_chromadb.py my-kb-name extracted_texts
```

### Clearing a Knowledge Base

To completely reset a knowledge base:

```powershell
# Remove the ChromaDB database
Remove-Item knowledge-bases\my-kb-name\chroma_db -Recurse -Force

# Re-index
python scripts/index_chromadb.py my-kb-name extracted_texts
```

## Best Practices

1. **Naming Convention**: Use lowercase with hyphens for knowledge base names
   - ✅ Good: `nutria`, `medical-kb`, `fitness-data`
   - ❌ Bad: `Nutr IA`, `MedicalKB`, `fitness_data`

2. **Document Organization**:
   - Keep source documents in `documents/`
   - Put processed/extracted text in `extracted_texts/`
   - Use `transcripts/` for audio transcriptions

3. **Backup**: Regularly backup your knowledge bases
   ```powershell
   # Backup a knowledge base
   Compress-Archive -Path knowledge-bases\nutria -DestinationPath backups\nutria-$(Get-Date -Format 'yyyyMMdd').zip
   ```

4. **Version Control**: Add large knowledge bases to `.gitignore`
   ```gitignore
   knowledge-bases/*/chroma_db/
   knowledge-bases/*/documents/
   knowledge-bases/*/videos/
   ```

## Troubleshooting

### "ChromaDB path not found" error

Make sure you've indexed the knowledge base first:
```bash
python scripts/index_chromadb.py my-kb-name extracted_texts
```

### Empty results from queries

1. Check that documents are indexed:
   ```bash
   python -c "from core.query_chromadb import get_collection; col = get_collection('my-kb-name'); print(col.count())"
   ```

2. Verify documents exist in the folder:
   ```powershell
   Get-ChildItem knowledge-bases\my-kb-name\extracted_texts
   ```

### Switching doesn't work

1. Verify the `.env` file has been updated
2. Restart the application (the collection is cached in memory)
3. Check the startup logs to see which knowledge base was loaded

## Multiple Knowledge Bases in Production

If you need to serve multiple knowledge bases simultaneously:

1. **Option 1**: Deploy separate instances with different `KNOWLEDGE_BASE` env vars
2. **Option 2**: Modify `app.py` to accept a `kb_name` parameter in API requests
3. **Option 3**: Create a routing layer that directs requests to different knowledge bases

See the main README.md for deployment instructions.
