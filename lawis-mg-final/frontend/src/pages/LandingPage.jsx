import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Scale, Search, GitCompare, Calculator, Upload, MessageSquare, CheckCircle2, ArrowRight } from "lucide-react";
import api from "../services/api";

const DOMAIN_LABELS = { travail: "Droit du travail", fiscal: "Droit fiscal", societes: "Droit des sociétés", donnees_personnelles: "Données personnelles", jurisprudence: "Jurisprudence", divers: "Divers" };

const FEATURES = [
  { icon: MessageSquare, title: "Chat juridique sourcé", desc: "Posez une question en français, obtenez une réponse structurée citant l'article, le document et la page exacts — vérifiable dans le texte officiel." },
  { icon: Search, title: "Recherche par référence", desc: "Retrouvez directement un texte par son numéro exact (loi 09-08, article 62, dahir 1-72-184)." },
  { icon: GitCompare, title: "Comparaison de versions", desc: "Visualisez les ajouts, suppressions et modifications entre deux versions d'un même texte." },
  { icon: Calculator, title: "Calculateurs juridiques", desc: "Indemnité de licenciement, préavis, salaire net — calculs déterministes fondés sur le code du travail, avec référence à l'article applicable." },
  { icon: Upload, title: "Vos documents", desc: "Importez vos propres PDF, Word ou texte pour les interroger via le chat — visibles par vous seul." },
];

const STEPS = [
  { n: "01", title: "Posez votre question", desc: "En français, sur le droit du travail, fiscal, des sociétés ou la protection des données personnelles." },
  { n: "02", title: "Recherche hybride", desc: "Recherche sémantique + lexicale dans les corpus officiels indexés, re-classées par pertinence réelle." },
  { n: "03", title: "Réponse sourcée", desc: "Réponse adaptée à votre profil, citant l'article et la page exacts — jamais d'information non fondée sur un texte réellement récupéré." },
];

export default function LandingPage() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.get("/health").then((r) => setStats(r.data)).catch(() => {});
  }, []);

  const domainsWithData = stats ? Object.entries(stats.corpus_stats || {}).filter(([, n]) => n > 0) : [];

  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-logo">
          <div className="sidebar-logo-icon"><Scale size={18}/></div>
          <div>
            <span className="landing-brand">LexIA Maroc</span>
            <span className="landing-tagline">Veille juridique intelligente</span>
          </div>
        </div>
        <div className="landing-header-actions">
          <Link to="/login" className="landing-btn-ghost">Connexion</Link>
          <Link to="/login" className="landing-btn-primary">Créer un compte</Link>
        </div>
      </header>

      <section className="landing-hero">
        <span className="landing-badge">Plateforme multi-RAG · Droit marocain</span>
        <h1>Le droit marocain,<br/><span className="landing-gold">interrogeable en langage naturel.</span></h1>
        <p className="landing-hero-sub">
          Assistant juridique fondé sur une architecture multi-RAG (recherche hybride, re-classement,
          citation systématique des sources) — conçu pour aider étudiants, particuliers, juristes,
          avocats et entreprises à naviguer le droit du travail, fiscal, des sociétés et la protection
          des données personnelles au Maroc.
        </p>
        <div className="landing-hero-cta">
          <Link to="/login" className="landing-btn-primary landing-btn-lg">Essayer maintenant <ArrowRight size={16}/></Link>
        </div>

        {stats && (
          <div className="landing-stats">
            <div className="landing-stat"><span className="landing-stat-value">{stats.total_chunks?.toLocaleString("fr-MA")}</span><span className="landing-stat-label">passages juridiques indexés</span></div>
            <div className="landing-stat"><span className="landing-stat-value">{domainsWithData.length}</span><span className="landing-stat-label">domaines actifs sur 6</span></div>
            <div className="landing-stat"><span className="landing-stat-value">FR</span><span className="landing-stat-label">langue d'interrogation</span></div>
          </div>
        )}
      </section>

      <section className="landing-section">
        <h2 className="landing-section-title">Comment ça marche</h2>
        <div className="landing-steps">
          {STEPS.map((s) => (
            <div key={s.n} className="landing-step">
              <span className="landing-step-num">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section landing-section-alt">
        <h2 className="landing-section-title">Fonctionnalités</h2>
        <div className="landing-features">
          {FEATURES.map((f) => (
            <div key={f.title} className="landing-feature-card">
              <div className="landing-feature-icon"><f.icon size={20}/></div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section">
        <h2 className="landing-section-title">Domaines couverts</h2>
        <p className="landing-section-sub">L'architecture est conçue pour accueillir n'importe quel nombre de corpus thématiques sans refonte. État actuel de l'indexation :</p>
        <div className="landing-domains">
          {Object.entries(DOMAIN_LABELS).map(([key, label]) => {
            const count = stats?.corpus_stats?.[key] || 0;
            return (
              <div key={key} className={`landing-domain-chip ${count > 0 ? "active" : ""}`}>
                {count > 0 && <CheckCircle2 size={13}/>}
                <span>{label}</span>
                {stats && <span className="landing-domain-count">{count > 0 ? `${count} passages` : "en cours"}</span>}
              </div>
            );
          })}
        </div>
      </section>

      <footer className="landing-footer">
        <p>Stage de fin d'année — Transformation Digitale Industrielle · Zenithsoft, Rabat</p>
        <p className="landing-disclaimer">Les réponses fournies sont informatives et ne constituent pas un avis juridique professionnel.</p>
      </footer>
    </div>
  );
}
