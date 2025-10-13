"""
Casa Amigo — Agent wrapper
==========================

Role of this module
- Build a conversational agent using LlamaIndex AgentWorkflow.
- Inject a toolset (RAG lease QnA, date/fee calculators, neighbourhood reccomender, etc).
- Provide a simple sync `chat(message) -> str` API for the UI.
- Capture useful debug info for display in the app.

Design notes
- We bind a single CallbackManager (with a debug handler) at the LLM
  and at global Settings. This way, retrievers/query-engines created
  elsewhere (e.g., inside build_tools) still emit traces.
- We keep memory simple (token-limited buffer). 
"""

from dataclasses import dataclass
from typing import Optional

from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler

from utils.prompts import SYSTEM_ROUTING_PROMPT
from utils.tool_registry import build_tools
from utils.utils import run_sync, extract_text


@dataclass
class AgentConfig:
    """ The conversational agents configurations. """
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    memory_token_limit: int = 2000
    similarity_top_k: int = 5
    verbose: bool = True


class CasaAmigoAgent:
    """
    Wrapper around LlamaIndex AgentWorkflow.

    Public API:
      - chat(message: str) -> str
      - get_tool_calls() -> list[dict]      # for debug panel
      - get_trace_tree() -> str | None      # logtrace when required, if available
    """

    def __init__(self, index: VectorStoreIndex, api_key: str, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()

        # ---- Debug / tracing: one manager everywhere ------------------------
        # Prints a concise tree after each agent run (to stdout).
        self._debug_handler = LlamaDebugHandler(print_trace_on_end=True)
        self._cb_manager = CallbackManager([self._debug_handler])

        # Ensure retrievers/query engines created elsewhere inherit callbacks.
        Settings.callback_manager = self._cb_manager

        # ---- LLM -------------------------------------------------------------
        self.llm = OpenAI(
            model=self.config.model,
            api_key=api_key,
            temperature=self.config.temperature,
            callback_manager=self._cb_manager,  # OK across versions
        )

        # ---- Tools -----------------------------------------------------------
        self._tools = build_tools(index, similarity_top_k=self.config.similarity_top_k)

        # ---- AgentWorkflow ---------------------------------------------------
        self.workflow = AgentWorkflow.from_tools_or_functions(
            self._tools,
            llm=self.llm,
            verbose=self.config.verbose,
            system_prompt=SYSTEM_ROUTING_PROMPT,
        )

        # ---- Memory ----------------------------------------------------------
        self.memory = ChatMemoryBuffer.from_defaults(
            token_limit=self.config.memory_token_limit,
            llm=self.llm,
        )

        # ---- Debug buffers (for UI display) ---------------------------------
        self._last_tool_calls: list[dict] = []



    # ------------------------------ Public API -------------------------------

    def chat(self, message: str) -> str:
        """
        Run one chat turn through the agent and return plain text for the UI.
        Also records a short list of tool calls (name + args) for debugging.
        """

        # Run the async workflow with a robust sync helper
        out = run_sync(self.workflow, message, self.memory)

        # Captures tool calls for debug panel 
        self._last_tool_calls = []
        tool_calls = getattr(out, "tool_calls", None) or getattr(out, "tool_execs", None)
        if tool_calls:
            for i, tc in enumerate(tool_calls):
                name = getattr(tc, "tool_name", None) or getattr(tc, "name", None)
                args = getattr(tc, "input", None) or getattr(tc, "tool_input", None)
                self._last_tool_calls.append(
                    {"i": i, "name": str(name), "args": args if isinstance(args, dict) else str(args)}
                )
                print(f"[agent] tool_call[{i}] name={name} args={args}")
        else:
            print("[agent] no tool calls recorded")

        return extract_text(out)

    # ------------------------------ Debug helpers ----------------------------

    def get_tool_calls(self) -> list[dict]:
        """Return the last tool-call list (for Streamlit debug panel)."""
        return list(self._last_tool_calls)

    def get_trace_tree(self) -> Optional[str]:
        """Return a pretty trace tree if the debug handler provides one."""
        # Some versions expose .get_trace_tree(); fall back gracefully otherwise.
        getter = getattr(self._debug_handler, "get_trace_tree", None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                return None
        return None
