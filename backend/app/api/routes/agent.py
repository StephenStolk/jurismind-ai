from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid
import json

from app.core.database import get_db
from app.models.document import Document, DocumentStatus
from app.agents.graph import legal_agent
from app.utils.response import success_response

router = APIRouter()

class AgentQueryRequest(BaseModel):
    doc_id: str
    query: str
    
@router.post("/query")
async def agent_query(
    request: AgentQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run the full LangGraph multi-agent pipeline.
    Classifier → Retriever → Analyst → Critic (loop) → Translator
    """
    
    #Validation
    try:
        uid = uuid.UUID(request.doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    
    result = await db.execute(select(Document).where(Document.id == uid))
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"Document not ready. Status: {doc.status}"
        )
        
    # Initial State
    initial_state: dict = {
        "query": request.query,
        "doc_id": request.doc_id,
        "raw_text": doc.raw_text[:3000] if doc.raw_text else "",
        "detected_language": "en",
        "query_intent": "question",
        "translated_query": request.query,
        "retrieved_chunks": [],
        "retrieval_score": 0.0,
        "draft_answer": "",
        "sources": [],
        "critic_passed": False,
        "critic_feedback": "",
        "retry_count": 0,
        "final_answer": "",
        "confidence_score": 0.0,
    }
    
    final_state = legal_agent.invoke(initial_state)
    return success_response(
        message="Agent query completed.",
        data={
            "query": request.query,
            "final_answer": final_state.get("final_answer", ""),
            "detected_language": final_state.get("detected_language"),
            "query_intent": final_state.get("query_intent"),
            "confidence_score": final_state.get("confidence_score"),
            "retry_count": final_state.get("retry_count", 0),
            "chunks_used": len(final_state.get("retrieved_chunks", [])),
            "sources": final_state.get("sources", []),
            "critic_passed": final_state.get("critic_passed"),
        },
    )
    
@router.post("/query/stream")
async def agent_query_stream(
    request: AgentQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Stream each agent node's progress as SSE events.
    Frontend can show: 'Classifying → Retrieving → Analysing → Reviewing...'
    """
    
    try:
        uid = uuid.UUID(request.doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    result = await db.execute(select(Document).where(Document.id == uid))
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status != DocumentStatus.READY:
        raise HTTPException(status_code=400, detail="Document not ready")
    
    initial_state: dict = {
        "query": request.query,
        "doc_id": request.doc_id,
        "raw_text": doc.raw_text[:3000] if doc.raw_text else "",
        "detected_language": "en",
        "query_intent": "question",
        "translated_query": request.query,
        "retrieved_chunks": [],
        "retrieval_score": 0.0,
        "draft_answer": "",
        "sources": [],
        "critic_passed": False,
        "critic_feedback": "",
        "retry_count": 0,
        "final_answer": "",
        "confidence_score": 0.0,
    }
    
    async def event_stream():
        # Stream node-by-node progress
        node_labels = {
            "classifier": "Detecting language and intent...",
            "retriever": "Searching document...",
            "analyst": "Analysing legal context...",
            "critic": "Reviewing answer quality...",
            "translator": "Preparing final response...",
        }
        
        async for event in legal_agent.astream(initial_state):
            for node_name, node_state in event.items():
                label = node_labels.get(node_name, node_name)
                payload = json.dumps({
                    "node": node_name,
                    "label": label,
                    "retry_count": node_state.get("retry_count", 0),
                })
                yield f"data: {payload}\n\n"

                # Stream final answer when translator completes
                if node_name == "translator":
                    final = json.dumps({
                        "node": "done",
                        "final_answer": node_state.get("final_answer", ""),
                        "confidence_score": node_state.get("confidence_score", 0),
                    })
                    yield f"data: {final}\n\n"

        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )            
                