export type Language = "en" | "hi" | "mixed"

export type DocumentStatus = "pending" | "processing" | "ready" | "failed"

export type RiskLabel = "STANDARD" | "UNUSUAL" | "RISKY"

export interface UploadedDocument {
  doc_id: string
  original_filename: string
  language: Language
  document_type: string
  status: DocumentStatus
  chunk_count: number
  created_at: string
}

export interface ClauseRisk {
  clause_index: number
  clause_text: string
  label: RiskLabel
  confidence: number
  color: string
}

export interface RiskSummary {
  STANDARD: number
  UNUSUAL: number
  RISKY: number
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  language: Language
  confidence_score?: number
  retry_count?: number
  timestamp: Date
}

export interface AgentQueryResponse {
  final_answer: string
  detected_language: Language
  query_intent: string
  confidence_score: number
  retry_count: number
  chunks_used: number
  critic_passed: boolean
}