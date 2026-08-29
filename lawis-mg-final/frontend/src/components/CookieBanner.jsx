import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Cookie } from "lucide-react";
import { getConsent, setConsent, loadGoogleAnalytics } from "../services/analytics";

export default function CookieBanner() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const check = () => {
      const consent = getConsent();
      if (consent === "accepted") { loadGoogleAnalytics(); setVisible(false); }
      else if (consent === "refused") setVisible(false);
      else setVisible(true);
    };
    check();
    // Déclenché par le lien "Gérer mes préférences" de la page confidentialité.
    window.addEventListener("cookie-consent-reset", check);
    return () => window.removeEventListener("cookie-consent-reset", check);
  }, []);

  const choose = (value) => { setConsent(value); setVisible(false); };

  if (!visible) return null;
  return (
    <div className="cookie-banner">
      <Cookie size={20} className="cookie-banner-icon"/>
      <p>
        {t("cookieBanner.text")} <Link to="/confidentialite">{t("cookieBanner.privacyLink")}</Link>.
      </p>
      <div className="cookie-banner-actions">
        <button className="cookie-btn-refuse" onClick={() => choose("refused")}>{t("cookieBanner.refuse")}</button>
        <button className="cookie-btn-accept" onClick={() => choose("accepted")}>{t("cookieBanner.accept")}</button>
      </div>
    </div>
  );
}
