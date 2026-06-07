import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import { Shield, Eye, EyeOff, ArrowRight } from "lucide-react"
import { signUp } from "../services/supabase"
import { useAppStore } from "../store/appStore"

export default function SignUpPage() {
  const nav = useNavigate()
  const setUser = useAppStore((s) => s.setUser)
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password.length < 8) { setError("Password must be at least 8 characters."); return }
    setLoading(true); setError("")
    const { data, error: err } = await signUp(email, password, name)
    if (err) { setError(err.message); setLoading(false); return }
    if (data.user) {
      setUser({ id: data.user.id, email: data.user.email!, name })
      nav("/dashboard")
    } else {
      setError("Check your email for a confirmation link.")
      setLoading(false)
    }
  }

  const field = { background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 10, color: "#e8eaf0", fontFamily: '"DM Sans", sans-serif', fontSize: 14, outline: "none", width: "100%", padding: "11px 14px", transition: "border-color 0.2s, box-shadow 0.2s" }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", position: "relative", padding: "0 16px" }}>
      <div className="orb" style={{ width: 400, height: 400, background: "rgba(45,212,191,0.06)", top: -100, right: -100 }} />
      <div className="orb" style={{ width: 300, height: 300, background: "rgba(99,102,241,0.05)", bottom: -50, left: -50 }} />

      <div className="animate-fade-up" style={{ position: "relative", zIndex: 10, width: "100%", maxWidth: 360 }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center", marginBottom: 32 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "var(--teal)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Shield style={{ width: 16, height: 16, color: "#000" }} />
          </div>
          <span style={{ fontWeight: 600, fontSize: 15, color: "var(--text)" }}>JurisMind AI</span>
        </div>

        <div className="glass-strong" style={{ borderRadius: 20, padding: 32 }}>
          <h1 style={{ fontSize: 24, fontWeight: 300, letterSpacing: "-0.02em", color: "var(--text)", marginBottom: 6 }}>Create account</h1>
          <p style={{ fontSize: 13, color: "var(--text-2)", marginBottom: 28 }}>Start analysing legal documents for free.</p>

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {[
              { label: "Full name", type: "text", val: name, set: setName, ph: "Ramesh Kumar" },
              { label: "Email", type: "email", val: email, set: setEmail, ph: "you@example.com" },
            ].map((f) => (
              <div key={f.label}>
                <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-2)", marginBottom: 6 }}>{f.label}</label>
                <input className="input" type={f.type} placeholder={f.ph} value={f.val} onChange={(e) => f.set(e.target.value)} required />
              </div>
            ))}

            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-2)", marginBottom: 6 }}>Password</label>
              <div style={{ position: "relative" }}>
                <input className="input" type={showPass ? "text" : "password"} placeholder="Min. 8 characters" value={password} onChange={(e) => setPassword(e.target.value)} required style={{ ...field, paddingRight: 40 }} />
                <button type="button" onClick={() => setShowPass(!showPass)}
                  style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: "var(--text-3)", display: "flex" }}>
                  {showPass ? <EyeOff style={{ width: 16, height: 16 }} /> : <Eye style={{ width: 16, height: 16 }} />}
                </button>
              </div>
            </div>

            {error && (
              <div style={{ fontSize: 12, padding: "10px 12px", borderRadius: 8, color: "var(--red)", background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.2)" }}>
                {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-teal" style={{ padding: "13px 0", marginTop: 4, gap: 8, fontSize: 14 }}>
              {loading
                ? <div style={{ width: 16, height: 16, border: "2px solid rgba(0,0,0,0.3)", borderTopColor: "#000", borderRadius: "50%" }} className="animate-spin" />
                : <><span>Create account</span><ArrowRight style={{ width: 16, height: 16 }} /></>
              }
            </button>
          </form>

          <p style={{ textAlign: "center", fontSize: 12, marginTop: 20, color: "var(--text-3)" }}>
            Already have an account?{" "}
            <Link to="/signin" style={{ color: "var(--teal)", textDecoration: "underline", textUnderlineOffset: 2 }}>Sign in</Link>
          </p>
        </div>

        <p style={{ textAlign: "center", fontSize: 12, marginTop: 20 }}>
          <Link to="/" style={{ color: "var(--text-3)", textDecoration: "none" }}>← Back to home</Link>
        </p>
      </div>
    </div>
  )
}
