import os
import re
import streamlit as st
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.schema import TextNode
from llama_index.core import SimpleDirectoryReader, Settings
from llama_index.embeddings.openai import OpenAIEmbedding

# Ensure we always use the same embedding model for this index
#Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-large")

# More forgiving clause detector, e.g.
# "2(b) SECURITY DEPOSIT"
# "2 (b) Security Deposit"
# "Clause 5 (f) Option To Renew"
CLAUSE_RE = re.compile(
    r"""(?imx)
    ^\s*(?:Clause\s*)?                 # optional 'Clause'
    (?P<label>\d{1,4}\s*\(?[a-zA-Z]?\)?)  # 5(b), 5 (b), 2023(a)
    [\s:.\-–]*                         # separators / spaces
    (?P<title>[A-Za-z][^\n\r]{0,100})  # up to 100 chars of title
    """
)

SUBCLAUSE_RE = re.compile(
    r"""(?imx)
    ^\s*\((?P<letter>[a-z])\)\s+
    (?P<title>[A-Za-z][^\n\r]{0,100})?
    """
)

class DocumentIndexManager:
    def __init__(
        self,
        pdf_path: str = None,
        persist_dir: str = None,
        cache_version: int = 1,
        embed_model=None,
        api_key= None,
    ):
        if pdf_path is None:
            # NOTE: no leading '/' in 'data' – otherwise join() ignores the prefix.
            pdf_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "data",
                "contracts",
                "Track_B_Tenancy_Agreement.pdf",
            )
        if persist_dir is None:
            persist_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "pdf_index_v2"
            )


        if embed_model is None:
            embed_model = OpenAIEmbedding(
                model="text-embedding-3-large",
                api_key=api_key,
            )

        self.pdf_path = pdf_path
        self.persist_dir = persist_dir
        self.cache_version = cache_version
        self.embed_model = embed_model

       
        self.index = self._load_or_build_index()



    # ---------- Clause-level splitting ----------
    
    
    def _split_into_clauses(self, text: str):
        """
        Returns list of (label, title, body_text) for each clause.
        We scan line-by-line looking for clause headers.
        """
        lines = text.splitlines()
        out, current = [], []
        current_label, current_title = None, None

        def flush():
            nonlocal current, current_label, current_title
            if current_label and current:
                body = "\n".join(current).strip()
                out.append((current_label, current_title or "", body))
            current, current_label, current_title = [], None, None

        current_number = None  # e.g. "5"

        for line in lines:
            m_clause = CLAUSE_RE.match(line)
            m_sub = SUBCLAUSE_RE.match(line) if not m_clause else None

            if m_clause:
                flush()
                raw_label = re.sub(r"\s+", "", m_clause.group("label")).lower()
                current_number = re.match(r"\d+", raw_label).group(0)
                current_label = raw_label                 # "5"
                current_title = (m_clause.group("title") or "").strip(" -–:")
            elif m_sub and current_number:
                # New lettered subclause inside current_number
                flush()
                letter = m_sub.group("letter").lower()    # "c"
                current_label = f"{current_number}({letter})"   # "5(c)"
                current_title = (m_sub.group("title") or "").strip(" -–:")
            else:
                current.append(line)
        
        flush()  # flush last clause
        return out

            


    @st.cache_resource
    def _cached_load_or_build_index(
        _self, pdf_path: str, persist_dir: str, cache_version: int
    ):
        """Load or build single-document clause-aware index."""

        if os.path.exists(persist_dir):

 
            storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
            index = load_index_from_storage(storage_context)
            print(f"Loaded existing index from {persist_dir}")



        else:
            print(f"Building new clause-aware index from {pdf_path}")
            reader = SimpleDirectoryReader(input_files=[pdf_path])
            docs = reader.load_data()
            all_nodes = []

            for doc in docs:
                text = doc.text or ""
                clauses = _self._split_into_clauses(text)
                for label, title, body in clauses:
                    enriched = f"Clause {label}: {title}\n\n{body}".strip()
                    # extract bare number part from label, e.g. "5(b)" -> "5"
                    mnum = re.match(r"(\d{1,4})", label)
                    num = mnum.group(1) if mnum else None
                    meta = {
                        "file_name": os.path.basename(pdf_path),
                        "clause_label": label,      # e.g. "5(b)"
                        "clause_num": num,          # e.g. "5"
                        "clause_title": title,      # e.g. "Option To Renew"
                        # keep page label if present
                        "page_label": doc.metadata.get("page_label"),
                    }
                    all_nodes.append(TextNode(text=enriched, metadata=meta))

            index = VectorStoreIndex(all_nodes)
            index.storage_context.persist(persist_dir=persist_dir)
            print(f"✅ Built and persisted index with {len(all_nodes)} clause nodes")
        return index

    def _load_or_build_index(self):
        return self._cached_load_or_build_index(
            self.pdf_path, self.persist_dir, self.cache_version
        )

    def rebuild(self):
        """Force rebuild."""
        if os.path.exists(self.persist_dir):
            for root, _, files in os.walk(self.persist_dir, topdown=False):
                for f in files:
                    try:
                        os.remove(os.path.join(root, f))
                    except Exception:
                        pass
                try:
                    os.rmdir(root)
                except Exception:
                    pass
        st.cache_resource.clear()
        self.cache_version += 1
        self.index = self._load_or_build_index()
