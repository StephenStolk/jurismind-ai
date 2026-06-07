import { useCallback, useState } from "react"
import { Upload, FileText, Loader2 } from "lucide-react"
import { uploadDocument, getDocument, getTaskStatus } from "../services/api"
import { useAppStore } from "../store/appStore"

export function UploadZone() {
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [statusText, setStatusText] = useState("")
  const { addDocument, setActiveDoc } = useAppStore()

  const processFile = useCallback(async (file: File) => {
    if (!file) return
    setUploading(true)
    setStatusText("Uploading...")
    try {
      const uploadRes = await uploadDocument(file)
      setStatusText("Processing document...")
      const poll = async (): Promise<void> => {
        const task = await getTaskStatus(uploadRes.task_id)
        if (task.state === "SUCCESS") {
          const doc = await getDocument(uploadRes.doc_id)
          addDocument(doc)
          setActiveDoc(doc)
          setStatusText("")
          setUploading(false)
        } else if (task.state === "FAILURE") {
          setStatusText("Processing failed.")
          setUploading(false)
        } else {
          setStatusText(`Processing... (${task.state})`)
          setTimeout(poll, 2000)
        }
      }
      await poll()
    } catch {
      setStatusText("Upload failed.")
      setUploading(false)
    }
  }, [addDocument, setActiveDoc])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) processFile(file)
  }, [processFile])

  return (
    <div
      onDrop={onDrop}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      style={{
        position: "relative",
        border: `2px dashed ${isDragging ? "var(--teal)" : "var(--border-2)"}`,
        borderRadius: 16,
        padding: "32px 20px",
        textAlign: "center",
        cursor: "pointer",
        background: isDragging ? "var(--teal-dim)" : "rgba(255,255,255,0.02)",
        transition: "all 0.2s",
      }}
    >
      <input
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) processFile(f) }}
        style={{ position: "absolute", inset: 0, opacity: 0, cursor: "pointer" }}
        disabled={uploading}
      />

      {uploading ? (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <Loader2 className="animate-spin" style={{ width: 28, height: 28, color: "var(--teal)" }} />
          <p style={{ fontSize: 12, color: "var(--text-2)" }}>{statusText}</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <div style={{ width: 48, height: 48, borderRadius: 12, background: "var(--teal-dim)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Upload style={{ width: 20, height: 20, color: "var(--teal)" }} />
          </div>
          <div>
            <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>Drop legal document here</p>
            <p style={{ fontSize: 11, color: "var(--text-3)", marginTop: 4 }}>PDF, PNG, JPG · Hindi or English</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
            <FileText style={{ width: 12, height: 12, color: "var(--text-3)" }} />
            <span style={{ fontSize: 11, color: "var(--text-3)" }}>Max {20}MB</span>
          </div>
        </div>
      )}
    </div>
  )
}
