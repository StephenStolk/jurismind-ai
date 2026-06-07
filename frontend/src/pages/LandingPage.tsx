import { useNavigate } from "react-router-dom"
import { Shield, Brain, Globe, Zap, FileText, Lock, ArrowRight, Sparkles, AlertCircle, AlertTriangle, Send } from "lucide-react"

const FEATURES = [
  { icon: Brain,       title: "Multi-Agent Loop",       desc: "5-node LangGraph pipeline with self-correction. Critic node eliminates hallucinations before you see the answer." },
  { icon: Shield,      title: "Risk Heatmap",           desc: "Every clause classified STANDARD · UNUSUAL · RISKY by a fine-tuned PyTorch model in real time." },
  { icon: Globe,       title: "Cross-Lingual RAG",      desc: "Ask in Hindi, retrieve from English legal corpus. MuRIL embeddings bridge the language gap seamlessly." },
  { icon: Zap,         title: "OCR + Scanned Docs",     desc: "Upload photos or scanned PDFs. Tesseract handles mixed Hindi/English text page by page." },
  { icon: Lock,        title: "Named Entity Extraction", desc: "Parties, dates, amounts, penalties extracted by a custom NER model trained on Indian legal text." },
  { icon: FileText,    title: "Plain-Language Summary", desc: "Dense legalese condensed into five bullet points any non-lawyer can understand, cached per document." },
]

const S: Record<string, React.CSSProperties> = {
  page:    { minHeight: "100vh", overflowX: "hidden", background: "#080b12", color: "#e8eaf0", fontFamily: '"DM Sans", system-ui, sans-serif' },
  maxW:    { maxWidth: 1100, margin: "0 auto", padding: "0 32px" },
  nav:     { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 32px", maxWidth: 1100, margin: "0 auto" },
}

export default function LandingPage() {
  const nav = useNavigate()

  return (
    <div style={S.page}>
      {/* Orbs */}
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0, overflow: "hidden" }}>
        <div style={{ position: "absolute", width: 500, height: 500, borderRadius: "50%", background: "radial-gradient(circle, rgba(45,212,191,0.08) 0%, transparent 70%)", top: -100, right: -100, filter: "blur(60px)" }} />
        <div style={{ position: "absolute", width: 400, height: 400, borderRadius: "50%", background: "radial-gradient(circle, rgba(99,102,241,0.06) 0%, transparent 70%)", bottom: 0, left: -80, filter: "blur(60px)" }} />
      </div>

      {/* Nav */}
      <nav style={S.nav}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "#2dd4bf", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Shield size={16} color="#000" />
          </div>
          <span style={{ fontWeight: 600, fontSize: 15, letterSpacing: "-0.01em" }}>JurisMind</span>
          <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "rgba(45,212,191,0.12)", color: "#2dd4bf", border: "1px solid rgba(45,212,191,0.2)", marginLeft: 2 }}>AI</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={() => nav("/signin")} style={{ background: "none", border: "none", color: "#8892a4", fontSize: 14, cursor: "pointer", padding: "8px 16px", borderRadius: 8, transition: "color 0.2s" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#e8eaf0")}
            onMouseLeave={e => (e.currentTarget.style.color = "#8892a4")}>
            Sign in
          </button>
          <button onClick={() => nav("/signup")} className="btn-teal" style={{ fontSize: 14, padding: "9px 20px" }}>
            Get started
          </button>
        </div>
      </nav>

      {/* ── HERO — left text, right mockup ── */}
      <section style={{ ...S.maxW, position: "relative", zIndex: 1, paddingTop: 72, paddingBottom: 100 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 64, alignItems: "center" }}>

          {/* Left */}
          <div className="animate-fade-up">
            <div style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "5px 14px", borderRadius: 99, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", fontSize: 12, color: "#8892a4", marginBottom: 28 }}>
              <Sparkles size={12} color="#2dd4bf" />
              LangGraph · MuRIL · PyTorch · RAG
            </div>

            <h1 style={{ fontSize: "clamp(2.2rem, 3.8vw, 3.4rem)", fontWeight: 300, lineHeight: 1.15, letterSpacing: "-0.03em", marginBottom: 20, color: "#e8eaf0" }}>
              Understand any<br />
              Indian{" "}
              <span className="serif" style={{ color: "#2dd4bf", fontStyle: "italic" }}>legal document</span>
              <br />
              in plain language.
            </h1>

            <p style={{ fontSize: 16, lineHeight: 1.7, color: "#8892a4", marginBottom: 36, maxWidth: 420 }}>
              Upload a rent agreement, loan paper, or property deed.
              Ask in Hindi or English. Get grounded, AI-verified answers — instantly.
            </p>

            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <button onClick={() => nav("/signup")} className="btn-teal" style={{ fontSize: 15, padding: "12px 24px", gap: 8 }}>
                Analyse a document free
                <ArrowRight size={16} />
              </button>
              <button onClick={() => nav("/signin")} style={{ background: "none", border: "1px solid rgba(255,255,255,0.1)", color: "#8892a4", fontSize: 15, padding: "12px 24px", borderRadius: 10, cursor: "pointer", transition: "all 0.2s" }}
                onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.04)"; e.currentTarget.style.color = "#e8eaf0" }}
                onMouseLeave={e => { e.currentTarget.style.background = "none"; e.currentTarget.style.color = "#8892a4" }}>
                Sign in
              </button>
            </div>

            {/* Trust line */}
            <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 40 }}>
              {[["9+", "Entity types extracted"], ["5-node", "Agent pipeline"], ["Hindi", "Native support"]].map(([val, lbl]) => (
                <div key={lbl}>
                  <div style={{ fontSize: 18, fontWeight: 600, color: "#2dd4bf", lineHeight: 1 }}>{val}</div>
                  <div style={{ fontSize: 11, color: "#4b5563", marginTop: 3 }}>{lbl}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right — App mockup */}
          <div className="animate-fade-up delay-300" style={{ position: "relative" }}>
            {/* Glow behind mockup */}
            <div style={{ position: "absolute", inset: -20, background: "radial-gradient(ellipse, rgba(45,212,191,0.07) 0%, transparent 70%)", borderRadius: 24, filter: "blur(20px)" }} />

            <div className="animate-float" style={{ position: "relative", borderRadius: 16, overflow: "hidden", background: "#0d1120", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 32px 80px rgba(0,0,0,0.6)" }}>
              {/* Titlebar */}
              <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "10px 14px", background: "#080b12", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: "rgba(248,113,113,0.6)" }} />
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: "rgba(251,191,36,0.6)" }} />
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: "rgba(52,211,153,0.6)" }} />
                <span style={{ fontSize: 11, color: "#4b5563", marginLeft: 8 }}>JurisMind — rent_agreement.pdf</span>
              </div>

              {/* App body */}
              <div style={{ display: "flex", height: 320 }}>
                {/* Sidebar */}
                <div style={{ width: 160, padding: 14, borderRight: "1px solid rgba(255,255,255,0.06)", display: "flex", flexDirection: "column", gap: 14 }}>
                  <div>
                    <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.12em", color: "#4b5563", marginBottom: 8 }}>Documents</div>
                    <div style={{ padding: "8px 10px", borderRadius: 8, background: "rgba(45,212,191,0.07)", border: "1px solid rgba(45,212,191,0.2)" }}>
                      <div style={{ fontSize: 11, color: "#e8eaf0", fontWeight: 500 }}>rent_agreement</div>
                      <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 4 }}>
                        <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#34d399" }} />
                        <span style={{ fontSize: 10, color: "#34d399" }}>ready</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ marginTop: "auto" }}>
                    <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.12em", color: "#4b5563", marginBottom: 8 }}>Risk Summary</div>
                    {[
                      { label: "Standard", count: 9, color: "#34d399", icon: Shield },
                      { label: "Unusual",  count: 3, color: "#fbbf24", icon: AlertTriangle },
                      { label: "Risky",    count: 2, color: "#f87171", icon: AlertCircle },
                    ].map((r) => (
                      <div key={r.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6, fontSize: 11 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 5, color: r.color }}>
                          <r.icon size={9} />
                          {r.label}
                        </div>
                        <span style={{ color: "#8892a4", fontWeight: 500 }}>{r.count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Chat area */}
                <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: 14, gap: 10 }}>
                  {/* User message */}
                  <div style={{ display: "flex", justifyContent: "flex-end" }}>
                    <div style={{ background: "rgba(45,212,191,0.1)", border: "1px solid rgba(45,212,191,0.2)", borderRadius: "12px 12px 3px 12px", padding: "8px 12px", fontSize: 12, color: "#e8eaf0", maxWidth: "80%", fontFamily: '"Noto Sans Devanagari", sans-serif' }}>
                      किरायेदार की जिम्मेदारियां क्या हैं?
                    </div>
                  </div>

                  {/* AI reply */}
                  <div style={{ display: "flex", justifyContent: "flex-start" }}>
                    <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "12px 12px 12px 3px", padding: "8px 12px", fontSize: 11.5, color: "#8892a4", maxWidth: "85%", lineHeight: 1.6, fontFamily: '"Noto Sans Devanagari", sans-serif' }}>
                      Clause 4.2 के अनुसार, किरायेदार समय पर किराया देगा, संपत्ति की देखभाल करेगा।
                    </div>
                  </div>

                  {/* Risky clause chip */}
                  <div style={{ background: "rgba(248,113,113,0.07)", border: "1px solid rgba(248,113,113,0.2)", borderLeft: "2px solid #f87171", borderRadius: 8, padding: "7px 10px" }}>
                    <div style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "#f87171", marginBottom: 3, fontWeight: 600 }}>⚠ Risky clause detected</div>
                    <div style={{ fontSize: 10.5, color: "#8892a4", lineHeight: 1.5 }}>Landlord may terminate without prior notice...</div>
                  </div>

                  {/* Input bar */}
                  <div style={{ marginTop: "auto", display: "flex", alignItems: "center", gap: 8, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 10, padding: "7px 10px" }}>
                    <span style={{ flex: 1, fontSize: 11, color: "#4b5563" }}>Ask about this document...</span>
                    <div style={{ width: 24, height: 24, borderRadius: 7, background: "#2dd4bf", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Send size={11} color="#000" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Divider ── */}
      <div style={{ ...S.maxW, borderTop: "1px solid rgba(255,255,255,0.05)", marginBottom: 80 }} />

      {/* ── Features ── */}
      <section style={{ ...S.maxW, position: "relative", zIndex: 1, paddingBottom: 100 }}>
        <div className="animate-fade-up" style={{ marginBottom: 48 }}>
          <p style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.18em", color: "#4b5563", marginBottom: 12 }}>Capabilities</p>
          <h2 style={{ fontSize: "clamp(1.6rem, 2.5vw, 2.2rem)", fontWeight: 300, letterSpacing: "-0.02em", color: "#e8eaf0" }}>
            Built with real{" "}
            <span className="serif" style={{ color: "#2dd4bf", fontStyle: "italic" }}>ML engineering</span>
          </h2>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          {FEATURES.map((f, i) => (
            <div key={i} className="animate-fade-up" style={{ animationDelay: `${i * 0.07}s`,
              padding: "22px 20px", borderRadius: 14, background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.06)",
              transition: "border-color 0.2s, background 0.2s", cursor: "default" }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(45,212,191,0.2)"; e.currentTarget.style.background = "rgba(45,212,191,0.03)" }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"; e.currentTarget.style.background = "rgba(255,255,255,0.025)" }}>
              <div style={{ width: 34, height: 34, borderRadius: 9, background: "rgba(45,212,191,0.1)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}>
                <f.icon size={16} color="#2dd4bf" />
              </div>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: "#e8eaf0", marginBottom: 8 }}>{f.title}</h3>
              <p style={{ fontSize: 12, color: "#8892a4", lineHeight: 1.65 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={{ ...S.maxW, position: "relative", zIndex: 1, paddingBottom: 100 }}>
        <div style={{ padding: "60px 48px", borderRadius: 20, background: "rgba(255,255,255,0.025)", border: "1px solid rgba(45,212,191,0.15)", position: "relative", overflow: "hidden" }}>
          <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at center, rgba(45,212,191,0.05) 0%, transparent 70%)", pointerEvents: "none" }} />
          <div style={{ position: "relative" }}>
            <p style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.18em", color: "#4b5563", marginBottom: 14 }}>Free to start</p>
            <h2 style={{ fontSize: "clamp(1.8rem, 3vw, 2.8rem)", fontWeight: 300, letterSpacing: "-0.02em", color: "#e8eaf0", marginBottom: 14 }}>
              Your document,{" "}
              <span className="serif" style={{ color: "#2dd4bf", fontStyle: "italic" }}>explained.</span>
            </h2>
            <p style={{ fontSize: 15, color: "#8892a4", marginBottom: 32, maxWidth: 440, lineHeight: 1.65 }}>
              No downloads. No lawyers required for a first read. Upload, ask, understand — in under 30 seconds.
            </p>
            <button onClick={() => nav("/signup")} className="btn-teal" style={{ fontSize: 15, padding: "12px 28px", gap: 8 }}>
              Start for free <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ ...S.maxW, borderTop: "1px solid rgba(255,255,255,0.05)", padding: "24px 32px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Shield size={14} color="#2dd4bf" />
          <span style={{ fontSize: 13, color: "#8892a4" }}>JurisMind AI</span>
        </div>
        <p style={{ fontSize: 12, color: "#4b5563" }}>© 2025 · Not a substitute for legal advice.</p>
      </footer>
    </div>
  )
}
