import os
from openai import OpenAI
from services.pdf_loader import load_pdf_smart_clauses
from core.config.supabase_client import SupabaseClient
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = SupabaseClient()

def insert_tenancy_agreement_chunks(file_path: str, tenancy_agreement_id: str):
    """Embed each clause/sub-clause and store label, title, and text in Supabase."""
    clauses = load_pdf_smart_clauses(file_path)
    print(f"📄 Processing {len(clauses)} clauses from {os.path.basename(file_path)}")

    for i, clause in enumerate(clauses, start=1):
        embedding = client.embeddings.create(
            model="text-embedding-3-small",
            input=clause["text"]
        ).data[0].embedding

        supabase.client.table("tenancy_agreement_chunks").insert({
            "tenancy_agreement_id": tenancy_agreement_id,
            "chunk_index": i,
            "clause_label": clause["label"],
            "clause_title": clause["title"],
            "content": clause["text"],
            "embedding": embedding,
            "metadata": {"source": os.path.basename(file_path)}
        }).execute()

    print(f"✅ Uploaded {len(clauses)} embeddings for tenancy_agreement_id={tenancy_agreement_id}")

def embed_full_tenancy_agreement(file_path: str, tenancy_agreement_id: str):
    """Embed the entire tenancy agreement and store it in the main table."""
    # Read entire PDF text
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)
    full_text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])

    # Generate embedding
    embedding = client.embeddings.create(
        model="text-embedding-3-small",  # or "text-embedding-3-large" if preferred
        input=full_text
    ).data[0].embedding

    # Update the main table
    supabase.client.table("tenancy_agreements").update({
        "agreement_embeddings": embedding
    }).eq("id", tenancy_agreement_id).execute()

    print(f"✅ Full tenancy agreement embedded for id={tenancy_agreement_id}")