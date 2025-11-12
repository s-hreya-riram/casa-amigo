import os
import re
import streamlit as st
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.schema import TextNode
from llama_index.core import SimpleDirectoryReader

# Detect clauses and sub-clauses: e.g. "5(b) Interest for Rent Arrears"
CLAUSE_RE = re.compile(
    r"""(?imx)
    ^\s*(?:Clause\s*)?
    (?P<label>\d{1,4}(?:\([a-z]\))?)     # e.g. 5(b)
    \s*[:.\-–]?\s*(?P<title>[A-Za-z][^\n]{0,80})
    """
)

class DocumentIndexManager:
    def __init__(self,
                 pdf_path: str = None,
                 persist_dir: str = None,
                 cache_version: int = 1):
        if pdf_path is None:
            pdf_path = os.path.join(os.path.dirname(__file__), "..", "..", "/data/contracts", "Track_B_Tenancy_Agreement.pdf")
        if persist_dir is None:
            persist_dir = os.path.join(os.path.dirname(__file__), "..", "..", "pdf_index_v2")

        self.pdf_path = pdf_path
        self.persist_dir = persist_dir
        self.cache_version = cache_version
        self.index = self._load_or_build_index()

    # ---------- Clause-level splitting ----------
    def _split_into_clauses(self, text: str):
        lines = text.splitlines()
        out, current = [], []
        current_label, current_title = None, None

        def flush():
            nonlocal current, current_label, current_title
            if current_label:
                out.append((current_label, current_title or "", "\n".join(current).strip()))
            current, current_label, current_title = [], None, None

        for line in lines:
            m = CLAUSE_RE.match(line)
            if m:
                flush()
                current_label = m.group("label")
                current_title = m.group("title").strip(" -–:")
                continue
            current.append(line)

        flush()
        return out

    def _pdf_to_nodes(self):
        reader = SimpleDirectoryReader(input_files=[self.pdf_path])
        docs = reader.load_data()
        all_nodes = []
        for doc in docs:
            text = doc.text or ""
            clauses = self._split_into_clauses(text)
            for label, title, body in clauses:
                enriched = f"Clause {label}: {title}\n\n{body}".strip()
                meta = {
                    "file_name": os.path.basename(self.pdf_path),
                    "clause_label": label,
                    "clause_num": re.match(r"\d+", label).group(0),
                    "clause_title": title,
                    "page_label": doc.metadata.get("page_label"),
                }
                all_nodes.append(TextNode(text=enriched, metadata=meta))
        return all_nodes

    @st.cache_resource
    def _cached_load_or_build_index(_self, pdf_path: str, persist_dir: str, cache_version: int):
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
                lines = text.splitlines()
                current_clause = []
                current_label, current_title = None, None
                for line in lines:
                    m = CLAUSE_RE.match(line)
                    if m:
                        if current_label and current_clause:
                            body = "\n".join(current_clause).strip()
                            enriched = f"Clause {current_label}: {current_title}\n\n{body}"
                            meta = {
                                "file_name": os.path.basename(pdf_path),
                                "clause_label": current_label,
                                "clause_title": current_title,
                            }
                            all_nodes.append(TextNode(text=enriched, metadata=meta))
                            current_clause = []
                        current_label = m.group("label")
                        current_title = m.group("title").strip(" -–:")
                    else:
                        current_clause.append(line)
                # final flush
                if current_label and current_clause:
                    body = "\n".join(current_clause).strip()
                    enriched = f"Clause {current_label}: {current_title}\n\n{body}"
                    meta = {
                        "file_name": os.path.basename(pdf_path),
                        "clause_label": current_label,
                        "clause_title": current_title,
                    }
                    all_nodes.append(TextNode(text=enriched, metadata=meta))

            index = VectorStoreIndex(all_nodes)
            index.storage_context.persist(persist_dir=persist_dir)
            print(f"✅ Built and persisted index with {len(all_nodes)} clause nodes")
        return index

    def _load_or_build_index(self):
        return self._cached_load_or_build_index(self.pdf_path, self.persist_dir, self.cache_version)

    def rebuild(self):
        """Force rebuild."""
        if os.path.exists(self.persist_dir):
            for root, _, files in os.walk(self.persist_dir, topdown=False):
                for f in files:
                    try: os.remove(os.path.join(root, f))
                    except: pass
                try: os.rmdir(root)
                except: pass
        st.cache_resource.clear()
        self.cache_version += 1
        self.index = self._load_or_build_index()
