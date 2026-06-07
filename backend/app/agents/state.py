from typing import TypedDict, List, Optional, Annotated
from langchain_core.documents import Document as LCDocument
import operator


class AgentState(TypedDict):
    # Input
    query: str
    doc_id: str
    raw_text: Optional[str]
    
    # Classifier
    detected_language: str
    query_intent: str           # question | summarize | risk_check | clause_lookup
    translated_query: Optional[str]
    
    # Retriever output
    retrieved_chunks: List[LCDocument] # chunks from hybrid search
    retrieval_score: float      # avg relevance score 0-1
    
    # Analyst output
    draft_answer: str           # first-pass answer
    sources: List[str]  
    
    # Critic output
    critic_passed: bool         # True = answer is good
    critic_feedback: str        # what was wrong if failed
    retry_count: int 
    
    # final answer
    final_answer: str
    confidence_score: float
    
    