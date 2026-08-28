import React, { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { Scale, Eye, EyeOff, AlertCircle, CheckCircle } from "lucide-react";
import { authService, extractErrorMessage } from "../services/api";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault(); setError(null);
    if (password !== confirm) { setError("Les mots de passe ne correspondent pas."); return; }
    setLoading(true);
    try {
      await authService.resetPassword(token, password);
      setDone(true);
      setTimeout(() => navigate("/login"), 2500);
    } catch (err) { setError(extractErrorMessage(err)); }
    finally { setLoading(false); }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-icon"><Scale size={26}/></div>
          <div><h1 className="auth-title">LexIA Maroc</h1><p className="auth-subtitle">Nouveau mot de passe</p></div>
        </div>
        {!token && <div className="auth-error"><AlertCircle size={15}/><span>Lien invalide — aucun jeton de réinitialisation trouvé.</span></div>}
        {error && <div className="auth-error"><AlertCircle size={15}/><span>{error}</span></div>}
        {done ? (
          <div className="auth-notice"><CheckCircle size={15}/><span>Mot de passe réinitialisé. Redirection vers la connexion...</span></div>
        ) : (
          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label>Nouveau mot de passe *</label>
              <div className="input-password">
                <input type={showPwd?"text":"password"} value={password} onChange={(e)=>setPassword(e.target.value)} required minLength={8} className="form-input" placeholder="Minimum 8 caractères"/>
                <button type="button" className="pwd-toggle" onClick={() => setShowPwd(!showPwd)}>{showPwd?<EyeOff size={15}/>:<Eye size={15}/>}</button>
              </div>
            </div>
            <div className="form-group">
              <label>Confirmer le mot de passe *</label>
              <input type={showPwd?"text":"password"} value={confirm} onChange={(e)=>setConfirm(e.target.value)} required minLength={8} className="form-input" placeholder="Retapez le mot de passe"/>
            </div>
            <button type="submit" className="auth-submit" disabled={loading || !token}>{loading ? "..." : "Réinitialiser"}</button>
          </form>
        )}
        <p className="auth-footer-note"><Link to="/login">Retour à la connexion</Link></p>
      </div>
    </div>
  );
}
