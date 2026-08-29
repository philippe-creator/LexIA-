import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams, Link } from "react-router-dom";
import { Scale, AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { authService, extractErrorMessage } from "../services/api";
import LanguageSwitcher from "../components/LanguageSwitcher";

export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [status, setStatus] = useState(token ? "loading" : "missing"); // loading | done | error | missing
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) return;
    authService.verifyEmail(token)
      .then((r) => { setStatus("done"); setMessage(r.data.message); })
      .catch((err) => { setStatus("error"); setMessage(extractErrorMessage(err)); });
  }, [token]);

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-lang-row"><LanguageSwitcher /></div>
        <div className="auth-logo">
          <div className="auth-logo-icon"><Scale size={26}/></div>
          <div><h1 className="auth-title">LexIA Maroc</h1><p className="auth-subtitle">{t("verifyEmail.subtitle")}</p></div>
        </div>
        {status === "missing" && <div className="auth-error"><AlertCircle size={15}/><span>{t("verifyEmail.invalidLink")}</span></div>}
        {status === "loading" && <div className="auth-notice"><Loader2 size={15} className="spin"/><span>{t("verifyEmail.loading")}</span></div>}
        {status === "done" && <div className="auth-notice"><CheckCircle size={15}/><span>{message}</span></div>}
        {status === "error" && <div className="auth-error"><AlertCircle size={15}/><span>{message}</span></div>}
        <p className="auth-footer-note"><Link to="/login">{t("verifyEmail.goToLogin")}</Link></p>
      </div>
    </div>
  );
}
