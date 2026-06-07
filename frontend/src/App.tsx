import { useEffect, useState } from "react"
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom"
import { FileText, List, MessageSquare, Shield, Globe, LogOut, User, ChevronRight } from "lucide-react"
import { UploadZone } from "./components/UploadZone"
import { RiskHeatmap } from "./components/RiskHeatmap"
import { ChatPanel } from "./components/ChatPanel"
import { useAppStore } from "./store/appStore"
import { listDocuments } from "./services/api"
import { getSession, signOut } from "./services/supabase"
import LandingPage from "./pages/LandingPage"
import SignUpPage from "./pages/SignUpPage"
import SignInPage from "./pages/SignInPage"
import type { Language } from "./types"

const LANGUAGE_OPTIONS: { value: Language; label: string }[] = [
  { value: "en", label: "EN" },
  { value: "hi", label: "हिं" },
  { value: "mixed", label: "Mix" },
]

type Tab = "upload" | "risks" | "history"

function Dashboard() {
  const nav = useNavigate()
  const [tab, setTab] = useState<Tab>("upload")
  const { activeDoc, documents, setDocuments, setActiveDoc, language, setLanguage, user, setUser } = useAppStore()

  useEffect(() => { listDocuments().then(setDocuments).catch(() => {}) }, [])

  const handleSignOut = async () => { await signOut(); setUser(null); nav("/") }

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: "var(--bg)" }}>
      <header className="flex items-center justify-between px-5 py-3 shrink-0"
              style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-2)" }}>
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: "var(--teal)" }}>
            <Shield className="w-3.5 h-3.5 text-black" />
          </div>
          <span className="text-sm font-semibold tracking-tight" style={{ color: "var(--text)" }}>JurisMind</span>
          <span className="text-[10px] ml-1 px-1 py-0.5 rounded" style={{ color: "var(--teal)", background: "var(--teal-dim)" }}>AI</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-0.5 p-0.5 rounded-lg" style={{ background: "var(--bg-3)", border: "1px solid var(--border)" }}>
            <Globe className="w-3 h-3 ml-1.5" style={{ color: "var(--text-3)" }} />
            {LANGUAGE_OPTIONS.map((opt) => (
              <button key={opt.value} onClick={() => setLanguage(opt.value)}
                className="px-2.5 py-1 rounded-md text-[11px] font-medium transition-all"
                style={{ background: language === opt.value ? "var(--teal)" : "transparent", color: language === opt.value ? "#000" : "var(--text-2)" }}>
                {opt.label}
              </button>
            ))}
          </div>
          {user && (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg glass">
                <User className="w-3 h-3" style={{ color: "var(--text-3)" }} />
                <span className="text-[11px]" style={{ color: "var(--text-2)" }}>{user.name || user.email.split("@")[0]}</span>
              </div>
              <button onClick={handleSignOut} className="p-1.5 rounded-lg glass" title="Sign out">
                <LogOut className="w-3.5 h-3.5" style={{ color: "var(--text-3)" }} />
              </button>
            </div>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-72 shrink-0 flex flex-col overflow-hidden"
             style={{ borderRight: "1px solid var(--border)", background: "var(--bg-2)" }}>
          <div className="flex" style={{ borderBottom: "1px solid var(--border)" }}>
            {([
              { id: "upload" as Tab, icon: FileText, label: "Upload" },
              { id: "risks"  as Tab, icon: Shield,   label: "Risks"  },
              { id: "history" as Tab, icon: List,    label: "History" },
            ]).map((t) => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className="flex-1 flex items-center justify-center gap-1.5 py-3 text-[11px] font-medium transition-all border-b-2"
                style={{ borderColor: tab === t.id ? "var(--teal)" : "transparent", color: tab === t.id ? "var(--teal)" : "var(--text-3)" }}>
                <t.icon className="w-3 h-3" />{t.label}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {tab === "upload" && (
              <div className="flex flex-col gap-4">
                <UploadZone />
                {activeDoc && (
                  <div className="rounded-xl p-3.5 text-xs" style={{ background: "var(--bg-3)", border: "1px solid var(--border)" }}>
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="w-3 h-3 shrink-0" style={{ color: "var(--teal)" }} />
                      <p className="font-medium truncate" style={{ color: "var(--text)" }}>{activeDoc.original_filename}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium"
                            style={{ background: activeDoc.status === "ready" ? "rgba(52,211,153,0.1)" : "rgba(251,191,36,0.1)", color: activeDoc.status === "ready" ? "var(--green)" : "var(--amber)" }}>
                        {activeDoc.status}
                      </span>
                      <span style={{ color: "var(--text-3)" }}>{activeDoc.chunk_count} chunks · {activeDoc.language.toUpperCase()}</span>
                    </div>
                  </div>
                )}
              </div>
            )}
            {tab === "risks" && <RiskHeatmap />}
            {tab === "history" && (
              <div className="flex flex-col gap-2">
                {documents.length === 0 && (
                  <div className="flex flex-col items-center gap-3 py-12" style={{ color: "var(--text-3)" }}>
                    <FileText className="w-8 h-8 opacity-30" /><p className="text-xs">No documents yet</p>
                  </div>
                )}
                {documents.map((doc) => (
                  <button key={doc.doc_id} onClick={() => setActiveDoc(doc)}
                    className="text-left p-3 rounded-xl text-xs transition-all group"
                    style={{ background: activeDoc?.doc_id === doc.doc_id ? "rgba(45,212,191,0.08)" : "var(--bg-3)", border: activeDoc?.doc_id === doc.doc_id ? "1px solid rgba(45,212,191,0.25)" : "1px solid var(--border)" }}>
                    <div className="flex items-center gap-2">
                      <FileText className="w-3 h-3 shrink-0" style={{ color: "var(--text-3)" }} />
                      <p className="font-medium truncate flex-1" style={{ color: "var(--text)" }}>{doc.original_filename}</p>
                      <ChevronRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: "var(--text-3)" }} />
                    </div>
                    <div className="flex items-center gap-2 mt-1.5 ml-5">
                      <span className="px-1.5 py-0.5 rounded-md text-[10px]"
                            style={{ background: doc.status === "ready" ? "rgba(52,211,153,0.1)" : "rgba(251,191,36,0.1)", color: doc.status === "ready" ? "var(--green)" : "var(--amber)" }}>
                        {doc.status}
                      </span>
                      <span style={{ color: "var(--text-3)" }}>{doc.language}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          {activeDoc ? (
            <>
              <div className="px-5 py-3 flex items-center gap-3 shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
                <MessageSquare className="w-4 h-4" style={{ color: "var(--teal)" }} />
                <span className="text-sm truncate" style={{ color: "var(--text-2)" }}>{activeDoc.original_filename}</span>
                <span className="ml-auto px-2 py-0.5 rounded-full text-[10px] font-medium"
                      style={{ background: activeDoc.status === "ready" ? "rgba(52,211,153,0.1)" : "rgba(251,191,36,0.1)", color: activeDoc.status === "ready" ? "var(--green)" : "var(--amber)" }}>
                  {activeDoc.status}
                </span>
              </div>
              <ChatPanel />
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center gap-4">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: "var(--bg-3)", border: "1px solid var(--border)" }}>
                <Shield className="w-7 h-7" style={{ color: "var(--border-2)" }} />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium mb-1" style={{ color: "var(--text-2)" }}>No document selected</p>
                <p className="text-xs" style={{ color: "var(--text-3)" }}>Upload a document from the left panel to begin</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAppStore((s) => s.user)
  if (!user) return <Navigate to="/signin" replace />
  return <>{children}</>
}

function AppRoot() {
  const { user, setUser } = useAppStore()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    getSession().then(({ data }) => {
      if (data.session?.user) {
        setUser({ id: data.session.user.id, email: data.session.user.email!, name: data.session.user.user_metadata?.name })
      }
      setChecking(false)
    })
  }, [])

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg)" }}>
        <div className="w-5 h-5 border-2 rounded-full animate-spin" style={{ borderColor: "var(--border)", borderTopColor: "var(--teal)" }} />
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/signup" element={user ? <Navigate to="/dashboard" replace /> : <SignUpPage />} />
      <Route path="/signin" element={user ? <Navigate to="/dashboard" replace /> : <SignInPage />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return <BrowserRouter><AppRoot /></BrowserRouter>
}
