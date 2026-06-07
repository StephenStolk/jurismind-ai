import os
from typing import List

import numpy as np
# from langchain.schema import Document as LCDocument
from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from rank_bm25 import BM25Okapi

from app.core.config import settings

class LegalTextSplitter:
    """
    Legal-aware chunking.
    Avoids splitting mid-clause by using legal section markers as separators.
    Supports both Hindi and English legal markers.
    """
    
    SEPARATORS = [
        # English legal markers
        r"\nWHEREAS",
        r"\nNOW THEREFORE",
        r"\nIN WITNESS WHEREOF",
        r"\nARTICLE\s+[IVX\d]+",
        r"\nSECTION\s+\d+",
        r"\nCLAUSE\s+\d+",
        # Numbered clauses
        r"\n\s*\d+\.\s",
        r"\n\s*[a-z]\)\s",
        # Hindi legal markers
        r"\nखण्ड\s+\d+",
        r"\nधारा\s+\d+",
        r"\nअनुच्छेद\s+\d+",
        # Generic fallbacks
        "\n\n",
        "\n",
        " ",
    ]
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size = chunk_size,
            chunk_overlap = chunk_overlap,
            separators = self.SEPARATORS,
            is_separator_regex = True,
        )
        
    def split(self, text: str, metadata: dict = None) -> List[LCDocument]:
        docs = self.splitter.create_documents(
            [text],
            metadatas=[metadata or {}],
        )
        
        for i, doc in enumerate(docs):
            doc.metadata["chunk_index"] = i
            doc.metadata["total_chunks"] = len(docs)
            
        return docs
    
class RAGPipeline:
    """
    Full RAG pipeline:
    - Multilingual embeddings (Hindi + English via MiniLM multilingual)
    - ChromaDB for persistent vector storage
    - BM25 for sparse retrieval
    - Hybrid retrieval combining both with configurable alpha weighting
    """
    
    def __init__(self):
        self.splitter = LegalTextSplitter()
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        
        #BM25 state
        self._bm25: BM25Okapi | None = None
        self._bmi25_docs: List[LCDocument] = []
        
        #ChromaDB state
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        self._vectorstore = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=self.embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        
    
    #Ingestion
    def ingest(self, text: str, doc_id: str, metadata: dict = None) -> int:
        """
        Chunk → embed → store a document in ChromaDB.
        Also updates the in-memory BM25 index.
        Returns number of chunks stored.
        """
        
        base_meta = {"doc_id": doc_id, **(metadata or {})}
        chunks = self.splitter.split(text, metadata=base_meta)
        
        if not chunks:
            return 0
        
        self._vectorstore.add_documents(chunks)
        
        self._bmi25_docs.extend(chunks)
        self._rebuild_bm25()
        
        return len(chunks)
    
    def _rebuild_bm25(self):
        tokenized = [
            doc.page_content.lower().split() for doc in self._bmi25_docs
        ]
        self._bmi25 = BM25Okapi(tokenized)
        
    #Retrieval
    def retrieve(
        self,
        query: str,
        doc_id: str = None,
        k: int = 6, ##top 6 chunks (LLM Context window limitations; also more chunks, reduce quality)
        alpha: float = 0.6, #dense vs sparse wighting contolling
    ) -> List[LCDocument]:
        """
        Hybrid retrieval: dense semantic + sparse BM25.

        alpha: float between 0 and 1
            1.0 = pure dense (semantic only)
            0.0 = pure BM25 (keyword only)
            0.6 = default, good for legal text with specific terms
        """
        chroma_filter = {"doc_id": doc_id} if doc_id else None
        
        #Dense Retrieval
        dense_results = self._vectorstore.similarity_search_with_score(
            query,
            k=k*2,
            filter=chroma_filter,
        )
        
        if not dense_results:
            return []
        
          # If no BM25 index yet, return dense only
        if self._bm25 is None or not self._bm25_docs:
            return [doc for doc, _ in dense_results[:k]]
        
        # ── BM25 retrieval ──
        tokenized_query = query.lower().split()
        bm25_scores = self._bm25.get_scores(tokenized_query)
        
        # Normalize BM25 scores to [0, 1]
        bm25_max = bm25_scores.max()
        if bm25_max > 0:
            bm25_scores = bm25_scores / bm25_max
            
        # ── Combine scores ──
        # Dense scores from Chroma are distances (lower = better), convert to similarity
        combined: dict[str, dict] = {}

        for doc, dist in dense_results:
            key = doc.page_content[:120]   # use content prefix as key
            dense_sim = 1 - dist           # convert distance → similarity
            combined[key] = {"doc": doc, "score": alpha * dense_sim}

        for idx, doc in enumerate(self._bm25_docs):
            # Only consider chunks belonging to this doc if filter set
            if doc_id and doc.metadata.get("doc_id") != doc_id:
                continue
            key = doc.page_content[:120]
            sparse_score = (1 - alpha) * float(bm25_scores[idx])
            if key in combined:
                combined[key]["score"] += sparse_score
            else:
                combined[key] = {"doc": doc, "score": sparse_score}
                
         # Sort by combined score descending
        ranked = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
        return [item["doc"] for item in ranked[:k]]

    def get_collection_count(self) -> int:
        """Return total number of chunks stored in ChromaDB."""
        return self._vectorstore._collection.count()   
    
rag_pipeline = RAGPipeline()