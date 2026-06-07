import { create } from "zustand"
import type { UploadedDocument, ChatMessage, Language, ClauseRisk, RiskSummary } from "../types"

export interface User {
  id: string
  email: string
  name?: string
}

interface AppStore {
  user: User | null
  setUser: (u: User | null) => void

  activeDoc: UploadedDocument | null
  setActiveDoc: (doc: UploadedDocument | null) => void

  documents: UploadedDocument[]
  setDocuments: (docs: UploadedDocument[]) => void
  addDocument: (doc: UploadedDocument) => void
  updateDocument: (docId: string, updates: Partial<UploadedDocument>) => void

  messages: ChatMessage[]
  addMessage: (msg: ChatMessage) => void
  clearMessages: () => void

  language: Language
  setLanguage: (lang: Language) => void

  clauseRisks: ClauseRisk[]
  riskSummary: RiskSummary | null
  setRiskData: (risks: ClauseRisk[], summary: RiskSummary) => void

  isProcessing: boolean
  setIsProcessing: (val: boolean) => void
  agentStatus: string
  setAgentStatus: (status: string) => void
}

export const useAppStore = create<AppStore>((set) => ({
  user: null,
  setUser: (user) => set({ user }),

  activeDoc: null,
  setActiveDoc: (doc) => set({ activeDoc: doc, messages: [], clauseRisks: [], riskSummary: null }),

  documents: [],
  setDocuments: (docs) => set({ documents: docs }),
  addDocument: (doc) => set((s) => ({ documents: [doc, ...s.documents] })),
  updateDocument: (docId, updates) =>
    set((s) => ({
      documents: s.documents.map((d) => d.doc_id === docId ? { ...d, ...updates } : d),
      activeDoc: s.activeDoc?.doc_id === docId ? { ...s.activeDoc, ...updates } : s.activeDoc,
    })),

  messages: [],
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  clearMessages: () => set({ messages: [] }),

  language: "en",
  setLanguage: (language) => set({ language }),

  clauseRisks: [],
  riskSummary: null,
  setRiskData: (clauseRisks, riskSummary) => set({ clauseRisks, riskSummary }),

  isProcessing: false,
  setIsProcessing: (isProcessing) => set({ isProcessing }),
  agentStatus: "",
  setAgentStatus: (agentStatus) => set({ agentStatus }),
}))
