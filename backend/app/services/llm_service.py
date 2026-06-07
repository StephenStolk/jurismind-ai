from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document as LCDocument
from typing import List, AsyncIterator

from app.core.config import settings

LEGAL_QA_PROMPT = ChatPromptTemplate.from_template(
    """
You are an expert Indian legal assistant. You help ordinary people understand 
legal documents written in English or Hindi.

CONTEXT FROM DOCUMENT:
{context}

USER QUESTION:
{question}

LANGUAGE INSTRUCTION:
{language_instruction}

RULES:
- Answer strictly based on the document context provided.
- If the answer is not in the context, say "This information is not found in the document."
- Identify specific clause numbers or section references when possible.
- Flag anything that seems unusual or potentially risky for the user.
- Never give a definitive legal opinion — always recommend consulting a lawyer for final decisions.

ANSWER:
"""
)

SUMMARY_PROMPT = ChatPromptTemplate.from_template("""
You are an expert Indian legal assistant. Summarize the following legal document 
in simple, plain language that a non-lawyer can understand.

DOCUMENT TEXT:
{document_text}

Provide the summary in {language}.

Structure your summary as:
1. Document Type
2. Parties Involved
3. Key Terms and Obligations
4. Important Dates or Deadlines
5. Any Clauses That Seem Unusual or Risky

SUMMARY:
""")

#LLM Service

class LLMService:
    """
    Wraps LangChain + OpenRouter LLM Calls.
    Handles QA, summarization, and streaming.
    """
    def __init__(self):
        # Standard LLM for non-streaming calls
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            temperature=0.1,       # low temp for factual legal responses
            max_tokens=1500,
        )
        
        # Streaming LLM — same config, streaming=True
        self.llm_streaming = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            temperature=0.1,
            max_tokens=1500,
            streaming=True,
        )
        
    def _format_context(self, docs: List[LCDocument]) -> str:
        """
        Format retrieved documents/chunks into a single context string. Preserves chunk order and adds chunk separators."""

        if not docs:
            return "No relevant information found."        
        parts = []
        for i, _doc in enumerate(docs):
            chunk_index = _doc.metadata.get("chunk_index", i)
            parts.append(f"[Chunk {chunk_index}]\n{_doc.page_content}")
            
        return "\n\n---\n\n".join(parts)
    
    def _language_instruction(self, language: str) -> str:
        if language == "hi":
            return "Respond in Hindi (Devanagari Script)."
        elif language == "mixed":
            return "Respond in simple Hindi mixed with English where needed (Hinglish is fine)."
        return "Respond in simple English."
    
    def answer_question(
        self,
        question: str,
        retrieved_docs: List[LCDocument],
        language: str = "en",
    ) -> str:
        """
        Single-shot QA — returns full answer as string.
        Use for non-streaming API calls.
        """
        context = self._format_context(retrieved_docs)
        lang_instruction = self._language_instruction(language)
        chain = LEGAL_QA_PROMPT | self.llm | StrOutputParser()
        
        return chain.invoke({
            "context": context,
            "question": question,
            "language_instruction": lang_instruction,
        })
    
    async def answer_question_stream(
        self,
        question: str,
        retrieved_docs: List[LCDocument],
        language: str = "en",
    ) -> AsyncIterator[str]:
        """
        Streaming QA — yields answer tokens one by one.
        Used for SSE streaming endpoint.
        """
        context = self._format_context(retrieved_docs)
        lang_instruction = self._language_instruction(language)
        chain = LEGAL_QA_PROMPT | self.llm_streaming | StrOutputParser()

        async for chunk in chain.astream({
            "context": context,
            "question": question,
            "language_instruction": lang_instruction,
        }):
            yield chunk
            
    def summarize_document(
        self,
        document_text: str,
        language: str = "en",
    ) -> str:
        """
        Generate a structured summary plain-language summary. Truncates to first 6000 chars to stay within context window.
        """
        lang_label = "Hindi" if language == "hi" else "English"
        
        truncated = document_text[:6000]
        if len(document_text) > 6000:
            truncated += "\n\n[Document truncated for summary...]"
            
        chain = SUMMARY_PROMPT | self.llm | StrOutputParser()
        
        return chain.invoke({
            "document_text": truncated,
            "language": lang_label,
        })
        
llm_service = LLMService()