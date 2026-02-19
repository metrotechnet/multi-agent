"""
Index ChromaDB from JSON
=========================
This script indexes the ChromaDB-compatible JSON format into ChromaDB.
It reads the transcripts_chromadb.json file and creates vector embeddings
for efficient semantic search.

Usage:
    python scripts/index_chromadb_json.py [knowledge_base_name]

Example:
    python scripts/index_chromadb_json.py nutria
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from openai import OpenAI


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
# Load environment variables
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embeddings(texts):
    """Get embeddings from OpenAI"""
    if isinstance(texts, str):
        texts = [texts]
    
    # Process in batches to avoid rate limits
    batch_size = 100
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = client.embeddings.create(model="text-embedding-3-large", input=batch)
        all_embeddings.extend([e.embedding for e in resp.data])
    
    return all_embeddings


def init_chromadb(kb_name="nutria"):
    """Initialize ChromaDB client for a specific knowledge base"""
    kb_path = PROJECT_ROOT / "knowledge-bases" / kb_name
    chroma_path = str(kb_path / "chroma_db")
    
    # Create directories if they don't exist
    os.makedirs(chroma_path, exist_ok=True)
    
    chroma_client = chromadb.PersistentClient(
        path=chroma_path,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=False
        )
    )
    
    collection_name = "transcripts"
    
    # Reset collection if it exists
    try:
        chroma_client.delete_collection(name=collection_name)
        print(f"♻️  Deleted existing collection: {collection_name}")
    except:
        pass
    
    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"description": f"Knowledge base: {kb_name}", "kb_name": kb_name}
    )
    
    return chroma_client, collection


def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


def index_chromadb_json(kb_name="nutria"):
    """
    Index ChromaDB-compatible JSON into ChromaDB
    
    Args:
        kb_name: Name of the knowledge base (default: "nutria")
    """
    kb_path = PROJECT_ROOT / "knowledge-bases" / kb_name
    json_file = kb_path / "transcripts_chromadb.json"
    
    if not json_file.exists():
        print(f"❌ File not found: {json_file}")
        print(f"   Run 'python scripts/extract_transcripts_to_json.py {kb_name}' first")
        return
    
    # Load JSON data
    print(f"📖 Loading JSON from: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    documents = data.get("documents", [])
    if not documents:
        print("❌ No documents found in JSON file")
        return
    
    print(f"Found {len(documents)} documents to index\n")
    
    # Initialize ChromaDB
    chroma_client, collection = init_chromadb(kb_name)
    
    all_ids = []
    all_embeddings = []
    all_documents = []
    all_metadatas = []
    
    total_chunks = 0
    
    for doc in documents:
        doc_id = doc["id"]
        text = doc["text"]
        metadata = doc["metadata"]
        
        print(f"Processing: {doc_id}")
        
        # Chunk the text
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        print(f"  Created {len(chunks)} chunks")
        total_chunks += len(chunks)
        
        # Get embeddings for all chunks
        embeddings = get_embeddings(chunks)
        
        # Prepare data for ChromaDB
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}_chunk{i}"
            all_ids.append(chunk_id)
            all_embeddings.append(embedding)
            all_documents.append(chunk)
            
            # Add chunk index to metadata
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            all_metadatas.append(chunk_metadata)
        
        print(f"  ✅ Successfully prepared {doc_id}")
    
    # Add all documents to ChromaDB in one batch
    print(f"\n📊 Indexing {total_chunks} chunks into ChromaDB...")
    collection.add(
        ids=all_ids,
        embeddings=all_embeddings,
        documents=all_documents,
        metadatas=all_metadatas
    )
    
    print(f"\n✅ Successfully indexed {total_chunks} chunks from {len(documents)} documents!")
    print(f"📦 Collection: {collection.name}")
    print(f"📈 Total items: {collection.count()}")


if __name__ == "__main__":
    # Get knowledge base name from command line or use default
    kb_name = sys.argv[1] if len(sys.argv) > 1 else "nutria"
    
    print(f"Starting ChromaDB indexing for knowledge base: {kb_name}\n")
    print("=" * 60)
    index_chromadb_json(kb_name=kb_name)
    print("=" * 60)
    print(f"\n✅ Indexing complete! Knowledge base '{kb_name}' is ready to be queried.")
