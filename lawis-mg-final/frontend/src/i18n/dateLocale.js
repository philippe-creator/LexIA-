// Locale à utiliser avec Date.prototype.toLocaleString()/toLocaleDateString()
// selon la langue de l'interface — évite de disperser ce mapping dans chaque
// composant qui affiche une date.
const DATE_LOCALE = { fr: "fr-MA", en: "en-US", ar: "ar-MA" };

export function dateLocale(lang) {
  return DATE_LOCALE[lang] || DATE_LOCALE.fr;
}
