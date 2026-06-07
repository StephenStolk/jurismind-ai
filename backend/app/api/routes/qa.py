import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.document import Document, DocumentStatus
from app.services.rag_pipeline import rag_pipeline
from app.services.llm_service import llm_service
from app.utils.response import success_response

router = APIRouter()


# ── Request schemas ───────────────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str
    doc_id: str
    language: str = "en"     # en | hi | mixed
    k: int = 6               # number of chunks to retrieve


class SummarizeRequest(BaseModel):
    doc_id: str
    language: str = "en"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_ready_document(doc_id: str, db: AsyncSession) -> Document:
    """Fetch document and verify it's ready for querying."""
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    result = await db.execute(select(Document).where(Document.id == uid))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"Document not ready. Current status: {doc.status}. "
                   f"Call POST /documents/{doc_id}/ingest first.",
        )

    return doc


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/ask")
async def ask_question(
    request: QuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a question about a specific document.
    Returns full answer (non-streaming).
    """
    doc = await _get_ready_document(request.doc_id, db)

    # Retrieve relevant chunks
    retrieved = rag_pipeline.retrieve(
        query=request.question,
        doc_id=request.doc_id,
        k=request.k,
    )

    if not retrieved:
        return success_response(
            message="No relevant context found in document.",
            data={"answer": "I couldn't find relevant information in this document for your question."},
        )

    # Generate answer
    answer = llm_service.answer_question(
        question=request.question,
        retrieved_docs=retrieved,
        language=request.language,
    )

    return success_response(
        message="Answer generated.",
        data={
            "answer": answer,
            "doc_id": request.doc_id,
            "chunks_used": len(retrieved),
            "question": request.question,
        },
    )


@router.post("/ask/stream")
async def ask_question_stream(
    request: QuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a question — streams the answer token by token via SSE.
    Frontend connects to this for real-time responses.
    """
    doc = await _get_ready_document(request.doc_id, db)

    retrieved = rag_pipeline.retrieve(
        query=request.question,
        doc_id=request.doc_id,
        k=request.k,
    )

    async def token_generator():
        if not retrieved:
            yield "data: No relevant context found.\n\n"
            return

        async for token in llm_service.answer_question_stream(
            question=request.question,
            retrieved_docs=retrieved,
            language=request.language,
        ):
            # SSE format — frontend EventSource reads this
            yield f"data: {token}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/summarize")
async def summarize_document(
    request: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a plain-language summary of the full document.
    Saves summary back to DB so it's not regenerated every time.
    """
    doc = await _get_ready_document(request.doc_id, db)

    # Return cached summary if exists
    cached = doc.summary_english if request.language == "en" else doc.summary_hindi
    if cached:
        return success_response(
            message="Summary retrieved from cache.",
            data={"summary": cached, "cached": True},
        )

    # Generate fresh summary
    summary = llm_service.summarize_document(
        document_text=doc.raw_text,
        language=request.language,
    )

    # Cache in DB
    if request.language == "en":
        doc.summary_english = summary
    else:
        doc.summary_hindi = summary
    await db.commit()

    return success_response(
        message="Summary generated.",
        data={"summary": summary, "cached": False},
    )