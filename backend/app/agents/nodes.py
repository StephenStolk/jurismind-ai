from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document as LCDocument
from typing import List
import json
import re

from app.core.config import settings
from app.services.rag_pipeline import rag_pipeline
from app.agents.state import AgentState

# Shared LLM
def _get_llm(temperature: float = 0.1) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_BASE_URL,
        temperature=temperature,
        max_tokens=1500,
    )
    

# Node 1: Classifier

CLASSIFIER_PROMPT = ChatPromptTemplate.from_template("""
Analyze this user query about a legal document.

QUERY: {query}

Respond ONLY with valid JSON — no explanation, no markdown:
{{
  "detected_language": "en" | "hi" | "mixed",
  "query_intent": "question" | "summarize" | "risk_check" | "clause_lookup",
  "translated_query": "<English translation if query is Hindi, else same as query>",
  "reasoning": "<one line explaining your classification>"
}}
""")

def classifier_node(state: AgentState) -> dict:
    """
    Node 1: Detect language and intent of user query.
    Translates Hindi queries to English for cross-lingual retrieval.
    """
    
    llm = _get_llm(temperature=0.0)
    chain = CLASSIFIER_PROMPT | llm | StrOutputParser()
    
    raw = chain.invoke({"query": state["query"]})
    clean_raw = re.sub(r"```json|```", "", raw).strip()
    
    try:
        result = json.loads(clean_raw)
    except json.JSONDecodeError:
        result = {
            "detected_language": "en",
            "query_intent": "question",
            "translated_query": state["query"],
            "reasoning": "fallback classification",
        }
    
    return {
        "detected_language": result.get("detected_language", "en"),
        "query_intent": result.get("query_intent", "question"),
        "translated_query": result.get("translated_query", state["query"]),
    }
    

# Retriever

def retriever_node(state: AgentState) -> dict:
    """
    Node 2: Cross-lingual hybrid retrieval.
    Uses translated (English) query for retrieval even if user asked in Hindi.
    This is CLIR — Cross-Lingual Information Retrieval.
    """
    search_query = state.get("translated_query") or state["query"]
    
    retrieved = rag_pipeline.retrieve(
        query=search_query,
        doc_id=state["doc_id"],
        k=6,
        alpha=0.6,
    )
    
    retrieval_score = min(len(retrieved) / 6.0, 1.0)
    
    return {
        "retrieved_chunks": retrieved,
        "retrieval_score": retrieval_score,
    }
    

# Node 3: Legal Analyst

ANALYST_PROMPT = ChatPromptTemplate.from_template("""
You are a senior Indian legal analyst. Analyze the document context and answer 
the user's question accurately.

DOCUMENT CONTEXT:
{context}

USER QUESTION (original): {original_query}
USER QUESTION (English): {translated_query}
QUERY INTENT: {intent}

INSTRUCTIONS:
- Answer based ONLY on the provided context.
- Cite specific clause numbers or sections when found.
- For risk_check intent: explicitly list risky clauses with explanation.
- For clause_lookup intent: quote the exact clause text.
- If context is insufficient, clearly state what is missing.
- Be specific, not generic.

ANSWER:
""")

def analyst_node(state: AgentState) -> dict:
    """
    Node 3: Generate a detailed legal analysis answer.
    """ 
    
    llm = _get_llm(temperature=0.2)
    chain = ANALYST_PROMPT | llm | StrOutputParser()
    
    context_parts = []
    sources = []
    for i, doc in enumerate(state["retrieved_chunks"]):
        chunk_idx = doc.metadata.get("chunk_index", i)
        context_parts.append(f"[Clause/Section {chunk_idx}]\n{doc.page_content}")
        sources.append(f"chunk_{chunk_idx}")
        
    context = "\n\n---\n\n".join(context_parts) if context_parts else "No context retrieved."
    
    answer = chain.invoke({
        "context": context,
        "original_query": state["query"],
        "translated_query": state.get("translated_query", state["query"]),
        "intent": state.get("query_intent", "question"),
    })
    
    return {
        "draft_answer": answer,
        "sources": sources,
    }
    

# Node 4: Critic
CRITIC_PROMPT = ChatPromptTemplate.from_template("""
You are a strict legal QA critic. Evaluate this answer for quality and accuracy.

ORIGINAL QUESTION: {question}
DOCUMENT CONTEXT USED: {context_summary}
DRAFT ANSWER: {draft_answer}

Check for these problems:
1. Hallucination — claims facts not present in the context
2. Vagueness — generic answer not specific to this document
3. Missing citations — specific clauses exist but weren't referenced
4. Incomplete — question not fully answered

Respond ONLY with valid JSON:
{{
  "passed": true | false,
  "confidence_score": 0.0 to 1.0,
  "issues": ["issue1", "issue2"],
  "feedback": "<specific instruction for improvement if failed>"
}}
""")

def critic_node(state: AgentState) -> dict:
    """
    Node 4: Self-correction loop.
    Checks answer quality. If failed and under retry limit, loops back.
    """
    
    llm = _get_llm(temperature=0.0)
    chain = CRITIC_PROMPT | llm | StrOutputParser()
    
    # Summarize context for critic (avoid token overflow)
    context_summary = " | ".join([
        doc.page_content[:150] for doc in state["retrieved_chunks"][:3]
    ])
    
    raw = chain.invoke({
        "question": state["query"],
        "context_summary": context_summary,
        "draft_answer": state["draft_answer"],
    })
    clean = re.sub(r"```json|```", "", raw).strip()
    
    try:
        result = json.loads(clean)
    except json.JSONDecodeError:
        # If critic itself fails, pass through
        result = {
            "passed": True,
            "confidence_score": 0.7,
            "issues": [],
            "feedback": "",
        }
    
    return {
        "critic_passed": result.get("passed", True),
        "confidence_score": float(result.get("confidence_score", 0.7)),
        "critic_feedback": result.get("feedback", ""),
        "retry_count": state.get("retry_count", 0),
    }
    

# Node 5: Translator

TRANSLATOR_PROMPT = ChatPromptTemplate.from_template("""
Translate this legal analysis into {target_language}.

Keep legal terms accurate. Use simple vocabulary a non-lawyer can understand.
If the target language is Hindi, write in Devanagari script.
If Hinglish (mixed), blend Hindi and English naturally.

ANSWER TO TRANSLATE:
{answer}

TRANSLATED ANSWER:
""")

def translator_node(state: AgentState) -> dict:
    """
    Node 5: Translate final answer to user's detected language.
    Skips translation if already in target language.
    """
    detected_lang = state.get("detected_language", "en")
    draft = state["draft_answer"]
    
    # No translation needed if English
    if detected_lang == "en":
        return {"final_answer": draft}
    
    llm = _get_llm(temperature=0.1)
    chain = TRANSLATOR_PROMPT | llm | StrOutputParser()
    
    lang_label = {
        "hi": "Hindi (Devanagari script)",
        "mixed": "Hinglish (natural Hindi-English mix)",
    }.get(detected_lang, "English")
    
    translated = chain.invoke({
        "target_language": lang_label,
        "answer": draft,
    })
    
    return {"final_answer": translated}