import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Scale, Eye, EyeOff, AlertCircle, CheckCircle } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useLanguage } from "../contexts/LanguageContext";
import { authService, extractErrorMessage } from "../services/api";
import LanguageSwitcher from "../components/LanguageSwitcher";

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

// Charge le script Google Identity Services une seule fois (partagé entre
// remontages du composant en React.StrictMode) et rend le bouton officiel
// Google dans le noeud fourni. Le widget Google n'accepte qu'une largeur en
// pixels (pas de %) — on la recalcule à partir du conteneur (qui, lui, est en
// %/flex et suit vraiment l'écran) à chaque montage et redimensionnement,
// pour éviter un bouton à largeur fixe qui déborde sur mobile.
function useGoogleSignInButton(containerRef, onCredential, locale) {
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !containerRef.current) return;
    let cancelled = false;
    let resizeTimer = null;
    const render = () => {
      if (cancelled || !window.google?.accounts?.id || !containerRef.current) return;
      window.google.accounts.id.initialize({ client_id: GOOGLE_CLIENT_ID, callback: (r) => onCredential(r.credential) });
      const available = containerRef.current.clientWidth || 360;
      const width = Math.round(Math.max(200, Math.min(400, available))); // bornes imposées par Google
      containerRef.current.innerHTML = "";
      window.google.accounts.id.renderButton(containerRef.current, { theme: "outline", size: "large", width, locale });
    };
    const handleResize = () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(render, 150);
    };
    const start = () => { render(); window.addEventListener("resize", handleResize); };
    let cleanupLoad = () => {};
    if (window.google?.accounts?.id) {
      start();
    } else {
      const existing = document.getElementById("google-gsi-script");
      if (existing) {
        existing.addEventListener("load", start);
        cleanupLoad = () => existing.removeEventListener("load", start);
      } else {
        const script = document.createElement("script");
        script.id = "google-gsi-script";
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.onload = start;
        document.body.appendChild(script);
      }
    }
    return () => { cancelled = true; clearTimeout(resizeTimer); window.removeEventListener("resize", handleResize); cleanupLoad(); };
  }, [containerRef, onCredential, locale]);
}

const ROLES = [
  { value:"particulier", emoji:"👤" },
  { value:"etudiant", emoji:"🎓" },
  { value:"juriste", emoji:"⚖️" },
  { value:"avocat", emoji:"🏛️" },
  { value:"entreprise", emoji:"🏢" },
];

export default function AuthPage() {
  const { t } = useTranslation();
  const [mode, setMode] = useState("login");
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [consent, setConsent] = useState(false);
  const [form, setForm] = useState({ email:"", password:"", username:"", full_name:"", role:"particulier" });
  const { login, register, loginWithGoogle } = useAuth();
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const googleBtnRef = useRef(null);

  const handleGoogleCredential = useCallback(async (idToken) => {
    setLoading(true); setError(null);
    try { await loginWithGoogle(idToken); navigate("/"); }
    catch (err) { setError(extractErrorMessage(err)); }
    finally { setLoading(false); }
  }, [loginWithGoogle, navigate]);
  useGoogleSignInButton(googleBtnRef, handleGoogleCredential, lang);

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
        <div className="auth-lang-row"><LanguageSwitcher /></div>
        <div className="auth-logo">
          <div className="auth-logo-icon"><Scale size={26}/></div>
          <div><h1 className="auth-title">{t("app.brand")}</h1><p className="auth-subtitle">{t("auth.tagline")}</p></div>
        </div>
        {mode !== "forgot" && (
          <div className="auth-tabs">
            {["login","register"].map((m) => (
              <button key={m} className={`auth-tab ${mode===m?"active":""}`} onClick={() => switchMode(m)}>
                {m==="login" ? t("auth.tabLogin") : t("auth.tabRegister")}
              </button>
            ))}
          </div>
        )}
        {error && (
          <div className="auth-error">
            <AlertCircle size={15}/><span>{error}</span>
            {mode === "login" && error.includes("non confirmée") && (
              <button type="button" className="auth-resend-link" onClick={handleResend} disabled={loading}>{t("auth.resendEmail")}</button>
            )}
          </div>
        )}
        {notice && <div className="auth-notice"><CheckCircle size={15}/><span>{notice}</span></div>}
        {mode !== "forgot" && GOOGLE_CLIENT_ID && (
          <>
            <div ref={googleBtnRef} className="google-signin-btn"/>
            <div className="auth-divider"><span>{t("auth.or")}</span></div>
          </>
        )}
        {mode === "forgot" ? (
          <form onSubmit={handleForgotSubmit} className="auth-form">
            <p className="form-hint">{t("auth.forgotHint")}</p>
            <div className="form-group"><label>{t("auth.email")}</label><input type="email" name="email" value={form.email} onChange={handleChange} required className="form-input" placeholder={t("auth.emailPlaceholder")}/></div>
            <button type="submit" className="auth-submit" disabled={loading}>{loading ? t("auth.loading") : t("auth.sendLink")}</button>
            <button type="button" className="auth-back-link" onClick={() => switchMode("login")}>{t("auth.backToLogin")}</button>
          </form>
        ) : (
        <form onSubmit={handleSubmit} className="auth-form">
          {mode==="register" && (
            <>
              <div className="form-group"><label>{t("auth.fullName")}</label><input name="full_name" value={form.full_name} onChange={handleChange} placeholder={t("auth.fullNamePlaceholder")} className="form-input"/></div>
              <div className="form-group"><label>{t("auth.username")}</label><input name="username" value={form.username} onChange={handleChange} required className="form-input" placeholder={t("auth.usernamePlaceholder")}/></div>
            </>
          )}
          <div className="form-group"><label>{t("auth.email")}</label><input type="email" name="email" value={form.email} onChange={handleChange} required className="form-input" placeholder={t("auth.emailPlaceholder")}/></div>
          <div className="form-group">
            <label>{t("auth.password")}</label>
            <div className="input-password">
              <input type={showPwd?"text":"password"} name="password" value={form.password} onChange={handleChange} required className="form-input" placeholder={t("auth.passwordPlaceholder")}/>
              <button type="button" className="pwd-toggle" onClick={() => setShowPwd(!showPwd)}>{showPwd?<EyeOff size={15}/>:<Eye size={15}/>}</button>
            </div>
          </div>
          {mode==="register" && (
            <div className="form-group">
              <label>{t("auth.role")}</label>
              <div className="role-grid">
                {ROLES.map((r) => (
                  <button key={r.value} type="button" className={`role-chip ${form.role===r.value?"active":""}`} onClick={() => setForm((p)=>({...p,role:r.value}))}>
                    <span className="role-emoji">{r.emoji}</span><span>{t(`role.${r.value}`)}</span>
                  </button>
                ))}
              </div>
              <p className="form-hint">{t("auth.roleHint")}</p>
            </div>
          )}
          {mode==="register" && (
            <label className="auth-consent">
              <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              <span>
                {t("auth.consentAccept")} <a href="/cgu" target="_blank" rel="noopener noreferrer">{t("auth.consentTerms")}</a> {t("auth.consentAnd")}{" "}
                <a href="/confidentialite" target="_blank" rel="noopener noreferrer">{t("auth.consentPrivacy")}</a>.
              </span>
            </label>
          )}
          {mode==="login" && (
            <button type="button" className="auth-back-link" onClick={() => switchMode("forgot")}>{t("auth.forgotPassword")}</button>
          )}
          <button type="submit" className="auth-submit" disabled={loading || (mode==="register" && !consent)}>
            {loading ? t("auth.loading") : mode==="login" ? t("auth.submitLogin") : t("auth.submitRegister")}
          </button>
        </form>
        )}
        <p className="auth-footer-note">{t("auth.footerNote")}</p>
      </div>
    </div>
  );
}
