import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Cookie } from "lucide-react";
import { getConsent, setConsent, loadGoogleAnalytics } from "../services/analytics";

export default function CookieBanner() {
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
        Nous utilisons des cookies de mesure d'audience (Google Analytics) pour comprendre l'usage du site.
        Rien n'est déposé sans votre accord. Voir la <Link to="/confidentialite">politique de confidentialité</Link>.
      </p>
      <div className="cookie-banner-actions">
        <button className="cookie-btn-refuse" onClick={() => choose("refused")}>Refuser</button>
        <button className="cookie-btn-accept" onClick={() => choose("accepted")}>J'accepte</button>
      </div>
    </div>
  );
}
