"""Document indexing and management for the Casa Amigo application."""

import os
import streamlit as st
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, load_index_from_storage

class DocumentIndexManager:
    """Manages document indexing and retrieval operations."""
    
    def __init__(self, data_dir: str = None, persist_dir: str = None):
        # Default paths relative to the project root
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "contracts")
        if persist_dir is None:
            persist_dir = os.path.join(os.path.dirname(__file__), "..", "..", "pdf_index")
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        self.index = self._load_or_build_index()
    
    @st.cache_resource
    def _cached_load_or_build_index(_self, data_dir: str, persist_dir: str):
        """Load existing index or build new one from documents."""
        if os.path.exists(persist_dir):
            storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
            index = load_index_from_storage(storage_context)
        else:
            documents = SimpleDirectoryReader(data_dir, required_exts=[".pdf"]).load_data()
            index = VectorStoreIndex.from_documents(documents)
            index.storage_context.persist(persist_dir=persist_dir)
        return index
    
    def _load_or_build_index(self):
        """Wrapper method to call cached function with instance parameters."""
        return self._cached_load_or_build_index(self.data_dir, self.persist_dir)
