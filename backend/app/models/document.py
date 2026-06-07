import uuid
import enum
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    RENT_AGREEMENT = "rent_agreement"
    LOAN_DOCUMENT = "loan_document"
    EMPLOYMENT_CONTRACT = "employment_contract"
    PROPERTY_DEED = "property_deed"
    FIR = "fir"
    AFFIDAVIT = "affidavit"
    UNKNOWN = "unknown"


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)

    # Extracted content
    raw_text = Column(Text, nullable=True)
    language = Column(String(10), default="en")   # hi | en | mixed

    # ML-derived fields
    document_type = Column(Enum(DocumentType), default=DocumentType.UNKNOWN)
    extracted_entities = Column(JSON, default=dict)  # NER output
    clause_risks = Column(JSON, default=list)         # Risk classifier
    summary_hindi = Column(Text, nullable=True)
    summary_english = Column(Text, nullable=True)

    # ChromaDB reference
    chroma_doc_id = Column(String(255), nullable=True)
    chunk_count = Column(Integer, default=0)

    # Processing status
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Document {self.id} | {self.document_type} | {self.status}>"