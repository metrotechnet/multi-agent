
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
# Refusal engine import
from core.refusal_engine import validate_user_query

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / '.env')

# Initialize ChromaDB client (local storage)
chroma_client = None
collection = None
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Get knowledge base name from environment or use default
KNOWLEDGE_BASE = os.getenv("KNOWLEDGE_BASE", "nutria")



def load_style_guides():
    """Load style guides from JSON file"""
    try:
        with open(PROJECT_ROOT / 'config' / 'style_guides.json', 'r', encoding='utf-8') as f:
            style_data = json.load(f)
        
        # Format the style guides for use in prompts
        formatted_guides = {}
        for lang, data in style_data.items():
            guide = f"# {data['title']}\n\n"
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

def load_prompts(kb_name=None):
    """
    Load prompts from JSON file in the knowledge base folder
    
    Args:
        kb_name: Name of the knowledge base (default: from KNOWLEDGE_BASE env var)
    """
    if kb_name is None:
        kb_name = KNOWLEDGE_BASE
    
    try:
        kb_path = PROJECT_ROOT / "knowledge-bases" / kb_name
        prompts_path = kb_path / 'prompts.json'
        
        # Fallback to config folder if not found in KB (for backward compatibility)
        if not prompts_path.exists():
            prompts_path = PROJECT_ROOT / 'config' / 'prompts.json'
            
        with open(prompts_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading prompts: {e}")
        return {}

def build_prompt_from_template(language, context, question, history_text=""):
    """Build a complete prompt from the JSON template. Returns (prompt, model_config)"""
    prompts_data = load_prompts()
    lang_data = prompts_data.get(language, prompts_data.get("fr", {}))
    
    # Extract model configuration
    model_config = {
        "supplier": prompts_data.get("model_supplier", "openai"),
        "name": prompts_data.get("model_name", "gpt-4o-mini")
    }
    
    if not lang_data:
        return None, model_config
    
    # Build communication style content
    comm_style = lang_data.get('communication_style', {})
    tone = comm_style.get('tone_and_voice', {})
    recurring = comm_style.get('recurring_messages', {})
    
    tone_content = f"## {tone.get('title', '')}\n"
    for char in tone.get('characteristics', []):
        tone_content += f"- {char}\n"
    
    recurring_content = f"\n## {recurring.get('title', '')}\n"
    for msg in recurring.get('messages', []):
        recurring_content += f"- « {msg} »\n"
    
    communication_style_content = tone_content + recurring_content
    
    # Build absolute rules content
    rules = lang_data.get('absolute_rules', {})
    rules_content = ""
    for rule in rules.get('rules', []):
        rules_content += f"- {rule}\n"
    
    # Build behavioral constraints content
    constraints = lang_data.get('behavioral_constraints', {})
    constraints_content = ""
    for constraint in constraints.get('constraints', []):
        constraints_content += f"- {constraint}\n"
    
    # Build the final prompt using the template
    template = lang_data.get('template', '')
    prompt = template.format(
        system_role=lang_data.get('system_role', ''),
        important_notice=lang_data.get('important_notice', ''),
        communication_style_title=comm_style.get('title', ''),
        communication_style_content=communication_style_content,
        absolute_rules_title=rules.get('title', ''),
        absolute_rules_content=rules_content,
        behavioral_constraints_title=constraints.get('title', ''),
        behavioral_constraints_content=constraints_content,
        context=context,
        history=history_text,
        question=question
    )
    
    return prompt, model_config

def get_collection(kb_name=None):
    """
    Get or create ChromaDB collection for the specified knowledge base
    
    Args:
        kb_name: Name of the knowledge base (default: from KNOWLEDGE_BASE env var)
    """
    global chroma_client, collection
    
    if kb_name is None:
        kb_name = KNOWLEDGE_BASE
    
    if collection is None:
        try:
            import os
            kb_path = PROJECT_ROOT / "knowledge-bases" / kb_name
            chroma_path = str(kb_path / "chroma_db")
            
            if not os.path.exists(chroma_path):
                print(f"Warning: ChromaDB path not found: {chroma_path}")
                print(f"Make sure knowledge base '{kb_name}' is indexed first.")
                return None
            
            # Create ChromaDB client with optimized settings for Cloud Run
            chroma_client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )
            
            # Get collection (will create if doesn't exist)
            try:
                collection = chroma_client.get_collection(name="transcripts")
                print(f"Collection 'transcripts' loaded from '{kb_name}' with {collection.count()} documents")
            except:
                print(f"Creating new transcripts collection for '{kb_name}'...")
                collection = chroma_client.create_collection(
                    name="transcripts",
                    metadata={"kb_name": kb_name}
                )
                print("Empty collection created")
                
        except Exception as e:
            print(f"ChromaDB error: {e}")
            return None
    return collection

def is_substantial_question(question):
    """
    Vérifie si la question est suffisamment substantielle pour mériter des liens.
    Retourne False pour les questions trop courtes ou génériques.
    """
    if not question or len(question.strip()) < 10:
        return False
    
    # Compter les mots significatifs (au moins 3 caractères)
    words = [w for w in question.split() if len(w) >= 3]
    if len(words) < 3:
        return False
    
    # Liste de phrases génériques qui ne méritent pas de liens
    generic_phrases = [
        'pose une question',
        'aide moi',
        'bonjour',
        'salut',
        'merci',
        'hello',
        'hi',
        'help',
        'ask a question',
        'ask question',
    ]
    
    question_lower = question.lower().strip()
    for phrase in generic_phrases:
        if question_lower == phrase or question_lower == phrase + '?':
            return False
    
    return True

def extract_pmids_from_text(text):
    """Extrait toutes les références PMID d'un texte."""
    return re.findall(r'PMID:\s*\d+', text)

def get_links_from_contexts(contexts, metadatas=None):
    """Extract links from contexts and metadata.
    
    Priority:
    1. Check metadatas for 'links' field (new ChromaDB format)
    2. Extract from matched chunks text (fallback)
    3. Look up chunk_0 of source documents (last resort)
    """
    links = set()
    
    # Priority 1: Check metadatas for direct link references (new format)
    if metadatas:
        for meta in metadatas:
            if isinstance(meta, dict) and 'links' in meta and meta['links']:
                # Links are stored as comma-separated string
                link_list = meta['links'].split(',')
                for link in link_list:
                    link = link.strip()
                    if link:
                        links.add(f"PMID: {link}")
    
    # If we found links in metadata, return them immediately
    if links:
        return list(links)
    
    # Priority 2: Fallback - check the matched chunks text themselves
    for doc in contexts:
        links.update(extract_pmids_from_text(doc))
    
    # Priority 3: If still no links and metadatas available, look up chunk_0
    if not links and metadatas:
        col = get_collection()
        if col:
            sources = set()
            for meta in metadatas:
                if isinstance(meta, dict) and 'source' in meta:
                    sources.add(meta['source'])
            chunk0_ids = [src + '_chunk0' for src in sources]
            if chunk0_ids:
                try:
                    results = col.get(ids=chunk0_ids, include=['documents'])
                    for doc in results.get('documents', []):
                        if doc:
                            links.update(extract_pmids_from_text(doc))
                except Exception as e:
                    print(f'Error fetching chunk_0 for links: {e}')
    
    return list(links)

def ask_question_stream(question, language="fr", timezone="UTC", locale="fr-FR", top_k=5, conversation_history=None, session=None, question_id=None):
    """Streaming version of ask_question with language support and conversation history"""
    # Use conversation_history if provided, otherwise empty list
    if conversation_history is None:
        conversation_history = []

    # Build history_text for refusal_engine
    history_text = ""
    if conversation_history and len(conversation_history) > 1:
        history_text = "\n\nHISTORIQUE DE LA CONVERSATION:\n"
        recent_history = conversation_history[-7:-1] if len(conversation_history) > 1 else []
        for msg in recent_history:
            role_label = "Utilisateur" if msg['role'] == 'user' else "Assistant"
            history_text += f"{role_label}: {msg['content']}\n"

    # context is not available yet (need ChromaDB), so pass empty string for now
    refusal_result = validate_user_query(question, llm_call_fn=None, language=language)
    if refusal_result and refusal_result.get("decision") == "refuse":
        # Store empty links list in session for refusal
        if session is not None and question_id is not None:
            if 'links' not in session:
                session['links'] = {}
            session['links'][question_id] = []
        yield "__REFUSAL__"
        yield refusal_result["answer"]
        return

    col = get_collection()
    if col is None:
        yield "Error: ChromaDB collection is not available. Please run 'python index_chromadb.py' first to index your documents."
        return

    try:
        # Get embedding for the question
        query_emb = client.embeddings.create(
            model="text-embedding-3-large", 
            input=question
        ).data[0].embedding

        # Query ChromaDB
        results = col.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            include=['documents', 'metadatas']
        )

        if not results['documents'] or not results['documents'][0]:
            yield "No relevant information found. Please make sure you have indexed some transcripts."
            return

        # Build context from results
        contexts = []
        for i, doc in enumerate(results['documents'][0]):
            contexts.append(doc)
        context = "\n\n".join(contexts)

        # Extraire les liens du contexte (with source metadata lookup)
        # Only extract links for substantial questions (not for generic/short questions)
        links = []
        if is_substantial_question(question):
            metadatas = results.get('metadatas', [[]])[0]
            links = get_links_from_contexts(contexts, metadatas=metadatas)
        
        # Save links in session if provided
        if session is not None and question_id is not None:
            if 'links' not in session:
                session['links'] = {}
            session['links'][question_id] = links

        # Build prompt using template from JSON
        prompt, model_config = build_prompt_from_template(language, context, question, history_text)
        
        if not prompt:
            yield "Error: Unable to load prompt template."
            return
                
 
        #Save prompt for debugging
        # with open("debug_prompt.txt", "w", encoding="utf-8") as f:
        #     f.write(prompt)

        # Get streaming response from configured LLM
        model_name = model_config.get('name', 'gpt-4o-mini')
        model_supplier = model_config.get('supplier', 'openai')
        
        if model_supplier == 'openai':
            # OpenAI streaming
            stream = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                stream=True
            )

            first_chunk = True
            answer = ""
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    # Strip leading whitespace from first chunk only
                    if first_chunk:
                        content = content.lstrip()
                        first_chunk = False
                    if content:
                        answer += content
                        yield content
                        
        elif model_supplier == 'gemini':
            # Gemini streaming
            model = genai.GenerativeModel(model_name, generation_config={
                "temperature": 0.7
            })
            
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
        else:
            yield f"Error: Model supplier '{model_supplier}' not supported. Use 'openai' or 'gemini'."
            return

    except Exception as e:
        yield f"Error processing your question: {str(e)}"


def ask_question_stream_gemini(question, language="fr", timezone="UTC", locale="fr-FR", top_k=5, conversation_history=None, session=None, question_id=None, model_name="gemini-2.0-flash-exp"):
    """Streaming answer using Gemini with new template system. 
    This function now uses build_prompt_from_template for consistency.
    """
    # Use conversation_history if provided, otherwise empty list
    if conversation_history is None:
        conversation_history = []

    # Build history_text for refusal_engine
    history_text = ""
    if conversation_history and len(conversation_history) > 1:
        history_text = "\n\nHISTORIQUE DE LA CONVERSATION:\n"
        recent_history = conversation_history[-7:-1] if len(conversation_history) > 1 else []
        for msg in recent_history:
            role_label = "Utilisateur" if msg['role'] == 'user' else "Assistant"
            history_text += f"{role_label}: {msg['content']}\n"

    # Refusal engine check
    refusal_result = validate_user_query(question, llm_call_fn=None, language=language)
    if refusal_result and refusal_result.get("decision") == "refuse":
        if session is not None and question_id is not None:
            if 'links' not in session:
                session['links'] = {}
            session['links'][question_id] = []
        yield "__REFUSAL__"
        yield refusal_result["answer"]
        return

    col = get_collection()
    if col is None:
        yield "Error: ChromaDB collection is not available. Please run 'python index_chromadb.py' first to index your documents."
        return

    try:
        # Get embedding for the question using OpenAI (keeps Chroma flow unchanged)
        query_emb = client.embeddings.create(
            model="text-embedding-3-large",
            input=question
        ).data[0].embedding

        # Query ChromaDB
        results = col.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            include=['documents', 'metadatas']
        )

        if not results['documents'] or not results['documents'][0]:
            yield "No relevant information found. Please make sure you have indexed some transcripts."
            return

        # Build context from results
        contexts = []
        for i, doc in enumerate(results['documents'][0]):
            contexts.append(doc)
        context = "\n\n".join(contexts)

        # Extract links from context
        links = []
        if is_substantial_question(question):
            metadatas = results.get('metadatas', [[]])[0]
            links = get_links_from_contexts(contexts, metadatas=metadatas)
        
        # Save links in session if provided
        if session is not None and question_id is not None:
            if 'links' not in session:
                session['links'] = {}
            session['links'][question_id] = links

        # Build prompt using template from JSON (same as OpenAI version)
        prompt, model_config = build_prompt_from_template(language, context, question, history_text)
        
        if not prompt:
            yield "Error: Unable to load prompt template."
            return

        # Configure Gemini model
        model = genai.GenerativeModel(model_name, generation_config={
            "temperature": 0.7
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
        yield f"Error processing your question (Gemini): {str(e)}"
