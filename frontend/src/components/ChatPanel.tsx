import { useState, useRef, useEffect } from "react"
import { Send, Loader2, Brain, CheckCircle } from "lucide-react"
import { useAppStore } from "../store/appStore"
import { createAgentStream } from "../services/api"
import type { ChatMessage } from "../types"

const NODE_LABELS: Record<string, string> = {
  classifier: "Detecting language and intent...",
  retriever:  "Searching document...",
  analyst:    "Analysing legal context...",
  critic:     "Reviewing answer quality...",
  translator: "Preparing final response...",
}

const SUGGESTIONS = [
  "What are the key obligations in this document?",
  "Are there any risky clauses I should know about?",
  "किरायेदार की जिम्मेदारियां क्या हैं?",
]

export function ChatPanel() {
  const [input, setInput] = useState("")
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const cleanupRef = useRef<(() => void) | null>(null)
  const { activeDoc, messages, addMessage, language, agentStatus, setAgentStatus } = useAppStore()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, agentStatus])

  const sendMessage = async (text?: string) => {
    const query = (text || input).trim()
    if (!query || !activeDoc || streaming) return

    addMessage({ id: crypto.randomUUID(), role: "user", content: query, language, timestamp: new Date() })
    setInput("")
    setStreaming(true)
    setAgentStatus("Starting...")

    cleanupRef.current = createAgentStream(
      query, activeDoc.doc_id,
      (node) => setAgentStatus(NODE_LABELS[node] || node),
      (answer, confidence) => {
        addMessage({ id: crypto.randomUUID(), role: "assistant", content: answer, language, confidence_score: confidence, timestamp: new Date() })
        setStreaming(false)
        setAgentStatus("")
      }
    )
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 20px 8px", display: "flex", flexDirection: "column", gap: 16 }}>

        {messages.length === 0 && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16 }}>
            <div style={{ width: 48, height: 48, borderRadius: 12, background: "rgba(45,212,191,0.08)", border: "1px solid rgba(45,212,191,0.15)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Brain style={{ width: 22, height: 22, color: "var(--teal)" }} />
            </div>
            <div style={{ textAlign: "center" }}>
              <p style={{ fontSize: 14, fontWeight: 500, color: "var(--text-2)", marginBottom: 4 }}>Ask anything about this document</p>
              <p style={{ fontSize: 12, color: "var(--text-3)" }}>Hindi or English — both work</p>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", maxWidth: 340 }}>
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => sendMessage(s)}
                  style={{ textAlign: "left", padding: "10px 14px", borderRadius: 10, background: "var(--bg-3)", border: "1px solid var(--border)", fontSize: 12, color: "var(--text-2)", cursor: "pointer", transition: "all 0.15s", fontFamily: "inherit" }}
                  onMouseEnter={e => { (e.target as HTMLElement).style.borderColor = "rgba(45,212,191,0.3)"; (e.target as HTMLElement).style.color = "var(--text)" }}
                  onMouseLeave={e => { (e.target as HTMLElement).style.borderColor = "var(--border)"; (e.target as HTMLElement).style.color = "var(--text-2)" }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{
              maxWidth: "82%", borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
              padding: "10px 14px", fontSize: 13, lineHeight: 1.65,
              background: msg.role === "user" ? "rgba(45,212,191,0.12)" : "rgba(255,255,255,0.04)",
              border: msg.role === "user" ? "1px solid rgba(45,212,191,0.2)" : "1px solid var(--border)",
              color: "var(--text)",
              fontFamily: msg.language === "hi" ? '"Noto Sans Devanagari", sans-serif' : "inherit",
            }}>
              <p style={{ whiteSpace: "pre-wrap" }}>{msg.content}</p>
              {msg.confidence_score !== undefined && (
                <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 8, fontSize: 10, color: "var(--text-3)" }}>
                  <CheckCircle style={{ width: 10, height: 10, color: "var(--teal)" }} />
                  {Math.round(msg.confidence_score * 100)}% confidence
                </div>
              )}
            </div>
          </div>
        ))}

        {streaming && agentStatus && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-3)" }}>
            <Loader2 className="animate-spin" style={{ width: 12, height: 12, color: "var(--teal)" }} />
            {agentStatus}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)" }}>
        <div style={{ display: "flex", gap: 8 }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
            placeholder={language === "hi" ? "दस्तावेज़ के बारे में पूछें..." : "Ask about this document..."}
            disabled={!activeDoc || streaming}
            rows={2}
            style={{
              flex: 1, resize: "none", borderRadius: 12, padding: "10px 14px", fontSize: 13,
              background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)",
              color: "var(--text)", outline: "none", fontFamily: language === "hi" ? '"Noto Sans Devanagari", sans-serif' : '"DM Sans", sans-serif',
              transition: "border-color 0.2s",
            }}
            onFocus={e => (e.target.style.borderColor = "var(--teal)")}
            onBlur={e => (e.target.style.borderColor = "var(--border)")}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || !activeDoc || streaming}
            className="btn-teal"
            style={{ padding: "0 16px", borderRadius: 12, flexShrink: 0 }}
          >
            {streaming ? <Loader2 className="animate-spin" style={{ width: 16, height: 16 }} /> : <Send style={{ width: 16, height: 16 }} />}
          </button>
        </div>
      </div>
    </div>
  )
}
