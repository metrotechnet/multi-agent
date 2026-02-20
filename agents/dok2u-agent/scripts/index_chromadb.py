import os
import sys
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from pathlib import Path


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent
# Load environment variables from the correct location
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_knowledge_base_path(kb_name="nutria"):
    """Get the path to a specific knowledge base"""
    return PROJECT_ROOT / "knowledge-bases" / kb_name


def init_chromadb(kb_name="nutria"):
    """Initialize ChromaDB client for a specific knowledge base"""
    kb_path = get_knowledge_base_path(kb_name)
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
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"description": f"Knowledge base: {kb_name}", "kb_name": kb_name}
    )
    
    return chroma_client, collection

def get_embeddings(texts):
    """Get embeddings from OpenAI"""
    if isinstance(texts, str):
        texts = [texts]
    resp = client.embeddings.create(model="text-embedding-3-large", input=texts)
    return [e.embedding for e in resp.data]

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

def index_text_files(kb_name="nutria", folder_type="extracted_texts"):
    """
    Index all .txt files from the specified folder in a knowledge base
    
    Args:
        kb_name: Name of the knowledge base (default: "nutria")
        folder_type: Type of folder to index ("extracted_texts", "transcripts", "documents")
    """
    kb_path = get_knowledge_base_path(kb_name)
    folder_path = str(kb_path / folder_type)
    
    if not os.path.exists(folder_path):
        print(f"❌ Folder '{folder_path}' not found")
        print(f"   Make sure the knowledge base '{kb_name}' exists in knowledge-bases/")
        return
    
    # Initialize ChromaDB for this knowledge base
    chroma_client, collection = init_chromadb(kb_name)
    
    txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    
    if not txt_files:
        print(f"❌ No .txt files found in '{folder_path}'")
        return
    
    print(f"Found {len(txt_files)} documents to index\n")
    
    all_ids = []
    all_embeddings = []
    all_documents = []
    all_metadatas = []
    
    for filename in txt_files:
        file_path = os.path.join(folder_path, filename)
        print(f"Processing: {filename}")
        
        try:
            # Read text file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if not text.strip():
                print(f"  ⚠️ No text found in {filename}")
                continue
            
            print(f"  Extracted {len(text)} characters")
            
            # Split into chunks
            chunks = chunk_text(text, chunk_size=500, overlap=50)
            print(f"  Created {len(chunks)} chunks")
            
            # Get embeddings for chunks
            embeddings = get_embeddings(chunks)
            
            # Prepare data for ChromaDB
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_id = f"{filename}_chunk{i}"
                all_ids.append(doc_id)
                all_embeddings.append(embedding)
                all_documents.append(chunk)
                all_metadatas.append({
                    "source": filename,
                    "chunk_index": i
                })
            
            print(f"  ✅ Successfully prepared {filename}")
            
        except Exception as e:
            print(f"  ❌ Error processing {filename}: {str(e)}")
    
    # Add all documents to ChromaDB in one batch
    if all_ids:
        print(f"\nIndexing {len(all_ids)} chunks into ChromaDB...")
        collection.add(
            ids=all_ids,
            embeddings=all_embeddings,
            documents=all_documents,
            metadatas=all_metadatas
        )
        print(f"✅ Successfully indexed {len(all_ids)} chunks from {len(txt_files)} documents!")
    else:
        print("❌ No data to index")

if __name__ == "__main__":
    # Get knowledge base name from command line or use default
    kb_name = sys.argv[1] if len(sys.argv) > 1 else "nutria"
    folder_type = sys.argv[2] if len(sys.argv) > 2 else "extracted_texts"
    
    print(f"Starting ChromaDB indexing for knowledge base: {kb_name}\n")
    print(f"Indexing from folder: {folder_type}\n")
    index_text_files(kb_name=kb_name, folder_type=folder_type)
    print(f"\n✅ Indexing complete! Knowledge base '{kb_name}' is ready to be queried.")
