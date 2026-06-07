import axios from "axios"
import type {
  UploadedDocument,
  ClauseRisk,
  RiskSummary,
  AgentQueryResponse,
  Language,
} from "../types"

const api = axios.create({
  baseURL: "http://localhost:8000/api/v1",
  timeout: 60000,
})

// ── Documents ─────────────────────────────────────────────

export async function uploadDocument(file: File): Promise<{
  doc_id: string
  task_id: string
  original_filename: string
  status: string
}> {
  const form = new FormData()
  form.append("file", file)
  const res = await api.post("/documents/upload", form)
  return res.data.data
}

export async function getDocument(docId: string): Promise<UploadedDocument> {
  const res = await api.get(`/documents/${docId}`)
  return res.data.data
}

export async function listDocuments(): Promise<UploadedDocument[]> {
  const res = await api.get("/documents/")
  return res.data.data
}

export async function getTaskStatus(taskId: string): Promise<{
  state: string
  result: any
  error: string | null
}> {
  const res = await api.get(`/documents/task/${taskId}/status`)
  return res.data.data
}

export async function getClauseRisks(docId: string): Promise<{
  total_clauses: number
  summary: RiskSummary
  clauses: ClauseRisk[]
}> {
  const res = await api.get(`/documents/${docId}/risks`)
  return res.data.data
}

// ── Agent ─────────────────────────────────────────────────

export async function agentQuery(
  query: string,
  docId: string
): Promise<AgentQueryResponse> {
  const res = await api.post("/agent/query", { query, doc_id: docId })
  return res.data.data
}

export function createAgentStream(
  query: string,
  docId: string,
  onNode: (node: string, label: string) => void,
  onDone: (answer: string, confidence: number) => void
): () => void {
  // POST via fetch for SSE
  const controller = new AbortController()

  fetch("http://localhost:8000/api/v1/agent/query/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, doc_id: docId }),
    signal: controller.signal,
  }).then(async (res) => {
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value)
      const lines = text.split("\n")

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue
        const payload = line.slice(6).trim()
        if (payload === "[DONE]") break

        try {
          const data = JSON.parse(payload)
          if (data.node === "done") {
            onDone(data.final_answer, data.confidence_score)
          } else {
            onNode(data.node, data.label)
          }
        } catch {}
      }
    }
  }).catch((err) => {
    if (err.name !== "AbortError") console.error("Stream error:", err)
  })

  // Return cleanup function
  return () => controller.abort()
}

export async function summarizeDocument(
  docId: string,
  language: Language
): Promise<string> {
  const res = await api.post("/qa/summarize", {
    doc_id: docId,
    language,
  })
  return res.data.data.summary
}