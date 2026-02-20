
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

def load_prompts():
    """Load prompts from JSON file"""
    try:
        with open(PROJECT_ROOT / 'config' / 'prompts.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading prompts: {e}")
        return {}

def build_prompt_from_template(language, context, question, history_text=""):
    """Build a complete prompt from the JSON template"""
    prompts_data = load_prompts()
    lang_data = prompts_data.get(language, prompts_data.get("fr", {}))
    
    if not lang_data:
        return None
    
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
    
    return prompt

def get_collection():
    global chroma_client, collection
    if collection is None:
        try:
            import os
            chroma_path = str(PROJECT_ROOT / "chroma_db")
            
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
                print(f"Collection 'transcripts' loaded with {collection.count()} documents")
            except:
                print("Creating new transcripts collection...")
                collection = chroma_client.create_collection(name="transcripts")
                print("Empty collection created")
                
        except Exception as e:
            print(f"ChromaDB error: {e}")
            return None
    return collection

def is_substantial_question(question):
    """
    Vérifie si la question est suffisamment substantielle pour mériter des PMIDs.
    Retourne False pour les questions trop courtes ou génériques.
    """
    if not question or len(question.strip()) < 10:
        return False
    
    # Compter les mots significatifs (au moins 3 caractères)
    words = [w for w in question.split() if len(w) >= 3]
    if len(words) < 3:
        return False
    
    # Liste de phrases génériques qui ne méritent pas de PMIDs
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

def get_pmids_from_contexts(contexts, metadatas=None):
    """Extract PMIDs from contexts. If metadatas with 'source' info is provided,
    look up chunk_0 of each source document to find PMIDs that may not be
    in the matched chunks."""
    pmids = set()
    # First, check the matched chunks themselves
    for doc in contexts:
        pmids.update(extract_pmids_from_text(doc))
    # If metadatas available, look up chunk_0 of each unique source for PMIDs
    if metadatas and not pmids:
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
                            pmids.update(extract_pmids_from_text(doc))
                except Exception as e:
                    print(f'Error fetching chunk_0 for PMIDs: {e}')
    return list(pmids)

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
        # Store empty PMIDs list in session for refusal
        if session is not None and question_id is not None:
            if 'pmids' not in session:
                session['pmids'] = {}
            session['pmids'][question_id] = []
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

        # Extraire les PMIDs du contexte (with source metadata lookup)
        # Only extract PMIDs for substantial questions (not for generic/short questions)
        pmids = []
        if is_substantial_question(question):
            metadatas = results.get('metadatas', [[]])[0]
            pmids = get_pmids_from_contexts(contexts, metadatas=metadatas)
        
        # Save PMIDs in session if provided
        if session is not None and question_id is not None:
            if 'pmids' not in session:
                session['pmids'] = {}
            session['pmids'][question_id] = pmids

        # Build prompt using template from JSON
        prompt = build_prompt_from_template(language, context, question, history_text)
        
        if not prompt:
            yield "Error: Unable to load prompt template."
            return
                

        #Save prompt for debugging
        # with open("debug_prompt.txt", "w", encoding="utf-8") as f:
        #     f.write(prompt)

        # Get streaming response from GPT
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
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

    except Exception as e:
        yield f"Error processing your question: {str(e)}"


def ask_question_stream_gemini(question, language="fr", timezone="UTC", locale="fr-FR", top_k=5, model_name="gemini-2.5-flash"):
    """Streaming answer using Gemini, mirroring ask_question_stream flow."""
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
            n_results=top_k
        )

        if not results['documents'] or not results['documents'][0]:
            yield "No relevant information found. Please make sure you have indexed some transcripts."
            return

        # Build context from results
        contexts = []
        for i, doc in enumerate(results['documents'][0]):
            contexts.append(doc)
        context = "\n\n".join(contexts)

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
        yield f"Error processing your question (Gemini): {str(e)}"
