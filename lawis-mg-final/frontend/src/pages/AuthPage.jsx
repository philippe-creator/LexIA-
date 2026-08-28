import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Scale, Eye, EyeOff, AlertCircle, CheckCircle } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { authService, extractErrorMessage } from "../services/api";

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

// Charge le script Google Identity Services une seule fois (partagé entre
// remontages du composant en React.StrictMode) et rend le bouton officiel
// Google dans le noeud fourni.
function useGoogleSignInButton(containerRef, onCredential) {
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !containerRef.current) return;
    let cancelled = false;
    const render = () => {
      if (cancelled || !window.google?.accounts?.id || !containerRef.current) return;
      window.google.accounts.id.initialize({ client_id: GOOGLE_CLIENT_ID, callback: (r) => onCredential(r.credential) });
      window.google.accounts.id.renderButton(containerRef.current, { theme: "outline", size: "large", width: 360, locale: "fr" });
    };
    if (window.google?.accounts?.id) { render(); return; }
    const existing = document.getElementById("google-gsi-script");
    if (existing) { existing.addEventListener("load", render); return () => existing.removeEventListener("load", render); }
    const script = document.createElement("script");
    script.id = "google-gsi-script";
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = render;
    document.body.appendChild(script);
    return () => { cancelled = true; };
  }, [containerRef, onCredential]);
}

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
  const [notice, setNotice] = useState(null);
  const [consent, setConsent] = useState(false);
  const [form, setForm] = useState({ email:"", password:"", username:"", full_name:"", role:"particulier" });
  const { login, register, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const googleBtnRef = useRef(null);

  const handleGoogleCredential = useCallback(async (idToken) => {
    setLoading(true); setError(null);
    try { await loginWithGoogle(idToken); navigate("/"); }
    catch (err) { setError(extractErrorMessage(err)); }
    finally { setLoading(false); }
  }, [loginWithGoogle, navigate]);
  useGoogleSignInButton(googleBtnRef, handleGoogleCredential);

  const handleChange = (e) => { setForm((p) => ({...p, [e.target.name]: e.target.value})); setError(null); };

  const switchMode = (m) => { setMode(m); setError(null); setNotice(null); };

  const handleForgotSubmit = async (e) => {
    e.preventDefault(); setLoading(true); setError(null); setNotice(null);
    try {
      const r = await authService.forgotPassword(form.email);
      setNotice(r.data.message);
    } catch (err) { setError(extractErrorMessage(err)); }
    finally { setLoading(false); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault(); setLoading(true); setError(null); setNotice(null);
    try {
      if (mode === "login") { await login(form.email, form.password); navigate("/"); }
      else {
        // /auth/register ne connecte plus automatiquement : le compte doit
        // être confirmé par email avant la première connexion.
        const data = await register(form);
        setMode("login");
        setNotice(data.message);
      }
    } catch (err) { setError(extractErrorMessage(err)); }
    finally { setLoading(false); }
  };

  const handleResend = async () => {
    setLoading(true); setError(null);
    try {
      const r = await authService.resendVerification(form.email);
      setNotice(r.data.message);
    } catch (err) { setError(extractErrorMessage(err)); }
    finally { setLoading(false); }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-icon"><Scale size={26}/></div>
          <div><h1 className="auth-title">LexIA Maroc</h1><p className="auth-subtitle">Veille juridique intelligente</p></div>
        </div>
        {mode !== "forgot" && (
          <div className="auth-tabs">
            {["login","register"].map((m) => (
              <button key={m} className={`auth-tab ${mode===m?"active":""}`} onClick={() => switchMode(m)}>
                {m==="login" ? "Connexion" : "Inscription"}
              </button>
            ))}
          </div>
        )}
        {error && (
          <div className="auth-error">
            <AlertCircle size={15}/><span>{error}</span>
            {mode === "login" && error.includes("non confirmée") && (
              <button type="button" className="auth-resend-link" onClick={handleResend} disabled={loading}>Renvoyer l'email</button>
            )}
          </div>
        )}
        {notice && <div className="auth-notice"><CheckCircle size={15}/><span>{notice}</span></div>}
        {mode !== "forgot" && GOOGLE_CLIENT_ID && (
          <>
            <div ref={googleBtnRef} className="google-signin-btn"/>
            <div className="auth-divider"><span>ou</span></div>
          </>
        )}
        {mode === "forgot" ? (
          <form onSubmit={handleForgotSubmit} className="auth-form">
            <p className="form-hint">Indiquez votre email : si un compte existe, un lien de réinitialisation vous sera envoyé.</p>
            <div className="form-group"><label>Email *</label><input type="email" name="email" value={form.email} onChange={handleChange} required className="form-input" placeholder="email@exemple.ma"/></div>
            <button type="submit" className="auth-submit" disabled={loading}>{loading ? "..." : "Envoyer le lien"}</button>
            <button type="button" className="auth-back-link" onClick={() => switchMode("login")}>Retour à la connexion</button>
          </form>
        ) : (
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
          {mode==="register" && (
            <label className="auth-consent">
              <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              <span>
                J'accepte les <a href="/cgu" target="_blank" rel="noopener noreferrer">CGU</a> et la{" "}
                <a href="/confidentialite" target="_blank" rel="noopener noreferrer">politique de confidentialité</a>.
              </span>
            </label>
          )}
          {mode==="login" && (
            <button type="button" className="auth-back-link" onClick={() => switchMode("forgot")}>Mot de passe oublié ?</button>
          )}
          <button type="submit" className="auth-submit" disabled={loading || (mode==="register" && !consent)}>
            {loading ? "..." : mode==="login" ? "Se connecter" : "Créer mon compte"}
          </button>
        </form>
        )}
        <p className="auth-footer-note">Les réponses fournies sont informatives et ne constituent pas un avis juridique professionnel.</p>
      </div>
    </div>
  );
}
