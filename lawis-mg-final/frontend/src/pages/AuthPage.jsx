import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Scale, Eye, EyeOff, AlertCircle } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const ROLES = [
  { value:"particulier", label:"Particulier", emoji:"👤" },
  { value:"etudiant", label:"Étudiant", emoji:"🎓" },
  { value:"juriste", label:"Juriste", emoji:"⚖️" },
  { value:"avocat", label:"Avocat", emoji:"🏛️" },
  { value:"entreprise", label:"Entreprise", emoji:"🏢" },
];

export default function AuthPage() {
  const [mode, setMode] = useState("login");
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ email:"", password:"", username:"", full_name:"", role:"particulier" });
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => { setForm((p) => ({...p, [e.target.name]: e.target.value})); setError(null); };

  const handleSubmit = async (e) => {
    e.preventDefault(); setLoading(true); setError(null);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form);
      navigate("/");
    } catch (err) { setError(err.response?.data?.detail || "Une erreur s'est produite."); }
    finally { setLoading(false); }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-icon"><Scale size={26}/></div>
          <div><h1 className="auth-title">LexIA Maroc</h1><p className="auth-subtitle">Veille juridique intelligente</p></div>
        </div>
        <div className="auth-tabs">
          {["login","register"].map((m) => (
            <button key={m} className={`auth-tab ${mode===m?"active":""}`} onClick={() => { setMode(m); setError(null); }}>
              {m==="login" ? "Connexion" : "Inscription"}
            </button>
          ))}
        </div>
        {error && <div className="auth-error"><AlertCircle size={15}/><span>{error}</span></div>}
        <form onSubmit={handleSubmit} className="auth-form">
          {mode==="register" && (
            <>
              <div className="form-group"><label>Nom complet</label><input name="full_name" value={form.full_name} onChange={handleChange} placeholder="Prénom Nom" className="form-input"/></div>
              <div className="form-group"><label>Nom d'utilisateur *</label><input name="username" value={form.username} onChange={handleChange} required className="form-input" placeholder="utilisateur_123"/></div>
            </>
          )}
          <div className="form-group"><label>Email *</label><input type="email" name="email" value={form.email} onChange={handleChange} required className="form-input" placeholder="email@exemple.ma"/></div>
          <div className="form-group">
            <label>Mot de passe *</label>
            <div className="input-password">
              <input type={showPwd?"text":"password"} name="password" value={form.password} onChange={handleChange} required className="form-input" placeholder="Minimum 8 caractères"/>
              <button type="button" className="pwd-toggle" onClick={() => setShowPwd(!showPwd)}>{showPwd?<EyeOff size={15}/>:<Eye size={15}/>}</button>
            </div>
          </div>
          {mode==="register" && (
            <div className="form-group">
              <label>Profil *</label>
              <div className="role-grid">
                {ROLES.map((r) => (
                  <button key={r.value} type="button" className={`role-chip ${form.role===r.value?"active":""}`} onClick={() => setForm((p)=>({...p,role:r.value}))}>
                    <span className="role-emoji">{r.emoji}</span><span>{r.label}</span>
                  </button>
                ))}
              </div>
              <p className="form-hint">Votre profil adapte les réponses à votre niveau.</p>
            </div>
          )}
          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? "..." : mode==="login" ? "Se connecter" : "Créer mon compte"}
          </button>
        </form>
        <p className="auth-footer-note">Les réponses fournies sont informatives et ne constituent pas un avis juridique professionnel.</p>
      </div>
    </div>
  );
}
