from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.core.database import get_db
from app.models.document import Document, DocumentStatus
from app.services.document_processor import document_processor
from app.utils.response import success_response, error_response
from app.services.ingestion_service import ingest_document_to_rag
from app.tasks.document_tasks import process_document_task
from app.core.celery_app import celery_app as celery
from app.services.ml.clause_classifier import clause_classifier

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a legal document.
    Saves file to disk, creates DB record, queues background processing.
    Returns immediately — processing happens async via Celery.
    """
    #file path, saved to disk
    file_path, unique_name, file_size = await document_processor.save_uploads(file)
    
    #DB record
    doc = Document(
        filename=unique_name,
        original_filename=file.filename,
        file_size=file_size,
        file_path=file_path,
        status=DocumentStatus.PENDING,
    )
    
    db.add(doc)
    await db.flush()
    
    doc_id = str(doc.id)
    await db.commit()
    
    task = process_document_task.delay(doc_id)
    
    return success_response(
        message="Document uploaded and text extracted successfully.",
        data={
            "doc_id": doc_id,
            "task_id": task.id,
            "original_filename": file.filename,
            "status": DocumentStatus.PENDING,
            "poll_url": f"/api/v1/documents/{doc_id}",
        },
    )
    
@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch document metadata and status by ID."""
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    result = await db.execute(select(Document).where(Document.id == uid))
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return success_response(
        message="Document found.",
        data={
            "doc_id": str(doc.id),
            "original_filename": doc.original_filename,
            "language": doc.language,
            "document_type": doc.document_type,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
            "has_summary": doc.summary_english is not None,
            "extracted_entities": doc.extracted_entities,
            "clause_risks": doc.clause_risks,
            "created_at": str(doc.created_at),
        },
    )
    
    
@router.get("/")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
):
    """List all uploaded documents."""
    result = await db.execute(
        select(Document)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    docs = result.scalars().all()
    
    return success_response(
        message=f"{len(docs)} documents found.",
        data=[
            {
                "doc_id": str(d.id),
                "original_filename": d.original_filename,
                "language": d.language,
                "document_type": d.document_type,
                "status": d.status,
                "created_at": str(d.created_at),
            }
            for d in docs
        ],
    )

@router.post("/{doc_id}/ingest")
async def ingest_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger RAG ingestion for an uploaded document.
    Call this after upload to make the document queryable.
    """
    result = await ingest_document_to_rag(doc_id, db)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return success_response(
        message="Document ingested into RAG pipeline successfully.",
        data=result,
    )
    
    
@router.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Check Celery task processing status.
    Frontend polls this after upload to show progress.
    """
    task = celery.AsyncResult(task_id)

    return success_response(
        message="Task status retrieved.",
        data={
            "task_id": task_id,
            "state": task.state,
            # PENDING | STARTED | SUCCESS | FAILURE | RETRY
            "result": task.result if task.state == "SUCCESS" else None,
            "error": str(task.info) if task.state == "FAILURE" else None,
        },
    )
    
@router.get("/{doc_id}/risks")
async def get_clause_risks(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Return clause risk analysis for a document.
    Powers the risk heatmap in the frontend.
    """
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    result = await db.execute(select(Document).where(Document.id == uid))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    risks = doc.clause_risks or []

    # Summary counts for the heatmap legend
    summary = {"STANDARD": 0, "UNUSUAL": 0, "RISKY": 0}
    for clause in risks:
        label = clause.get("label", "STANDARD")
        summary[label] = summary.get(label, 0) + 1
        
    return success_response(
        message="Clause risk analysis retrieved.",
        data={
            "doc_id": doc_id,
            "total_clauses": len(risks),
            "summary": summary,
            "clauses": risks,
        },
    )  
    
@router.get("/{doc_id}/entities")
async def get_entities(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Return extracted named entities grouped by type.
    Powers the entity panel in the frontend.
    """
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    result = await db.execute(select(Document).where(Document.id == uid))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    entities = doc.extracted_entities or []

    # Group by label for easy frontend consumption
    grouped: dict = {}
    for ent in entities:
        label = ent.get("label", "OTHER")
        if label not in grouped:
            grouped[label] = []
        text = ent.get("text", "")
        if text and text not in grouped[label]:
            grouped[label].append(text)

    return success_response(
        message="Entities retrieved.",
        data={
            "doc_id": doc_id,
            "total": len(entities),
            "entities": entities,
            "grouped": grouped,
        },
    )