from typing import List
from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolMetadata
from llama_index.core import VectorStoreIndex


def date_calculator():
    pass

def dimension_calculator():
    pass

def notification_workflow():
    pass

def personalised_recommendation(): 
    pass

def neighbourhood_researcher():
    pass


def build_tools(index: VectorStoreIndex, similarity_top_k: int = 5):
    # RAG query engine as a first-class tool
    qe = index.as_query_engine(similarity_top_k=similarity_top_k, response_mode="compact")
    lease_qna = QueryEngineTool(
        query_engine=qe,
        metadata=ToolMetadata(
            name="lease_qna",
            description=("Use for any lease/contract question. Return an answer with clause citations. "
                         "If computation is needed (dates/fees), call date_calculator after retrieving the clause.")
        ),
    )

    date_calc_tool = FunctionTool.from_defaults(
        fn=date_calculator,
        name="date_calculator",
        description=("Deterministic calculator for notice periods, last day of tenancy, proration, late fees. "
                     "Inputs: ISO dates (YYYY-MM-DD), currency in SGD. Use after lease_qna reveals the rules.")
    )

    neighborhood_tool = FunctionTool.from_defaults(
        fn=neighbourhood_researcher,
        name="neighborhood_researcher",
        description=("External locality info: MRT/schools proximity, commute times, amenities, reviews. "
                     "Use for area/market questions, not contract terms.")
    )

    fit_tool = FunctionTool.from_defaults(
        fn=dimension_calculator,
        name="fit_checker",
        description=("Spatial check for furniture vs door/room. Dimensions in cm. "
                     "Returns pass/fail plus limiting step (door width, diagonal turn, corridor).")
    )

    workflow_tool = FunctionTool.from_defaults(
        fn=notification_workflow,
        name="workflow_helper",
        description=("Creates checklists, reminder schedules, viewing emails/notes. Use when the user asks to schedule/share/export.")
    )

    persona_tool = FunctionTool.from_defaults(
        fn=personalised_recommendation,
        name="persona_ranker",
        description=("Builds a persona profile (noise sensitivity, commute max, greenery preference, budget) "
                     "and scores candidate listings with an audit trail.")
    )

    return [lease_qna, date_calc_tool, neighborhood_tool, fit_tool, workflow_tool, persona_tool]
