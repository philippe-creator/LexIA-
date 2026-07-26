import React, { useState, useEffect } from "react";
import { Check, Crown, Loader2 } from "lucide-react";
import { billingService } from "../services/api";
import { useAuth } from "../contexts/AuthContext";
import { useReveal } from "../hooks/useReveal";

export default function Pricing() {
  const { user, updateUser } = useAuth();
  const [plans, setPlans] = useState([]);
  const [usage, setUsage] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const load = () => {
    billingService.plans().then((r) => setPlans(r.data.plans)).catch(() => setError("Impossible de charger les offres."));
    billingService.me().then((r) => setUsage(r.data)).catch(() => {});
  };
  useEffect(load, []);
  useReveal([plans]);

  const currentPlan = usage?.plan || user?.plan || "free";

  const choose = async (planKey) => {
    setError(null); setNotice(null); setBusy(planKey);
    try {
      if (planKey === "free") {
        await billingService.cancel();
        setNotice("Vous êtes repassé à l'offre Gratuit.");
      } else {
        await billingService.subscribe(planKey);
        setNotice("Offre Pro activée. Profitez des questions illimitées et de toutes les fonctionnalités !");
      }
      updateUser({ plan: planKey });
      load();
    } catch (e) {
      setError(e.response?.data?.detail || "Opération impossible.");
    } finally { setBusy(null); }
  };

  return (
    <div className="pricing-container">
      <div className="pricing-head">
        <h2>Nos offres</h2>
        <p>Commencez gratuitement. Passez à Pro quand vous en avez besoin.</p>
        {usage && !usage.unlimited && (
          <p className="pricing-usage">Ce mois-ci : <strong>{usage.questions_used}/{usage.monthly_questions}</strong> questions utilisées.</p>
        )}
        {usage && usage.unlimited && <p className="pricing-usage">Offre Pro active — questions illimitées.</p>}
      </div>

      {notice && <div className="pricing-notice">{notice}</div>}
      {error && <div className="calc-error" style={{ maxWidth: 720, margin: "0 auto 16px" }}>{error}</div>}

      <div className="pricing-grid">
        {plans.map((p) => {
          const isCurrent = p.key === currentPlan;
          const isPro = p.key === "pro";
          return (
            <div key={p.key} className={`pricing-card reveal ${isPro ? "pricing-card-pro" : ""} ${isCurrent ? "pricing-card-current" : ""}`}>
              {isPro && <div className="pricing-ribbon"><Crown size={13} /> Recommandé</div>}
              <div className="pricing-card-head">
                <h3>{p.label}</h3>
                <div className="pricing-price">
                  {p.price_mad === 0 ? "Gratuit" : <>{p.price_mad} <span className="pricing-price-unit">MAD / mois</span></>}
                </div>
                <p className="pricing-tagline">{p.tagline}</p>
              </div>
              <ul className="pricing-features">
                {p.highlights.map((h, i) => (
                  <li key={i}><Check size={15} className="pricing-check" /> {h}</li>
                ))}
              </ul>
              <button
                className={`pricing-cta ${isPro ? "pricing-cta-pro" : ""}`}
                disabled={isCurrent || busy !== null}
                onClick={() => choose(p.key)}
              >
                {busy === p.key ? <Loader2 size={15} className="spin" /> : isCurrent ? "Votre offre actuelle" : isPro ? "Passer à Pro" : "Choisir Gratuit"}
              </button>
            </div>
          );
        })}
      </div>

      <p className="pricing-foot">
        Paiement en cours d'intégration — l'activation est actuellement immédiate à des fins de démonstration.
      </p>
    </div>
  );
}
