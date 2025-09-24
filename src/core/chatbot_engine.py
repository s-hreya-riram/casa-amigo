"""Chatbot engine for the Casa Amigo application."""

from llama_index.core import VectorStoreIndex
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.openai import OpenAI


class ChatbotEngine:
    """Handles chatbot functionality and LLM interactions."""
    
    def __init__(self, index: VectorStoreIndex, api_key: str):
        self.index = index
        self.api_key = api_key
        self.llm = OpenAI(model="gpt-4o-mini", api_key=api_key, temperature=0.1)
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=2000)
        self.chat_engine = self._create_chat_engine()
    
    def _create_chat_engine(self):
        """Create and configure the chat engine."""
        return self.index.as_chat_engine(
            chat_mode="condense_question",
            llm=self.llm,
            memory=self.memory,
            verbose=True
        )
    
    def get_response(self, query: str) -> str:
        """Get chatbot response for a given query."""
        response = self.chat_engine.chat(query)
        return response.response
