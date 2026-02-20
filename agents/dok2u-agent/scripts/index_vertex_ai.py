import os
import json
from dotenv import load_dotenv
from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
from openai import OpenAI
from pathlib import Path


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent
# Load environment variables from the correct location
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Initialize clients
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Vertex AI configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
REGION = os.getenv("GCP_REGION", "us-east4")
INDEX_DISPLAY_NAME = os.getenv("VERTEX_INDEX_NAME")
ENDPOINT_DISPLAY_NAME = os.getenv("VERTEX_ENDPOINT_NAME")
DEPLOYED_INDEX_ID = os.getenv("VERTEX_DEPLOYED_INDEX_ID")

# Initialize Vertex AI
aiplatform.init(project=PROJECT_ID, location=REGION)


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


def create_index():
    """Create a Vertex AI Vector Search index"""
    try:
        # Create index configuration
        index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
            display_name=INDEX_DISPLAY_NAME,
            dimensions=3072,  # text-embedding-3-large dimension
            approximate_neighbors_count=10,
            distance_measure_type="DOT_PRODUCT_DISTANCE",
            description="Vector index for Ben Nutritionniste transcripts",
            leaf_node_embedding_count=1000,
            leaf_nodes_to_search_percent=10,
        )
        
        print(f"✅ Index created: {index.resource_name}")
        print(f"   Index ID: {index.name}")
        return index
    
    except Exception as e:
        print(f"❌ Error creating index: {str(e)}")
        return None


def create_index_endpoint():
    """Create an index endpoint for querying"""
    try:
        endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
            display_name=ENDPOINT_DISPLAY_NAME,
            description="Endpoint for Ben Nutritionniste vector search",
            public_endpoint_enabled=True,
        )
        
        print(f"✅ Endpoint created: {endpoint.resource_name}")
        print(f"   Endpoint ID: {endpoint.name}")
        return endpoint
    
    except Exception as e:
        print(f"❌ Error creating endpoint: {str(e)}")
        return None


def prepare_embeddings_for_vertex(folder_path=str(PROJECT_ROOT / "transcripts")):
    """Prepare embeddings data for Vertex AI index"""
    if not os.path.exists(folder_path):
        print(f"❌ Folder '{folder_path}' not found")
        return None
    
    txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    
    if not txt_files:
        print(f"❌ No .txt files found in '{folder_path}'")
        return None
    
    print(f"Found {len(txt_files)} documents to process\n")
    
    embeddings_data = []
    
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
            
            # Prepare data in Vertex AI format
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_id = f"{filename}_chunk{i}"
                embeddings_data.append({
                    "id": doc_id,
                    "embedding": embedding,
                    "restricts": [{
                        "namespace": "source",
                        "allow_list": [filename]
                    }],
                    "crowding_tag": str(i % 10)  # For diversity in results
                })
            
            print(f"  ✅ Successfully prepared {filename}")
            
        except Exception as e:
            print(f"  ❌ Error processing {filename}: {str(e)}")
    
    return embeddings_data


def save_embeddings_to_gcs(embeddings_data, bucket_name, directory="embeddings"):
    """Save embeddings to Google Cloud Storage in batches"""
    try:
        from google.cloud import storage
        
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        
        # Split embeddings into batches and save as separate files
        batch_size = 100
        batch_count = 0
        
        for i in range(0, len(embeddings_data), batch_size):
            batch = embeddings_data[i:i + batch_size]
            
            # Create JSONL content (one JSON per line)
            jsonl_content = "\n".join([json.dumps({
                "id": item["id"],
                "embedding": item["embedding"]
            }) for item in batch])
            
            # Upload batch file
            blob_name = f"{directory}/batch_{batch_count:04d}.json"
            blob = bucket.blob(blob_name)
            blob.upload_from_string(jsonl_content, content_type='application/json')
            batch_count += 1
            
            print(f"  Uploaded batch {batch_count} ({len(batch)} embeddings)")
        
        gcs_uri = f"gs://{bucket_name}/{directory}"
        print(f"✅ All embeddings saved to: {gcs_uri}")
        return gcs_uri
    
    except Exception as e:
        print(f"❌ Error saving to GCS: {str(e)}")
        return None


def update_index_with_embeddings(index, gcs_uri):
    """Update the index with embeddings from GCS"""
    try:
        # Update index with new embeddings
        index = index.update_embeddings(
            contents_delta_uri=gcs_uri,
        )
        
        print(f"✅ Index updated with embeddings from {gcs_uri}")
        return index
    
    except Exception as e:
        print(f"❌ Error updating index: {str(e)}")
        return None


def deploy_index_to_endpoint(index, endpoint):
    """Deploy the index to an endpoint for querying"""
    try:
        print(f"Deploying with machine type: n1-standard-16")
        print("This operation will take 15-30 minutes...")
        
        endpoint.deploy_index(
            index=index,
            deployed_index_id=DEPLOYED_INDEX_ID,
            machine_type="n1-standard-16",
            min_replica_count=1,
            max_replica_count=1,
        )
        
        print(f"✅ Index deployment initiated")
        print(f"   Deployed Index ID: {DEPLOYED_INDEX_ID}")
        print(f"\nNote: Deployment is asynchronous and will take 15-30 minutes.")
        print(f"\nCheck status with:")
        print(f"  gcloud ai index-endpoints describe {endpoint.resource_name} --region={REGION}")
        return endpoint
    
    except Exception as e:
        print(f"❌ Error deploying index: {str(e)}")
        print("\nTry deploying manually with:")
        print(f"  gcloud ai index-endpoints deploy-index {endpoint.resource_name} \\")
        print(f"    --deployed-index-id={DEPLOYED_INDEX_ID} \\")
        print(f"    --display-name={DEPLOYED_INDEX_ID} \\")
        print(f"    --index={index.resource_name} \\")
        print(f"    --machine-type=n1-standard-16 \\")
        print(f"    --min-replica-count=1 \\")
        print(f"    --region={REGION}")
        return None


def index_to_vertex_ai(folder_path=str(PROJECT_ROOT / "transcripts"), bucket_name=None):
    """Complete workflow to index documents to Vertex AI Vector Search"""
    print("Starting Vertex AI Vector Search indexing...\n")
    
    if not bucket_name:
        bucket_name = f"{PROJECT_ID}-vector-embeddings"
        print(f"Using default bucket name: {bucket_name}")
    
    # Step 1: Prepare embeddings
    print("\n=== Step 1: Preparing embeddings ===")
    embeddings_data = prepare_embeddings_for_vertex(folder_path)
    
    if not embeddings_data:
        print("❌ No embeddings data prepared. Exiting.")
        return
    
    print(f"✅ Prepared {len(embeddings_data)} embeddings")
    
    # Step 2: Create index (if needed)
    print("\n=== Step 2: Creating/Getting index ===")
    try:
        # Try to get existing index
        indexes = aiplatform.MatchingEngineIndex.list(
            filter=f'display_name="{INDEX_DISPLAY_NAME}"'
        )
        if indexes:
            index = indexes[0]
            print(f"✅ Using existing index: {index.resource_name}")
        else:
            index = create_index()
            if not index:
                return
    except Exception as e:
        print(f"Creating new index due to: {str(e)}")
        index = create_index()
        if not index:
            return
    
    # Step 3: Save embeddings to GCS
    print("\n=== Step 3: Saving embeddings to GCS ===")
    gcs_uri = save_embeddings_to_gcs(embeddings_data, bucket_name)
    
    if not gcs_uri:
        print("❌ Failed to save embeddings to GCS. Exiting.")
        return
    
    # Step 4: Update index with embeddings
    print("\n=== Step 4: Updating index with embeddings ===")
    index = update_index_with_embeddings(index, gcs_uri)
    
    if not index:
        print("❌ Failed to update index. Exiting.")
        return
    
    # Step 5: Create/Get endpoint
    print("\n=== Step 5: Creating/Getting endpoint ===")
    try:
        endpoints = aiplatform.MatchingEngineIndexEndpoint.list(
            filter=f'display_name="{ENDPOINT_DISPLAY_NAME}"'
        )
        if endpoints:
            endpoint = endpoints[0]
            print(f"✅ Using existing endpoint: {endpoint.resource_name}")
        else:
            endpoint = create_index_endpoint()
            if not endpoint:
                return
    except Exception as e:
        print(f"Creating new endpoint due to: {str(e)}")
        endpoint = create_index_endpoint()
        if not endpoint:
            return
    
    # Step 6: Deploy index to endpoint
    print("\n=== Step 6: Deploying index to endpoint ===")
    endpoint = deploy_index_to_endpoint(index, endpoint)
    
    if not endpoint:
        print("❌ Failed to deploy index. Exiting.")
        return
    
    # Print configuration for .env
    print("\n" + "="*60)
    print("✅ INDEXING COMPLETE!")
    print("="*60)
    print("\nAdd these to your .env file:")
    print(f"VERTEX_INDEX_ID={index.name}")
    print(f"VERTEX_ENDPOINT_ID={endpoint.name}")
    print(f"VERTEX_DEPLOYED_INDEX_ID={DEPLOYED_INDEX_ID}")
    print(f"GCP_PROJECT_ID={PROJECT_ID}")
    print(f"GCP_REGION={REGION}")
    print("="*60)


if __name__ == "__main__":
    # Get bucket name from environment or use default
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    
    # Run indexing
    index_to_vertex_ai(folder_path=str(PROJECT_ROOT / "transcripts"), bucket_name=bucket_name)