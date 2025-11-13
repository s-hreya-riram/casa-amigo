from llama_index.core import VectorStoreIndex
from llama_index.core.tools import FunctionTool
from utils.reminder_tool import notification_workflow_tool, ReminderInput
from utils.neighbourhood_research_tool import neighborhood_researcher
from utils.lease_tool import build_lease_qna_tool, LeaseQnAInput
from datetime import datetime
import threading

# ---- in-memory debug list if we want to show models debug logs --------------------------
_DEBUG_LOG: list[dict] = []

def debug_log(event: str, **kwargs):
    _DEBUG_LOG.append({"event": event, **kwargs})

def consume_debug_log() -> list[dict]:
    """UI can call this to read & clear the buffer each turn."""
    out = list(_DEBUG_LOG)
    _DEBUG_LOG.clear()
    return out

# ---- TODO tools to add ----------------------------------------------------
def date_calculator(): ...
def dimension_calculator(): ...
def personalised_recommendation(): ...


# ---- Tool registry ---------------------------------------------------------

def build_tools(index: VectorStoreIndex, similarity_top_k: int = 5, llm_client=None):
    """
    Build tools with shared LLM client for efficiency.
    
    Args:
        index: Vector store index for RAG
        similarity_top_k: Number of similar documents to retrieve
        llm_client: OpenAI client instance to share across tools
    """
    
    lease_qna_fn = build_lease_qna_tool(index, debug_log)

    # ----- tool 1: tenancy qna -------
    lease_qna = FunctionTool.from_defaults(
        fn=lease_qna_fn,
        name="lease_qna",
        description=("Use for any lease/contract question. Return an answer followed by "
                     "'Relevant excerpts' with exact clause labels and short verbatim quotes. "
                     "If dates/fees must be computed, call date_calculator after this."),
        fn_schema=LeaseQnAInput,
        return_direct=True, 
    )

    # ------- tool 2: neighbourhood amenity proximity questions ---------
    neighborhood_tool = FunctionTool.from_defaults(
        fn=neighborhood_researcher,
        name="neighborhood_researcher",
        description="Return walking distances to nearby asked for amenities. Input: any string address and string amentiy type.",
        return_direct=True,
    )

    # ---------- tool 3: reminder / notification tool ----------------
    from datetime import datetime
    now = datetime.now()
    iso = now.isoformat(timespec="seconds")
    year = now.year
    
    def reminder_tool_wrapper(input: ReminderInput | dict | None = None, **kwargs):
        """Wrapper that injects auth AND LLM client."""
        from utils.auth_store import get_auth_store
        
        # Get auth from global store
        auth = get_auth_store().get()
        print(f"[TOOL_WRAPPER] Auth from store: user_id={auth.get('user_id')}, has_token={bool(auth.get('token'))}")
        
        # Inject both auth and LLM client into kwargs
        kwargs['_injected_auth'] = auth
        # Don't pass llm_client if it's None to avoid issues
        if llm_client is not None:
            kwargs['llm_client'] = llm_client
        
        # Call with just input and kwargs
        return notification_workflow_tool(input, **kwargs)

    reminder_tool = FunctionTool.from_defaults(
        fn=reminder_tool_wrapper,
        name="notification_workflow_tool",
        description=(
            "Create and manage reminders related to tenancy milestones. "
            f"Current datetime (authoritative): {iso}. "
            f"Always resolve relative dates using this datetime. "
            f"Default year: {year}. Never use 2023 unless user said 2023."
            "Infer reminder_type_id based on the task: "
            "1=LOI, 2=Deposit, 3=Lease signing, 4=Rent (recurring), "
            "5=Renewal notice, 6=Move out. "
            "When creating a reminder, ALWAYS output `reminder_date` as a full ISO 8601 "
            "datetime string: 'YYYY-MM-DDTHH:MM:SS'. "
            "Use the user's current year by default (the present year), unless the user "
            "explicitly specifies another year. "
            "If the user says things like 'today', 'tomorrow', or gives only day+month "
            "like '31 Oct at 12:20pm', you MUST expand it to a full ISO datetime in the "
            "current year. "
            "For monthly rent reminders (type 4), prefer `recurring_rule` instead of `reminder_date`."
        ),
        fn_schema=ReminderInput,
        return_direct=True,
    )

    # TODO: tool to calculate notice periods / last dates / pro rata rents
    date_calc_tool = FunctionTool.from_defaults(
        fn=date_calculator,
        name="date_calculator",
        description=("Deterministic calculator for notice periods, last day, proration, late fees. "
                     "Inputs: ISO dates (YYYY-MM-DD), currency in SGD; use after lease_qna."),
    )

    # TODO: tool to spatially check if furniture can fit / maybe via images
    fit_tool = FunctionTool.from_defaults(
        fn=dimension_calculator,
        name="fit_checker",
        description=("Spatial check for furniture/door/room; returns pass/fail and limiting step."),
    )

    # TODO: tool to ask about user persona and recommend specific listings
    persona_tool = FunctionTool.from_defaults(
        fn=personalised_recommendation,
        name="persona_ranker",
        description=("Builds a user persona and scores candidate listings with an audit trail."),
    )

    return [lease_qna, neighborhood_tool, reminder_tool]