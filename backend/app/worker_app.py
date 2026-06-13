import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.services.document_processor import document_processor
from app.services.rag_pipeline import rag_pipeline
from app.services.llm_service import llm_service
from app.services.ml.ner_service import ner_service
from app.services.ml.clause_classifier import clause_classifier

# Setup clean basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("custom_worker")

async def process_document(doc_id: uuid.UUID):
    """Executes the core document processing pipeline stages sequentially."""
    logger.info(f"Starting pipeline sequence for doc_id: {doc_id}")
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        
        if not doc:
            logger.error(f"Document record {doc_id} not found in DB.")
            return
            
        try:
            # Stage 1: Mark processing and parse text
            doc.status = DocumentStatus.PROCESSING
            await db.commit()
            
            logger.info(f"[{doc_id}] Stage 1: Running text extraction/OCR")
            if not doc.raw_text:
                extraction = document_processor.extract_text(doc.file_path)
                doc.raw_text = extraction["text"]
                doc.language = document_processor.detect_language(doc.raw_text)
                await db.commit()
            
            # Stage 2: RAG Ingestion
            logger.info(f"[{doc_id}] Stage 2: RAG Pipeline ingestion")
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
            
            # Stage 2.5: Entity Extraction via Hugging Face API (Awaited!)
            logger.info(f"[{doc_id}] Stage 2.5: Querying Hugging Face API for NER entities")
            entities = await ner_service.extract_entities(doc.raw_text[:5000])
            doc.extracted_entities = entities
            await db.commit()
            
            # Stage 2.7: Clause Risk Classification (Sync)
            logger.info(f"[{doc_id}] Stage 2.7: Executing clause risk metrics")
            clause_risks = clause_classifier.classify_document(doc.raw_text[:8000])
            doc.clause_risks = clause_risks
            await db.commit()
            
            # Stage 3: Summarization (Sync)
            logger.info(f"[{doc_id}] Stage 3: Building LLM summary profile")
            summary = llm_service.summarize_document(
                document_text=doc.raw_text,
                language=doc.language,
            )
            if doc.language == "hi":
                doc.summary_hindi = summary
            else:
                doc.summary_english = summary
            
            # Pipeline absolute success
            doc.status = DocumentStatus.READY
            await db.commit()
            logger.info(f"[{doc_id}] Processing pipeline completed successfully.")
            
        except Exception as e:
            logger.error(f"Pipeline crashed on document {doc_id}. Error: {str(e)}")
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            await db.commit()

async def database_polling_loop():
    """An infinite polling loop that monitors PostgreSQL for PENDING work items."""
    logger.info("Database polling loop has started.")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Find the oldest pending job. (Use with_for_update(skip_locked=True) here if expanding workers)
                result = await db.execute(
                    select(Document)
                    .where(Document.status == DocumentStatus.PENDING)
                    .order_by(Document.created_at.asc())
                    .limit(1)
                )
                pending_doc = result.scalar_one_or_none()
                
                if pending_doc:
                    doc_to_process = pending_doc.id
                    logger.info(f"Found pending work asset: {doc_to_process}")
                    # Process the document sequentially to respect single-core thresholds
                    await process_document(doc_to_process)
                else:
                    # No active tasks found; sleep to save CPU execution loops
                    await asyncio.sleep(4)
                    
        except Exception as queue_err:
            logger.error(f"Exception encountered within DB loop cycle: {str(queue_err)}")
            await asyncio.sleep(5)

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    # Fire up the loop thread upon application boot
    polling_task = asyncio.create_task(database_polling_loop())
    yield
    # Safely terminate task hooks on container tear-downs
    polling_task.cancel()

# Minimal App wrapper to trick Render's web portal requirement
app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def worker_health_endpoint():
    return {"status": "operational", "engine": "custom-db-worker"}
