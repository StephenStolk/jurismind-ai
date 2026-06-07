from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from agents.nodes import (
    classifier_node,
    retriever_node,
    analyst_node,
    critic_node,
    translator_node,
)

MAX_RETRIES = 2

def _retry_logic(state: AgentState) -> bool:
    """
    Conditional edge after critic node.
    If critic failed AND under retry limit → loop back to retriever.
    Otherwise → proceed to translator.
    """
    retry_count = state.get("retry_count",0)
    critic_passed = state.get("critic_passed", True)
    
    if not critic_passed and retry_count < MAX_RETRIES:
        #increment count and loop back
        state["retry_count"] = retry_count + 1
        return "retry"
    
    return "done"

def build_legal_agent() -> StateGraph:
    """
    Construct the LangGraph agent graph.

    Graph structure:
    classifier → retriever → analyst → critic → (retry loop | translator) → END
    """
    graph = StateGraph(AgentState)
    
    #Add Nodes
    graph.add_node("classifier", classifier_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("critic", critic_node)
    graph.add_node("translator", translator_node)
    
    #Linear edges
    graph.add_edge("classifier", "retriever")
    graph.add_edge("retriever", "analyst")
    graph.add_edge("analyst", "critic")
    
    #Conditional edge from critic
    graph.add_conditional_edges(
        "critic",
        _retry_logic,
        {
            "retry": "retriever",
            "done": "translator",
        },
    )
    
    graph.add_edge("translator", END)
    
    #Entry point
    graph.set_entry_point("classifier")
    
    return graph.compile()

legal_agent = build_legal_agent()