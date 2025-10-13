"""
Functionality of chatbot

Bare minimum:
    1. Contract related FAQ with clause citations (3 sample questions for sanity check)

Extra features by tool:
    1. Calculator tool: for answering specifics about last dates / late fees
    2. Real-time recc tool: for answering questions about MRT / school proximity, weather/food, reviews
    3. Spatial reasoning tool: for calculating things like will my 200x40cm sofa fit against this wall
    4. Workflow tool: for scheduling emails, reminders for viewing, etc
    5. Personalisation tool: to create user persona / recommend properties based off of these / give a score to user

Extra features by agent:
    1. Audio / visual input supported
    2. Multilingual conversation supported

"""

from dataclasses import dataclass
from typing import Optional, List

from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import VectorStoreIndex

from utils.prompts import SYSTEM_ROUTING_PROMPT
from utils.tool_registry import build_tools
from utils.utils import run_sync, extract_text

@dataclass
class AgentConfig:
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    memory_token_limit: int = 2000
    similarity_top_k: int = 5
    verbose: bool = True

class CasaAmigoAgent:
    def __init__(self, index: VectorStoreIndex, api_key: str, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.llm = OpenAI(model=self.config.model, api_key=api_key, temperature=self.config.temperature)

        tools = build_tools(index, similarity_top_k=self.config.similarity_top_k)
        self.workflow = AgentWorkflow.from_tools_or_functions(
            tools,
            llm=self.llm,
            verbose=self.config.verbose,
            system_prompt=SYSTEM_ROUTING_PROMPT,
        )

        self.memory = ChatMemoryBuffer.from_defaults(token_limit=self.config.memory_token_limit, llm=self.llm)

    # Public chat API
    def chat(self, message: str) -> str:
        out = run_sync(self.workflow, message, self.memory)
        return extract_text(out)

