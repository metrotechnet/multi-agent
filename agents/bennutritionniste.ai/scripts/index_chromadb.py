import os
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


# Initialize ChromaDB (stored locally) with explicit settings
chroma_path = str(PROJECT_ROOT / "chroma_db")
chroma_client = chromadb.PersistentClient(
    path=chroma_path,
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=False
    )
)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get or create collection
collection_name = "transcripts"
collection = chroma_client.get_or_create_collection(
    name=collection_name,
    metadata={"description": "AI Ben Nutritionniste transcripts"}
)

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

def index_text_files(folder_path=str(PROJECT_ROOT / "transcripts")):
    """Index all .txt files from the extracted folder"""
    if not os.path.exists(folder_path):
        print(f"❌ Folder '{folder_path}' not found")
        return
    
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
    print("Starting ChromaDB indexing...\n")
    index_text_files()
    print("\n✅ Indexing complete! Your documents are ready to be queried.")
