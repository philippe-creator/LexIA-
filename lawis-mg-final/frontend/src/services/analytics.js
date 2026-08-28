// Mesure d'audience (Google Analytics) — chargée UNIQUEMENT après consentement
// explicite (voir CookieBanner.jsx) : aucun script Google ne part avant que
// l'utilisateur ait cliqué "J'accepte". C'est le point qui rend ça conforme
// (RGPD / loi 09-08) — un simple bandeau qui n'empêche pas le tracking de
// démarrer en arrière-plan ne suffit pas.
const GA_ID = process.env.REACT_APP_GA_MEASUREMENT_ID;
const CONSENT_KEY = "lexia_cookie_consent"; // "accepted" | "refused"

export function getConsent() {
  try { return localStorage.getItem(CONSENT_KEY); } catch { return null; }
}

let gaLoaded = false;
export function loadGoogleAnalytics() {
  if (gaLoaded || !GA_ID) return;
  gaLoaded = true;
  const script = document.createElement("script");
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_ID}`;
  script.async = true;
  document.head.appendChild(script);
  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag() { window.dataLayer.push(arguments); };
  window.gtag("js", new Date());
  // anonymize_ip : conforme même pour les visiteurs qui acceptent, on ne
  // stocke pas l'IP complète chez Google.
  window.gtag("config", GA_ID, { anonymize_ip: true });
}

export function setConsent(value) {
  try { localStorage.setItem(CONSENT_KEY, value); } catch {}
  if (value === "accepted") loadGoogleAnalytics();
}

// Permet de revenir sur son choix (lien "Gérer mes préférences cookies" sur
// la page de politique de confidentialité) — redéclenche l'affichage du
// bandeau sans recharger la page.
export function resetConsent() {
  try { localStorage.removeItem(CONSENT_KEY); } catch {}
  window.dispatchEvent(new Event("cookie-consent-reset"));
}

export function trackPageview(path) {
  if (getConsent() === "accepted" && window.gtag) {
    window.gtag("event", "page_view", { page_path: path });
  }
}
