"""
Agent Creation Script - Initialize new agent from configuration

This script automates the creation of a new agent by:
1. Reading agent configuration from JSON file
2. Creating agent folder structure from template
3. Copying and processing documents (PDF, DOCX, TXT, JSON)
4. Creating transcripts from all document files automatically
5. Transcribing audio files using Whisper
6. Indexing all content to ChromaDB
7. Registering agent in agents.json

Supported document formats:
- PDF (.pdf) - Text extraction with PyPDF2
- Word (.docx) - Text extraction with python-docx
- Text (.txt) - Direct reading
- JSON (.json) - Structured data converted to readable text format

All documents are automatically processed to create transcript files
in addition to being indexed to ChromaDB for semantic search.
"""

import os
import json
import shutil
import argparse
import re
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import PyPDF2
import docx
from tqdm import tqdm

# Load environment variables
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / '.env')

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client_openai = OpenAI(api_key=OPENAI_API_KEY)

KNOWLEDGE_BASES_DIR = PROJECT_ROOT / "knowledge-bases"
TEMPLATE_AGENT_DIR = KNOWLEDGE_BASES_DIR / "template-agent"
AGENTS_CONFIG_PATH = KNOWLEDGE_BASES_DIR / "agents.json"


def validate_config(config: dict) -> bool:
    """Validate agent configuration"""
    required_fields = ["agent", "model", "prompts", "config"]
    for field in required_fields:
        if field not in config:
            print(f"❌ Missing required field: {field}")
            return False
    
    agent = config["agent"]
    if not all(k in agent for k in ["id", "name", "description"]):
        print("❌ Agent must have: id, name, description")
        return False
    
    # Validate agent ID (alphanumeric, hyphens, underscores only)
    agent_id = agent["id"]
    if not agent_id.replace("-", "").replace("_", "").isalnum():
        print("❌ Agent ID must contain only letters, numbers, hyphens, and underscores")
        return False
    
    return True


def create_agent_structure(agent_id: str) -> Path:
    """Create agent folder structure from template"""
    agent_dir = KNOWLEDGE_BASES_DIR / agent_id
    
    if agent_dir.exists():
        response = input(f"⚠️  Agent '{agent_id}' already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Aborted")
            return None
        shutil.rmtree(agent_dir)
    
    print(f"📁 Creating agent structure: {agent_id}")
    
    # Copy template structure
    shutil.copytree(TEMPLATE_AGENT_DIR, agent_dir)
    
    # Create empty directories if they don't exist
    (agent_dir / "documents").mkdir(exist_ok=True)
    (agent_dir / "extracted_texts").mkdir(exist_ok=True)
    (agent_dir / "transcripts").mkdir(exist_ok=True)
    (agent_dir / "chroma_db").mkdir(exist_ok=True)
    
    print(f"✅ Agent structure created: {agent_dir}")
    return agent_dir


def save_prompts_json(agent_dir: Path, config: dict):
    """Create prompts.json from configuration"""
    model = config.get("model", {})
    prompts = config.get("prompts", {})
    
    prompts_data = {
        "model_supplier": model.get("supplier", "openai"),
        "model_name": model.get("name", "gpt-4o-mini"),
        **prompts
    }
    
    prompts_path = agent_dir / "prompts.json"
    with open(prompts_path, 'w', encoding='utf-8') as f:
        json.dump(prompts_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Created: prompts.json")


def save_config_json(agent_dir: Path, config: dict):
    """Create config.json from configuration"""
    config_data = config.get("config", {})
    
    config_path = agent_dir / "config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Created: config.json")


def copy_documents(agent_dir: Path, config: dict) -> list:
    """Copy document files to agent documents folder and create transcripts"""
    documents = config.get("documents", {})
    files = documents.get("files", [])
    
    if not files:
        print("⚠️  No documents to copy")
        return []
    
    documents_dir = agent_dir / "documents"
    transcripts_dir = agent_dir / "transcripts"
    copied_files = []
    transcript_files = []
    
    print(f"📄 Processing {len(files)} documents...")
    for file_path_str in tqdm(files, desc="Processing documents"):
        file_path = Path(file_path_str).expanduser()
        
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue
        
        # Copy original file
        dest_path = documents_dir / file_path.name
        shutil.copy2(file_path, dest_path)
        copied_files.append(dest_path)
        
        # Extract text and create transcript
        text = extract_text_from_file(file_path)
        if text:
            # Create transcript file
            transcript_name = f"{file_path.stem}.txt"
            transcript_path = transcripts_dir / transcript_name
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"# Extracted from: {file_path.name}\n\n")
                f.write(text)
            
            transcript_files.append(transcript_path)
    
    print(f"✅ Copied {len(copied_files)} documents")
    print(f"✅ Created {len(transcript_files)} transcripts from documents")
    return copied_files


def transcribe_audio_files(agent_dir: Path, config: dict) -> list:
    """Transcribe audio files using Whisper"""
    documents = config.get("documents", {})
    audio_files = documents.get("audio_files", [])
    
    if not audio_files:
        print("⚠️  No audio files to transcribe")
        return []
    
    transcripts_dir = agent_dir / "transcripts"
    transcribed_files = []
    
    print(f"🎙️  Transcribing {len(audio_files)} audio files...")
    for audio_info in tqdm(audio_files, desc="Transcribing audio"):
        audio_path = Path(audio_info["path"]).expanduser()
        language = audio_info.get("language")
        output_name = audio_info.get("output_name", f"{audio_path.stem}.txt")
        
        if not audio_path.exists():
            print(f"⚠️  Audio file not found: {audio_path}")
            continue
        
        try:
            # Read audio file
            with open(audio_path, 'rb') as f:
                audio_bytes = f.read()
            
            # Transcribe using Whisper
            params = {
                "model": "whisper-1",
                "file": audio_bytes,
                "response_format": "text"
            }
            if language:
                params["language"] = language
            
            # Create temporary file for Whisper API
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=audio_path.suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            try:
                with open(tmp_path, "rb") as audio_file:
                    transcript = client_openai.audio.transcriptions.create(**params)
                
                # Save transcript
                transcript_path = transcripts_dir / output_name
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    f.write(transcript)
                
                transcribed_files.append(transcript_path)
                print(f"✅ Transcribed: {audio_path.name} → {output_name}")
            finally:
                os.unlink(tmp_path)
                
        except Exception as e:
            print(f"❌ Error transcribing {audio_path.name}: {e}")
    
    print(f"✅ Transcribed {len(transcribed_files)} audio files")
    return transcribed_files


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF"""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX"""
    try:
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text.strip()
    except Exception as e:
        print(f"Error extracting DOCX: {e}")
        return ""


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from TXT"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading TXT: {e}")
        return ""


def extract_text_from_json(file_path: str) -> str:
    """Extract text from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert JSON to readable text format
        def json_to_text(obj, indent=0):
            """Recursively convert JSON object to readable text"""
            text_parts = []
            prefix = "  " * indent
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, (dict, list)):
                        text_parts.append(f"{prefix}{key}:")
                        text_parts.append(json_to_text(value, indent + 1))
                    else:
                        text_parts.append(f"{prefix}{key}: {value}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        text_parts.append(f"{prefix}[{i}]:")
                        text_parts.append(json_to_text(item, indent + 1))
                    else:
                        text_parts.append(f"{prefix}- {item}")
            else:
                text_parts.append(f"{prefix}{obj}")
            
            return "\n".join(text_parts)
        
        return json_to_text(data).strip()
    except Exception as e:
        print(f"Error extracting JSON: {e}")
        return ""


def extract_text_from_file(file_path: Path) -> str:
    """Extract text based on file extension"""
    suffix = file_path.suffix.lower()
    
    if suffix == '.pdf':
        return extract_text_from_pdf(str(file_path))
    elif suffix == '.docx':
        return extract_text_from_docx(str(file_path))
    elif suffix == '.txt':
        return extract_text_from_txt(str(file_path))
    elif suffix == '.json':
        return extract_text_from_json(str(file_path))
    else:
        print(f"⚠️  Unsupported file type: {suffix}")
        return ""


def create_transcripts_chromadb_json(agent_dir: Path, agent_id: str):
    """Create transcripts_chromadb.json file from transcripts and JSON documents"""
    print(f"📝 Creating transcripts_chromadb.json...")
    
    transcripts_dir = agent_dir / "transcripts"
    documents_dir = agent_dir / "documents"
    output_path = agent_dir / "transcripts_chromadb.json"
    
    documents = []
    doc_counter = 0
    
    # Process transcript files (.txt)
    if transcripts_dir.exists():
        transcript_files = list(transcripts_dir.glob("*.txt"))
        print(f"📄 Processing {len(transcript_files)} transcript files...")
        
        for file_path in tqdm(transcript_files, desc="Processing transcripts"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                if not text.strip():
                    continue
                
                # Create document ID and metadata
                doc_id = f"doc_{doc_counter:04d}_{file_path.stem}"
                doc_counter += 1
                
                # Basic metadata
                metadata = {
                    "source": file_path.name,
                    "reference": file_path.stem,
                    "type": "transcript"
                }
                
                # Try to extract date from filename if present
                date_match = re.search(r'(\d{2})(\d{2})(\d{2})', file_path.stem)
                if date_match:
                    day, month, year = date_match.groups()
                    metadata["date"] = f"20{year}-{month}-{day}"
                
                # Add to documents array
                documents.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": metadata
                })
                
            except Exception as e:
                print(f"⚠️  Error processing {file_path.name}: {e}")
                continue
    
    # Process JSON files (each entry becomes a separate document)
    if documents_dir.exists():
        json_files = list(documents_dir.glob("*.json"))
        print(f"📚 Processing {len(json_files)} JSON files...")
        
        for json_file in tqdm(json_files, desc="Processing JSON files"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # Handle both array and single object
                if isinstance(json_data, list):
                    entries = json_data
                elif isinstance(json_data, dict):
                    entries = [json_data]
                else:
                    print(f"⚠️  Unsupported JSON structure in {json_file.name}")
                    continue
                
                # Create a document for each entry
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    
                    # Generate readable text from the entry
                    text_parts = []
                    
                    # Use entry's own ID if available, otherwise generate one
                    entry_id = entry.get("id", f"entry_{doc_counter}")
                    
                    # Build readable text from key fields
                    if "titre" in entry or "title" in entry:
                        title = entry.get("titre") or entry.get("title")
                        text_parts.append(f"Titre: {title}")
                    
                    if "label" in entry:
                        text_parts.append(f"Label: {entry['label']}")
                    
                    if "auteur" in entry or "author" in entry:
                        author = entry.get("auteur") or entry.get("author")
                        text_parts.append(f"Auteur: {author}")
                    
                    if "resume" in entry or "summary" in entry:
                        resume = entry.get("resume") or entry.get("summary")
                        if resume:
                            text_parts.append(f"\nRésumé: {resume}")
                    
                    if "description" in entry:
                        text_parts.append(f"\nDescription: {entry['description']}")
                    
                    if "categorie" in entry or "category" in entry:
                        cat = entry.get("categorie") or entry.get("category")
                        text_parts.append(f"\nCatégorie: {cat}")
                    
                    # Add any other important fields
                    for key in ["editeur", "publisher", "parution", "pages", "langue", "language"]:
                        if key in entry and entry[key]:
                            text_parts.append(f"{key.capitalize()}: {entry[key]}")
                    
                    # Combine all parts
                    text = "\n".join(text_parts)
                    
                    if not text.strip():
                        # Fallback: convert entire entry to text
                        text = "\n".join([f"{k}: {v}" for k, v in entry.items() if v and k != "classification"])
                    
                    # Create document ID
                    doc_id = f"doc_{doc_counter:04d}_{entry_id}"
                    doc_counter += 1
                    
                    # Build metadata from entry fields
                    metadata = {
                        "source": json_file.name,
                        "type": entry.get("type", "json_entry"),
                        "entry_id": entry_id
                    }
                    
                    # Add relevant fields to metadata
                    for key in ["categorie", "category", "editeur", "publisher", "langue", "language"]:
                        if key in entry and entry[key]:
                            metadata[key] = entry[key]
                    
                    # Add to documents array
                    documents.append({
                        "id": doc_id,
                        "text": text,
                        "metadata": metadata
                    })
                
            except Exception as e:
                print(f"⚠️  Error processing {json_file.name}: {e}")
                continue
    
    if not documents:
        print("⚠️  No documents to process")
        return
    
    # Create the complete structure
    transcripts_data = {
        "knowledge_base": agent_id,
        "format": "chromadb",
        "total_documents": len(documents),
        "extracted_at": datetime.now().isoformat(),
        "documents": documents
    }
    
    # Save to file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcripts_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Created transcripts_chromadb.json with {len(documents)} documents")
    except Exception as e:
        print(f"❌ Error saving transcripts_chromadb.json: {e}")


def index_to_chromadb(agent_dir: Path, agent_id: str):
    """Index documents from transcripts_chromadb.json to ChromaDB"""
    print(f"🔍 Indexing documents to ChromaDB...")
    
    # Load transcripts_chromadb.json
    transcripts_json_path = agent_dir / "transcripts_chromadb.json"
    
    if not transcripts_json_path.exists():
        print("❌ transcripts_chromadb.json not found. Run create_transcripts_chromadb_json first.")
        return
    
    try:
        with open(transcripts_json_path, 'r', encoding='utf-8') as f:
            transcripts_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading transcripts_chromadb.json: {e}")
        return
    
    documents = transcripts_data.get("documents", [])
    
    if not documents:
        print("⚠️  No documents found in transcripts_chromadb.json")
        return
    
    # Setup ChromaDB
    chroma_db_dir = agent_dir / "chroma_db"
    extracted_dir = agent_dir / "extracted_texts"
    
    extracted_dir.mkdir(exist_ok=True)
    
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=OPENAI_API_KEY,
        model_name="text-embedding-3-large"
    )
    
    chroma_client = chromadb.PersistentClient(
        path=str(chroma_db_dir),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=False
        )
    )
    
    collection = chroma_client.get_or_create_collection(
        name="gdrive_documents",
        embedding_function=ef
    )
    
    indexed_count = 0
    
    print(f"📚 Processing {len(documents)} documents from transcripts_chromadb.json...")
    
    for doc in tqdm(documents, desc="Indexing documents"):
        
        try:
            text = doc.get("text", "")
            doc_id = doc.get("id", "")
            metadata = doc.get("metadata", {})
            
            if not text or not text.strip():
                print(f"⚠️  No text in document: {doc_id}")
                continue
            
            # Chunk the text
            chunk_size = 1000
            overlap = 100
            chunks = []
            
            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i:i + chunk_size]
                if chunk.strip():
                    chunks.append(chunk)
            
            if not chunks:
                print(f"⚠️  No chunks created from: {doc_id}")
                continue
            
            # Add to ChromaDB
            for idx, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{idx}"
                
                # Combine document metadata with chunk metadata
                chunk_metadata = {
                    **metadata,
                    "document_id": doc_id,
                    "chunk_index": idx,
                    "source": metadata.get("source", "transcript")
                }
                
                collection.add(
                    documents=[chunk],
                    ids=[chunk_id],
                    metadatas=[chunk_metadata]
                )
            
            indexed_count += 1
            
        except Exception as e:
            print(f"❌ Error indexing document {doc.get('id', 'unknown')}: {e}")
            continue
    
    print(f"✅ Indexed {indexed_count} documents to ChromaDB")


def update_agents_json(config: dict):
    """Update or create agents.json with new agent"""
    agent = config["agent"]
    agent_id = agent["id"]
    
    # Load existing agents.json or create new
    if AGENTS_CONFIG_PATH.exists():
        with open(AGENTS_CONFIG_PATH, 'r', encoding='utf-8') as f:
            agents_data = json.load(f)
    else:
        agents_data = {
            "agents": {},
            "default": "nutria"
        }
    
    # Get name and description (support both old and new format)
    name = agent.get("name")
    if isinstance(name, dict):
        # New format: {"fr": "...", "en": "..."}
        name = name.get("en", name.get("fr", agent_id))
    elif not name:
        name = agent_id
    
    description = agent.get("description")
    if isinstance(description, dict):
        # New format: {"fr": "...", "en": "..."}
        description = description.get("en", description.get("fr", ""))
    elif not description:
        description = ""
    
    # Add or update agent
    agents_data["agents"][agent_id] = {
        "id": agent_id,
        "name": name,
        "description": description,
        "logo": agent.get("logo", f"/static/logos/logo-{agent_id}.png"),
        "accessKey": agent.get("accessKey", "")
    }
    
    # Save agents.json
    with open(AGENTS_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(agents_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Updated agents.json")


def update_common_config_suggestions(config: dict):
    """Update or add agent in common/config.json suggestions"""
    agent = config["agent"]
    agent_id = agent["id"]
    
    common_config_path = KNOWLEDGE_BASES_DIR / "common" / "config.json"
    
    if not common_config_path.exists():
        print("⚠️  common/config.json not found, skipping suggestion update")
        return
    
    # Load common config
    with open(common_config_path, 'r', encoding='utf-8') as f:
        common_config = json.load(f)
    
    # Get agent info from config - support both old and new format
    agent_name = agent.get("name", agent_id)
    agent_description = agent.get("description", "")
    agent_icon = agent.get("icon", "🤖")
    agent_color = agent.get("color", "#e0e0e0")
    
    # Handle name - support both string and object format
    if isinstance(agent_name, dict):
        # New format: {"fr": "...", "en": "..."}
        name_fr = agent_name.get("fr", agent_id)
        name_en = agent_name.get("en", agent_id)
    else:
        # Old format: string
        name_fr = agent_name
        name_en = agent_name
    
    # Handle description - support multiple formats
    if isinstance(agent_description, dict):
        # New format: {"fr": "...", "en": "..."}
        desc_fr = agent_description.get("fr", "")
        desc_en = agent_description.get("en", "")
    else:
        # Old format: try separate fields first, then use base description
        desc_fr = agent.get("description_fr", agent_description)
        desc_en = agent.get("description_en", agent_description)
    
    # Create suggestion entry
    def create_suggestion(lang="fr"):
        """Create suggestion object for a specific language"""
        if lang == "fr":
            title = name_fr
            description = desc_fr
        else:  # en
            title = name_en
            description = desc_en
        
        return {
            "id": agent_id,
            "icon": agent_icon,
            "title": title,
            "description": description,
            "color": agent_color,
            "event": f"switch:{agent_id}"
        }
    
    # Update both language sections
    updated = False
    for lang in ["fr", "en"]:
        if lang not in common_config:
            continue
        
        if "suggestions" not in common_config[lang]:
            common_config[lang]["suggestions"] = []
        
        suggestions = common_config[lang]["suggestions"]
        
        # Check if agent already exists
        existing_index = None
        for i, suggestion in enumerate(suggestions):
            if suggestion.get("id") == agent_id:
                existing_index = i
                break
        
        # Replace or append
        new_suggestion = create_suggestion(lang)
        if existing_index is not None:
            suggestions[existing_index] = new_suggestion
            print(f"✅ Updated {agent_id} in common/config.json suggestions ({lang})")
        else:
            suggestions.append(new_suggestion)
            print(f"✅ Added {agent_id} to common/config.json suggestions ({lang})")
        
        updated = True
    
    # Save updated config
    if updated:
        with open(common_config_path, 'w', encoding='utf-8') as f:
            json.dump(common_config, f, ensure_ascii=False, indent=2)


def create_agent_from_config(config_path: str):
    """Main function to create agent from configuration"""
    print("=" * 60)
    print("🤖 IMX Multi-Agent - Agent Creation Script")
    print("=" * 60)
    
    # Load configuration
    config_file = Path(config_path).expanduser()
    if not config_file.exists():
        print(f"❌ Configuration file not found: {config_path}")
        return False
    
    print(f"📖 Loading configuration: {config_file}")
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Validate configuration
    if not validate_config(config):
        return False
    
    agent_id = config["agent"]["id"]
    print(f"✅ Configuration validated for agent: {agent_id}")
    
    # Create agent structure
    agent_dir = create_agent_structure(agent_id)
    if not agent_dir:
        return False
    
    # Save configuration files
    save_prompts_json(agent_dir, config)
    save_config_json(agent_dir, config)
    
    # Copy documents
    copy_documents(agent_dir, config)
    
    # Transcribe audio files
    transcribe_audio_files(agent_dir, config)
    
    # Create transcripts_chromadb.json
    create_transcripts_chromadb_json(agent_dir, agent_id)
    
    # Index to ChromaDB
    index_to_chromadb(agent_dir, agent_id)
    
    # Update agents.json
    update_agents_json(config)
    
    # Update common/config.json suggestions
    update_common_config_suggestions(config)
    
    print("\n" + "=" * 60)
    print(f"✅ Agent '{agent_id}' created successfully!")
    print("=" * 60)
    print(f"\n📁 Agent directory: {agent_dir}")
    print(f"🔑 Access key: {config['agent'].get('accessKey', 'Not set')}")
    print(f"\n💡 Next steps:")
    print(f"   1. Add logo image: static/logos/logo-{agent_id}.png")
    print(f"   2. Test the agent in the web interface")
    print(f"   3. Update documents: /update?agent={agent_id}")
    
    return True


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="Create a new agent from configuration file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python core/create_agent.py agent-config.json

Configuration file should follow the format in agent-config.example.json
        """
    )
    parser.add_argument(
        "config",
        help="Path to agent configuration JSON file"
    )
    
    args = parser.parse_args()
    
    try:
        success = create_agent_from_config(args.config)
        if not success:
            exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
