import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { Scale, Eye, EyeOff, AlertCircle, CheckCircle } from "lucide-react";
import { authService, extractErrorMessage } from "../services/api";
import LanguageSwitcher from "../components/LanguageSwitcher";

export default function ResetPasswordPage() {
  const { t } = useTranslation();
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
    if (password !== confirm) { setError(t("resetPassword.mismatchError")); return; }
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
        <div className="auth-lang-row"><LanguageSwitcher /></div>
        <div className="auth-logo">
          <div className="auth-logo-icon"><Scale size={26}/></div>
          <div><h1 className="auth-title">LexIA Maroc</h1><p className="auth-subtitle">{t("resetPassword.subtitle")}</p></div>
        </div>
        {!token && <div className="auth-error"><AlertCircle size={15}/><span>{t("resetPassword.invalidLink")}</span></div>}
        {error && <div className="auth-error"><AlertCircle size={15}/><span>{error}</span></div>}
        {done ? (
          <div className="auth-notice"><CheckCircle size={15}/><span>{t("resetPassword.successMsg")}</span></div>
        ) : (
          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label>{t("resetPassword.newPassword")}</label>
              <div className="input-password">
                <input type={showPwd?"text":"password"} value={password} onChange={(e)=>setPassword(e.target.value)} required minLength={8} className="form-input" placeholder={t("auth.passwordPlaceholder")}/>
                <button type="button" className="pwd-toggle" onClick={() => setShowPwd(!showPwd)}>{showPwd?<EyeOff size={15}/>:<Eye size={15}/>}</button>
              </div>
            </div>
            <div className="form-group">
              <label>{t("resetPassword.confirmPassword")}</label>
              <input type={showPwd?"text":"password"} value={confirm} onChange={(e)=>setConfirm(e.target.value)} required minLength={8} className="form-input" placeholder={t("resetPassword.confirmPlaceholder")}/>
            </div>
            <button type="submit" className="auth-submit" disabled={loading || !token}>{loading ? t("auth.loading") : t("resetPassword.submit")}</button>
          </form>
        )}
        <p className="auth-footer-note"><Link to="/login">{t("auth.backToLogin")}</Link></p>
      </div>
    </div>
  );
}
