import React, { useState, useEffect, useRef } from "react";
import { MessageSquare, FileText } from "lucide-react";

// Démonstrations réelles (contenu vérifié dans le corpus). Jouées en boucle,
// « tapées » à l'écran, pour donner à la landing un aperçu vivant du produit
// SANS solliciter l'API à chaque visite.
const SCRIPT = [
  {
    q: "Quelle est la durée de la période d'essai pour un cadre ?",
    a: "Trois mois pour les cadres et assimilés, renouvelable une seule fois (article 14 du Code du travail).",
    sources: ["Code du travail 65-99 — p. 17"],
  },
  {
    q: "Un employeur peut-il licencier sans entendre le salarié ?",
    a: "Non. Avant tout licenciement, le salarié doit pouvoir se défendre et être entendu par l'employeur (article 62).",
    sources: ["Code du travail 65-99 — p. 34"],
  },
  {
    q: "Que risque le salarié en cas de licenciement abusif ?",
    a: "Il a droit à des dommages-intérêts et à l'indemnité de préavis (article 59), et peut demander sa réintégration par la conciliation (article 41).",
    sources: ["Code du travail 65-99 — p. 33", "p. 28"],
  },
];

// Phases : tape la question → réfléchit → tape la réponse → montre les sources
// → pause → suivant.
export default function LiveDemo() {
  const [idx, setIdx] = useState(0);
  const [qText, setQText] = useState("");
  const [aText, setAText] = useState("");
  const [phase, setPhase] = useState("q"); // q | thinking | a | done
  const timer = useRef(null);

  useEffect(() => {
    const item = SCRIPT[idx];
    let cancelled = false;
    const clear = () => timer.current && clearTimeout(timer.current);

    const typeInto = (full, setter, speed, onDone) => {
      let i = 0;
      const step = () => {
        if (cancelled) return;
        i++;
        setter(full.slice(0, i));
        if (i < full.length) timer.current = setTimeout(step, speed);
        else onDone && (timer.current = setTimeout(onDone, 600));
      };
      step();
    };

    setQText(""); setAText(""); setPhase("q");
    typeInto(item.q, setQText, 34, () => {
      if (cancelled) return;
      setPhase("thinking");
      timer.current = setTimeout(() => {
        if (cancelled) return;
        setPhase("a");
        typeInto(item.a, setAText, 20, () => {
          if (cancelled) return;
          setPhase("done");
          timer.current = setTimeout(() => setIdx((p) => (p + 1) % SCRIPT.length), 2600);
        });
      }, 900);
    });

    return () => { cancelled = true; clear(); };
  }, [idx]);

  const item = SCRIPT[idx];

  return (
    <div className="livedemo" aria-hidden="true">
      <div className="livedemo-q">
        <span className="livedemo-avatar livedemo-avatar-user">Q</span>
        <div className="livedemo-bubble livedemo-bubble-q">
          {qText}{phase === "q" && <span className="stream-cursor">▍</span>}
        </div>
      </div>
      {(phase === "thinking" || phase === "a" || phase === "done") && (
        <div className="livedemo-a">
          <span className="livedemo-avatar livedemo-avatar-ai"><MessageSquare size={13}/></span>
          <div className="livedemo-bubble livedemo-bubble-a">
            {phase === "thinking" ? (
              <span className="livedemo-dots"><i/><i/><i/></span>
            ) : (
              <>
                <span>{aText}{phase === "a" && <span className="stream-cursor">▍</span>}</span>
                {phase === "done" && (
                  <div className="livedemo-sources">
                    <FileText size={11}/>
                    {item.sources.map((s, i) => <span key={i} className="livedemo-source">{s}</span>)}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
