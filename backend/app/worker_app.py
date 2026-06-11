import asyncio
import logging
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.services.document_processor import document_processor
from app.services.rag_pipeline import rag_pipeline
from app.services.llm_service import llm_service
from app.services.ml.ner_service import ner_service
from app.services.ml.clause_classifier import clause_classifier

logger = logging.getLogger(__name__)

# --- The Actual Processing Logic ---
async def process_document(doc_id: str):
    """Your existing document processing logic, ported from Celery."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        
        if not doc:
            return
            
        try:
            # Mark as processing
            doc.status = DocumentStatus.PROCESSING
            await db.commit()
            
            logger.info(f"[{doc_id}] Extracting text...")
            if not doc.raw_text:
                extraction = document_processor.extract_text(doc.file_path)
                doc.raw_text = extraction["text"]
                doc.language = document_processor.detect_language(doc.raw_text)
                await db.commit()
            
            # --- Insert your other stages here (RAG, NER, Classification, Summary) ---
            # ...
            # ...

            # Finalize
            doc.status = DocumentStatus.READY
            await db.commit()
            logger.info(f"[{doc_id}] Processing complete.")
            
        except Exception as e:
            logger.error(f"Error processing {doc_id}: {str(e)}")
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            await db.commit()


# --- The Polling Loop ---
async def poll_for_tasks():
    """Continuously checks the database for PENDING documents."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Find one pending document
                # Pro-tip: If you ever scale to multiple workers, use .with_for_update(skip_locked=True)
                result = await db.execute(
                    select(Document)
                    .where(Document.status == DocumentStatus.PENDING)
                    .limit(1)
                )
                doc = result.scalar_one_or_none()

                if doc:
                    logger.info(f"Found pending document: {doc.id}")
                    # Process it (awaits completion before pulling the next one)
                    await process_document(doc.id)
                else:
                    # No tasks found, sleep for a few seconds to prevent DB spam
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"Error in worker polling loop: {e}")
            await asyncio.sleep(5) # Backoff on error


# --- The "Dummy" FastAPI App for Render ---
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background polling task when the app starts
    task = asyncio.create_task(poll_for_tasks())
    yield
    # Cancel the task when the app shuts down
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health_check():
    """Render hits this to ensure the service is alive."""
    return {"status": "healthy", "service": "custom-worker"}