import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import fr from "./locales/fr/common.json";
import en from "./locales/en/common.json";
import ar from "./locales/ar/common.json";

// Langue initiale résolue de façon synchrone (avant le premier rendu) pour
// éviter un flash de français au chargement — LanguageContext prend ensuite
// le relais (préférence utilisateur connecté, avec priorité sur ce choix
// local dès que /auth/me répond, voir contexts/LanguageContext.jsx).
const SUPPORTED = ["fr", "en", "ar"];
function resolveInitialLang() {
  try {
    const stored = window.localStorage.getItem("lexia_lang");
    if (stored && SUPPORTED.includes(stored)) return stored;
  } catch {}
  return "fr";
}

i18n.use(initReactI18next).init({
  resources: { fr: { common: fr }, en: { common: en }, ar: { common: ar } },
  lng: resolveInitialLang(),
  fallbackLng: "fr",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});

export default i18n;
