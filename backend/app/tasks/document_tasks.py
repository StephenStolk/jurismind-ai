import asyncio
from celery import shared_task
from celery.utils.log import get_task_logger

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.services.document_processor import document_processor
from app.services.rag_pipeline import rag_pipeline
from app.services.llm_service import llm_service
from app.services.ml.ner_service import ner_service
from app.services.ml.clause_classifier import clause_classifier

from sqlalchemy import select
import uuid


logger = get_task_logger(__name__)


def _run_async(coro):
    """Helper to run async code inside a Celery sync task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="tasks.process_document",
)


def process_document_task(self, doc_id: str):
    """
    Full async document processing pipeline:
    1. Extract text (OCR if needed)
    2. Ingest into RAG (chunk + embed + store)
    3. Generate summary
    4. Update DB status throughout
    """
    logger.info(f"Starting processing for doc_id: {doc_id}")
    
    async def _process():
        async with AsyncSessionLocal() as db:
            # Fetch document
            uid = uuid.UUID(doc_id)
            result = await db.execute(
                select(Document).where(Document.id == uid)
            )
            doc = result.scalar_one_or_none()
            
            if not doc:
                logger.error(f"Document with ID {doc_id} not found.")
                return {"success": False, "error": "Document not found"}
            
            try:
                # Stage 1: OCR
                logger.info(f"[{doc_id}] Stage 1: Text extraction")
                doc.status = DocumentStatus.PROCESSING
                await db.commit()
                
                if not doc.raw_text:
                    extraction = document_processor.extract_text(doc.file_path)
                    doc.raw_text = extraction["text"]
                    doc.language = document_processor.detect_language(doc.raw_text)
                    await db.commit()
                    
                # Stage 2: RAG Ingestion
                logger.info(f"[{doc_id}] Stage 2: RAG ingestion")
                chunk_count = rag_pipeline.ingest(
                    text=doc.raw_text,
                    doc_id=str(doc.id),
                    metadata={
                        "filename": doc.original_filename,
                        "language": doc.language,
                        "document_type": str(doc.document_type),
                    },
                )
                
                doc.chunk_count = chunk_count
                doc.chroma_doc_id = str(doc.id)
                await db.commit()
                
                # NER extraction 
                logger.info(f"[{doc_id}] Stage 2.5: Entity extraction")
                entities = ner_service.extract_entities(doc.raw_text[:5000])
                doc.extracted_entities = entities
                await db.commit()
                
                # Clause risk classification
                logger.info(f"[{doc_id}] Stage 2.7: Clause risk classification")
                clause_risks = clause_classifier.classify_document(doc.raw_text[:8000])
                doc.clause_risks = clause_risks
                await db.commit()
                
                # Stage 3: Summarization
                logger.info(f"[{doc_id}] Stage 3: Summarization")
                summary = llm_service.summarize_document(
                    document_text=doc.raw_text,
                    language=doc.language,
                )
                
                if doc.language == "hi":
                    doc.summary_hindi = summary
                else:
                    doc.summary_english = summary
                await db.commit()
                
                # Finalize
                doc.status = DocumentStatus.READY
                await db.commit()
                
                logger.info(f"[{doc_id}] Processing complete. Chunks: {chunk_count}")
                return {
                    "success": True,
                    "doc_id": doc_id,
                    "chunk_count": chunk_count,
                }
                
            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {str(e)}")
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                await db.commit()
                
    try:
        return _run_async(_process())
    except Exception as exc:
        logger.error(f"Unexpected error in Celery task for doc_id {doc_id}: {exc}")
        raise self.retry(exc=exc)
    