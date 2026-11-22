import os
from supabase.client import create_client
from sentence_transformers import SentenceTransformer
from typing import List, Dict

# --- INITIALIZATION ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Supabase environment variables not set.")

# Use the Service Key for backend operations (bypasses RLS for insertion)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Initialize the Hugging Face Embedding Model (384 dimensions)
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
try:
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    VECTOR_DIMENSION = embedder.get_sentence_embedding_dimension()
    print(f"Loaded embedding model: {EMBEDDING_MODEL_NAME} (Dim: {VECTOR_DIMENSION})")
except Exception as e:
    print(f"Error loading SentenceTransformer: {e}")
    # Fallback/Error handling needed in production environment

# --- CORE FUNCTIONS ---

def _format_transaction_to_text(transaction: Dict) -> str:
    """Formats a raw transaction dictionary into a single, descriptive text chunk."""
    # Ensure fields exist before accessing them, or use defaults
    merchant = transaction.get('merchant_name') or 'Unknown Merchant'
    category = transaction.get('category') or ['Uncategorized']
    date = transaction.get('date', 'N/A')
    amount = transaction.get('amount', 0.0)
    
    return (
        f"Transaction Context: Date: {date}, Amount: ${amount:.2f}, "
        f"Merchant: {merchant}, Category: {', '.join(category)}, "
        f"Plaid ID: {transaction.get('transaction_id')}"
    )

def ingest_transactions_to_supabase(
    transactions: List[Dict], 
    user_uuid: str
) -> Dict:
    """
    Processes a list of transactions, generates embeddings, and inserts them into Supabase.
    """
    
    documents = []
    
    for tx in transactions:
        text_chunk = _format_transaction_to_text(tx)
        
        # 1. Generate embedding
        embedding = embedder.encode(text_chunk).tolist()
        
        # 2. Prepare document for insertion
        documents.append({
            "user_id": user_uuid,
            "content": text_chunk,
            "embedding": embedding,
            # Store the original transaction ID to check for duplicates later
            "original_transaction_id": tx.get('transaction_id') 
        })

    if not documents:
        return {"status": "success", "message": "No transactions to ingest."}
        
    # 3. Store in Supabase using the table name 'transaction_vectors'
    try:
        response = supabase.table("transaction_vectors").insert(documents).execute()
        return {
            "status": "success", 
            "message": f"Successfully ingested {len(response.data)} new vectors for user {user_uuid}."
        }
    except Exception as e:
        # Log the error properly in a production environment
        return {"status": "error", "message": f"Supabase ingestion failed: {e}"}