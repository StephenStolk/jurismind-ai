import { useEffect } from "react"
import { Shield, AlertTriangle, AlertCircle } from "lucide-react"
import { useAppStore } from "../store/appStore"
import { getClauseRisks } from "../services/api"
import type { RiskLabel } from "../types"

const RISK_CONFIG: Record<RiskLabel, { icon: any; color: string; bg: string; border: string; label: string }> = {
  STANDARD: { icon: Shield,        color: "#34d399", bg: "rgba(52,211,153,0.07)",  border: "#34d399", label: "Standard" },
  UNUSUAL:  { icon: AlertTriangle, color: "#fbbf24", bg: "rgba(251,191,36,0.07)",  border: "#fbbf24", label: "Unusual"  },
  RISKY:    { icon: AlertCircle,   color: "#f87171", bg: "rgba(248,113,113,0.07)", border: "#f87171", label: "Risky"    },
}

export function RiskHeatmap() {
  const { activeDoc, clauseRisks, riskSummary, setRiskData } = useAppStore()

  useEffect(() => {
    if (!activeDoc || activeDoc.status !== "ready") return
    getClauseRisks(activeDoc.doc_id).then((data) => setRiskData(data.clauses, data.summary))
  }, [activeDoc?.doc_id])

  if (!activeDoc || clauseRisks.length === 0) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, paddingTop: 48, color: "var(--text-3)" }}>
        <Shield style={{ width: 32, height: 32, opacity: 0.3 }} />
        <p style={{ fontSize: 12 }}>No risk data yet</p>
        <p style={{ fontSize: 11, textAlign: "center", lineHeight: 1.5 }}>Upload and process a document to see clause analysis</p>
      </div>
    )
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Summary */}
      {riskSummary && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {(Object.entries(RISK_CONFIG) as [RiskLabel, typeof RISK_CONFIG[RiskLabel]][]).map(([key, cfg]) => (
            <div key={key} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: cfg.color,
                                    background: cfg.bg, border: `1px solid ${cfg.color}30`, borderRadius: 6, padding: "3px 8px" }}>
              <cfg.icon style={{ width: 10, height: 10 }} />
              {riskSummary[key]} {cfg.label}
            </div>
          ))}
        </div>
      )}

      {/* Clauses */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 400, overflowY: "auto", paddingRight: 4 }}>
        {clauseRisks.map((clause) => {
          const cfg = RISK_CONFIG[clause.label as RiskLabel]
          return (
            <div key={clause.clause_index} style={{
              borderRadius: 10, padding: "10px 12px", fontSize: 12,
              background: cfg.bg, borderLeft: `2px solid ${cfg.border}`,
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ display: "flex", alignItems: "center", gap: 4, fontWeight: 600, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em", color: cfg.color }}>
                  <cfg.icon style={{ width: 10, height: 10 }} />
                  {clause.label}
                </span>
                <span style={{ fontSize: 10, color: "var(--text-3)" }}>{Math.round(clause.confidence * 100)}%</span>
              </div>
              <p style={{ color: "var(--text-2)", lineHeight: 1.6 }}>
                {clause.clause_text.slice(0, 200)}{clause.clause_text.length > 200 ? "..." : ""}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
