import { useState, useEffect, useRef } from "react";

// Anime un nombre de 0 jusqu'à `target` (ease-out) quand l'élément entre à
// l'écran. Donne aux statistiques réelles un effet « temps réel ».
export function useCountUp(target, duration = 1400) {
  const [value, setValue] = useState(0);
  const ref = useRef(null);
  const started = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || target == null) return;
    const run = () => {
      if (started.current) return;
      started.current = true;
      const t0 = performance.now();
      const tick = (now) => {
        const p = Math.min((now - t0) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3); // ease-out cubic
        setValue(Math.round(eased * target));
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && run()),
      { threshold: 0.4 }
    );
    obs.observe(el);
    // Filet de sécurité : si l'observer ne se déclenche pas, on anime quand même
    // après un court délai pour ne jamais rester bloqué sur « 0 ».
    const fallback = setTimeout(run, 1600);
    return () => { obs.disconnect(); clearTimeout(fallback); };
  }, [target, duration]);

  return [value, ref];
}
