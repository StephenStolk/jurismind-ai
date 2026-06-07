from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.models.document import Document, DocumentStatus
from app.services.rag_pipeline import rag_pipeline


async def ingest_document_to_rag(doc_id: str, db: AsyncSession) -> dict:
    """
    Fetch document from DB, ingest its text into RAG pipeline,
    update status to READY.
    """
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        return {"success": False, "error": "Invalid document ID"}

    # Fetch from DB
    result = await db.execute(select(Document).where(Document.id == uid))
    doc = result.scalar_one_or_none()

    if not doc:
        return {"success": False, "error": "Document not found"}

    if not doc.raw_text:
        return {"success": False, "error": "Document has no extracted text"}

    # Mark as processing
    doc.status = DocumentStatus.PROCESSING
    await db.commit()

    try:
        # Ingest into RAG
        chunk_count = rag_pipeline.ingest(
            text=doc.raw_text,
            doc_id=str(doc.id),
            metadata={
                "filename": doc.original_filename,
                "language": doc.language,
                "document_type": str(doc.document_type),
            },
        )

        # Update DB record
        doc.chunk_count = chunk_count
        doc.chroma_doc_id = str(doc.id)
        doc.status = DocumentStatus.READY
        await db.commit()

        return {
            "success": True,
            "doc_id": doc_id,
            "chunk_count": chunk_count,
        }

    except Exception as e:
        doc.status = DocumentStatus.FAILED
        doc.error_message = str(e)
        await db.commit()
        return {"success": False, "error": str(e)}