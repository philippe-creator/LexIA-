import React from "react";
import { useTranslation } from "react-i18next";
import { useLanguage } from "../contexts/LanguageContext";

/** Liste déroulante de langue, réutilisée partout (barre latérale, page de
 * connexion, landing page) — un seul contrôle de langue dans toute l'app,
 * plutôt qu'un réglage dupliqué par écran. */
export default function LanguageSwitcher({ variant = "light", className = "" }) {
  const { t } = useTranslation();
  const { lang, setLang, supported } = useLanguage();

  return (
    <select
      className={`language-switcher language-switcher-${variant} ${className}`}
      value={lang}
      onChange={(e) => setLang(e.target.value)}
      aria-label={t("language.fr") + " / " + t("language.en") + " / " + t("language.ar")}
    >
      {supported.map((code) => (
        <option key={code} value={code}>{t(`language.${code}`)}</option>
      ))}
    </select>
  );
}
