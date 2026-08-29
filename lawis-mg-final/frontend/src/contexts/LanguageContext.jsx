import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import i18n from "../i18n";
import { authService } from "../services/api";

const LanguageContext = createContext(null);
const SUPPORTED = ["fr", "en", "ar"];
const STORAGE_KEY = "lexia_lang";

function resolveStoredLang() {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED.includes(stored)) return stored;
  } catch {}
  return "fr";
}

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(resolveStoredLang);

  useEffect(() => {
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = lang;
  }, [lang]);

  // Choix explicite par l'utilisateur (sélecteur de langue) — persisté en
  // localStorage pour les visiteurs anonymes, et sur le profil serveur pour
  // les comptes connectés (réutilise PATCH /auth/me, déjà câblé pour
  // preferred_language — voir ProfilePage.jsx pour le même appel).
  const setLang = useCallback((newLang) => {
    if (!SUPPORTED.includes(newLang)) return;
    setLangState(newLang);
    i18n.changeLanguage(newLang);
    try { window.localStorage.setItem(STORAGE_KEY, newLang); } catch {}
    authService.updateProfile({ preferred_language: newLang }).catch(() => {});
  }, []);

  // Appliquée par AuthContext juste après la connexion : la préférence
  // enregistrée côté serveur l'emporte sur un choix anonyme local — pas de
  // ré-écriture serveur ici, on vient justement de la lire depuis /auth/me.
  const applyUserLanguage = useCallback((preferred) => {
    if (!preferred || !SUPPORTED.includes(preferred)) return;
    setLangState(preferred);
    i18n.changeLanguage(preferred);
    try { window.localStorage.setItem(STORAGE_KEY, preferred); } catch {}
  }, []);

  return (
    <LanguageContext.Provider value={{ lang, setLang, applyUserLanguage, supported: SUPPORTED }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
