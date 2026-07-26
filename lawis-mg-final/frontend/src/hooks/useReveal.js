import { useEffect } from "react";

// Ajoute la classe `is-visible` aux éléments `.reveal` quand ils entrent à
// l'écran (animation d'apparition). Re-scanne quand `deps` change, car des
// sections peuvent apparaître après le chargement des données.
export function useReveal(deps = []) {
  useEffect(() => {
    const els = [...document.querySelectorAll(".reveal:not(.is-visible)")];
    if (!els.length) return;
    const reveal = (el) => el.classList.add("is-visible");
    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) { reveal(e.target); obs.unobserve(e.target); }
      }),
      { threshold: 0.12 }
    );
    els.forEach((el) => obs.observe(el));
    // Filet de sécurité : si l'observer ne se déclenche pas (onglet non composité,
    // navigateur exotique), on révèle tout après un court délai — jamais de
    // section laissée invisible.
    const fallback = setTimeout(() => els.forEach(reveal), 1600);
    return () => { obs.disconnect(); clearTimeout(fallback); };
    // eslint-disable-line
  }, deps);
}
