import os
import streamlit as st
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
import re

CLAUSE_RE = re.compile(
    r"""(?imx)
    ^\s*(?:Clause\s*)?
    (?P<num>\d+(?:\.\d+)*(?:\([a-zA-Z]\))?)\s*[:.\-–]?\s*(?P<title>[A-Za-z][^\n]{0,80})
    """
)

def _docs_to_nodes_with_clause_meta(docs):
    splitter = SentenceSplitter(chunk_size=800, chunk_overlap=120)
    nodes = []
    for doc in docs:
        text = doc.text or ""
        last_num, last_title = None, None
        for chunk in splitter.split_text(text):
            m = CLAUSE_RE.search(chunk)
            if m:
                last_num = m.group("num")
                last_title = m.group("title").strip(" -–:")
            meta = {
                "file_name": doc.metadata.get("file_name"),
                "page_label": doc.metadata.get("page_label"),
            }
            if last_num or last_title:
                meta["clause_num"] = last_num
                meta["clause_title"] = last_title
            nodes.append(TextNode(text=chunk, metadata=meta))
    return nodes

class DocumentIndexManager:
    def __init__(self, data_dir: str = None, persist_dir: str = None, cache_version: int = 1):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "contracts")
        if persist_dir is None:
            persist_dir = os.path.join(os.path.dirname(__file__), "..", "..", "pdf_index")
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        self.cache_version = cache_version 

        self.index = self._load_or_build_index()

    @st.cache_resource
    def _cached_load_or_build_index(_self, data_dir: str, persist_dir: str, cache_version: int):
        """Load existing index or build new one from documents."""
        if os.path.exists(persist_dir):
            storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
            index = load_index_from_storage(storage_context)
        else:
            docs = SimpleDirectoryReader(
                data_dir,
                required_exts=[".pdf"],
                filename_as_id=True,
            ).load_data()
            nodes = _docs_to_nodes_with_clause_meta(docs)
            index = VectorStoreIndex(nodes)
            index.storage_context.persist(persist_dir=persist_dir)
        return index

    def _load_or_build_index(self):
        return self._cached_load_or_build_index(self.data_dir, self.persist_dir, self.cache_version)

    def rebuild(self):
        """Force a rebuild: delete persisted index and clear Streamlit cache."""
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
