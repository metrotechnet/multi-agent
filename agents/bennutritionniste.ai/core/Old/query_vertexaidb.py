import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
import google.generativeai as genai

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Load environment variables from the correct location
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Initialize ChromaDB client (local storage)
chroma_client = None
collection = None
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize Vertex AI
project_id = os.getenv("GCP_PROJECT_ID")
location = os.getenv("GCP_REGION")
index_id = os.getenv("VERTEX_INDEX_ID")
endpoint_id = os.getenv("VERTEX_ENDPOINT_ID")
deployed_index_id=os.getenv("VERTEX_DEPLOYED_INDEX_ID")

# Vertex AI Vector Search client (lazy initialization)
vertex_ai_index = None
vertex_ai_endpoint = None

def load_style_guides():
    """Load style guides from JSON file"""
    try:
        with open(PROJECT_ROOT / 'config' / 'style_guides.json', 'r', encoding='utf-8') as f:
            style_data = json.load(f)
        
        # Format the style guides for use in prompts
        formatted_guides = {}
        for lang, data in style_data.items():
            guide = f"# {data['title']}\n\n"
            guide += f"## {data['narrative_structure']['title']}\n"
            for i, step in enumerate(data['narrative_structure']['steps'], 1):
                guide += f"{i}. {step}\n"
            guide += f"\n## {data['characteristic_expressions']['title']}\n"
            for phrase in data['characteristic_expressions']['phrases']:
                guide += f"- \"{phrase}\"\n"
            guide += f"\n## {data['tone_and_voice']['title']}\n"
            for char in data['tone_and_voice']['characteristics']:
                guide += f"- {char}\n"
            guide += f"\n## {data['key_messages']['title']}\n"
            for msg in data['key_messages']['messages']:
                guide += f"- \"{msg}\"\n"
            formatted_guides[lang] = guide
        
        return formatted_guides, style_data
    except Exception as e:
        print(f"Error loading style guides: {e}")
        return {}, {}

def load_system_prompts():
    """Load system prompts from JSON file"""
    try:
        with open(PROJECT_ROOT / 'config' / 'system_prompts.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading system prompts: {e}")
        return {}


# ============================================================================
# VERTEX AI VECTOR SEARCH FUNCTIONS
# ============================================================================

def get_vertex_ai_index():
    """Initialize and return Vertex AI Vector Search index client."""
    global vertex_ai_index, vertex_ai_endpoint
    
    if vertex_ai_index is None or vertex_ai_endpoint is None:
        try:
            from google.cloud import aiplatform
            from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
            


            
            if not index_id or not endpoint_id:
                print("Error: VERTEX_INDEX_ID and VERTEX_ENDPOINT_ID must be set in environment")
                return None, None
            
            aiplatform.init(project=project_id, location=location)
            
            # Get index and endpoint
            vertex_ai_index = MatchingEngineIndex(index_name=index_id)
            vertex_ai_endpoint = MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_id)
            
            print(f"Vertex AI Vector Search initialized: {index_id}")
            
        except Exception as e:
            print(f"Vertex AI initialization error: {e}")
            return None, None
    
    return vertex_ai_index, vertex_ai_endpoint


def query_vertex_ai(query_embedding, top_k=5):
    """Query Vertex AI Vector Search with an embedding vector."""
    try:
        _, endpoint = get_vertex_ai_index()
        
        if endpoint is None:
            return None
        
        # Query the index
        response = endpoint.find_neighbors(
            deployed_index_id=deployed_index_id,
            queries=[query_embedding],
            num_neighbors=top_k
        )
        
        # Extract documents from response
        documents = []
        for neighbor in response[0]:
            # Assuming metadata contains the document text
            doc_text = neighbor.id  # or neighbor.metadata.get('text', '')
            documents.append(doc_text)
        
        return documents
        
    except Exception as e:
        print(f"Vertex AI query error: {e}")
        return None


def ask_question_stream_vertex(question, language="fr", timezone="UTC", locale="fr-FR", top_k=5):
    """Streaming version using Vertex AI Vector Search with OpenAI."""
    _, endpoint = get_vertex_ai_index()
    
    if endpoint is None:
        yield "Error: Vertex AI Vector Search is not available. Please configure VERTEX_INDEX_ID and VERTEX_ENDPOINT_ID."
        return
    
    try:
        # Get embedding for the question
        query_emb = client.embeddings.create(
            model="text-embedding-3-large", 
            input=question
        ).data[0].embedding
        
        # Query Vertex AI Vector Search
        documents = query_vertex_ai(query_emb, top_k=top_k)
        
        if not documents or len(documents) == 0:
            yield "No relevant information found in Vertex AI Vector Search."
            return
        
        # Build context from results
        context = "\n\n".join(documents)
        
        # Load Style Card from JSON based on language
        style_guides, style_data = load_style_guides()
        style_guide = style_guides.get(language, style_guides.get("fr", ""))
        
        # Get not found message for the language
        not_found_msg = style_data.get(language, {}).get('not_found_message', 
                                                        style_data.get('fr', {}).get('not_found_message', 
                                                        "Information not found in current content."))
        
        # Load system prompts from JSON
        system_prompts_data = load_system_prompts()
        
        # Create dynamic prompts with context and style guide
        base_prompt_fr = system_prompts_data.get('fr', {}).get('content', '')
        base_prompt_en = system_prompts_data.get('en', {}).get('content', '')
        
        # Build full prompts with style guide and context
        prompts = {
            "fr": f"""{base_prompt_fr}

            {style_guide}

            CONTEXTE DISPONIBLE:
            {context}

            QUESTION DE L'UTILISATEUR: {question}

            INSTRUCTIONS SPÉCIALES:
            - Si l'information n'est pas disponible dans le contexte, réponds: "{not_found_msg}"
            - Applique rigoureusement ta structure narrative et tes expressions caractéristiques
            - Reste dans ton rôle de Ben avec ton style unique et reconnaissable""",

            "en": f"""{base_prompt_en}

            {style_guide}

            AVAILABLE CONTEXT:
            {context}

            USER QUESTION: {question}

            SPECIAL INSTRUCTIONS:
            - If information is not available in the context, respond: "{not_found_msg}"
            - Strictly apply your narrative structure and characteristic expressions
            - Stay in your role as Ben with your unique and recognizable style"""
        }
        
        # Use French as fallback for unsupported languages
        prompt = prompts.get(language, prompts["fr"]) if language in ["fr", "en"] else prompts["fr"]

        # Get streaming response from GPT
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            stream=True
        )
        
        first_chunk = True
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                # Strip leading whitespace from first chunk only
                if first_chunk:
                    content = content.lstrip()
                    first_chunk = False
                if content:  # Only yield if not empty after stripping
                    yield content
        
    except Exception as e:
        yield f"Error processing your question (Vertex AI): {str(e)}"


def ask_question_stream_vertex_gemini(question, language="fr", timezone="UTC", locale="fr-FR", top_k=5, model_name="gemini-2.5-flash"):
    """Streaming version using Vertex AI Vector Search with Gemini."""
    _, endpoint = get_vertex_ai_index()
    
    if endpoint is None:
        yield "Error: Vertex AI Vector Search is not available. Please configure VERTEX_INDEX_ID and VERTEX_ENDPOINT_ID."
        return
    
    try:
        # Get embedding for the question using OpenAI (for consistency)
        query_emb = client.embeddings.create(
            model="text-embedding-3-large",
            input=question
        ).data[0].embedding

        # Query Vertex AI Vector Search
        documents = query_vertex_ai(query_emb, top_k=top_k)
        
        if not documents or len(documents) == 0:
            yield "No relevant information found in Vertex AI Vector Search."
            return

        # Build context from results
        context = "\n\n".join(documents)

        # Load Style Card and system prompts
        style_guides, style_data = load_style_guides()
        style_guide = style_guides.get(language, style_guides.get("fr", ""))
        not_found_msg = style_data.get(language, {}).get(
            'not_found_message',
            style_data.get('fr', {}).get('not_found_message', "Information not found in current content.")
        )

        system_prompts_data = load_system_prompts()
        base_prompt_fr = system_prompts_data.get('fr', {}).get('content', '')
        base_prompt_en = system_prompts_data.get('en', {}).get('content', '')

        prompts = {
            "fr": f"""{base_prompt_fr}

            {style_guide}

            CONTEXTE DISPONIBLE:
            {context}

            QUESTION DE L'UTILISATEUR: {question}

            INSTRUCTIONS SPÉCIALES:
            - Si l'information n'est pas disponible dans le contexte, réponds: "{not_found_msg}"
            - Applique rigoureusement ta structure narrative et tes expressions caractéristiques
            - Reste dans ton rôle de Ben avec ton style unique et reconnaissable""",

            "en": f"""{base_prompt_en}

            {style_guide}

            AVAILABLE CONTEXT:
            {context}

            USER QUESTION: {question}

            SPECIAL INSTRUCTIONS:
            - If information is not available in the context, respond: "{not_found_msg}"
            - Strictly apply your narrative structure and characteristic expressions
            - Stay in your role as Ben with your unique and recognizable style"""
        }

        prompt = prompts.get(language, prompts["fr"]) if language in ["fr", "en"] else prompts["fr"]

        # Configure model (temperature to mirror OpenAI setup)
        model = genai.GenerativeModel(model_name, generation_config={
            "temperature": 0.3
        })

        # Stream tokens
        response = model.generate_content(prompt, stream=True)

        first_chunk = True
        for chunk in response:
            text = getattr(chunk, "text", None)
            if text:
                if first_chunk:
                    text = text.lstrip()
                    first_chunk = False
                if text:
                    yield text

    except Exception as e:
        yield f"Error processing your question (Vertex AI + Gemini): {str(e)}"

