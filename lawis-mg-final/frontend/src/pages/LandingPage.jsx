import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Scale, Search, GitCompare, Calculator, Upload, MessageSquare, CheckCircle2, ArrowRight, Send, Loader2, ExternalLink } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { chatService, watchService, searchService, extractErrorMessage } from "../services/api";
import LiveDemo from "../components/landing/LiveDemo";
import { useCountUp } from "../hooks/useCountUp";
import { useReveal } from "../hooks/useReveal";
import LanguageSwitcher from "../components/LanguageSwitcher";
import { useLanguage } from "../contexts/LanguageContext";
import { dateLocale } from "../i18n/dateLocale";

// Statistique réelle avec compteur animé (0 → valeur à l'entrée à l'écran).
function CountStat({ value, label, suffix = "", numLocale }) {
  const [n, ref] = useCountUp(value || 0);
  return (
    <div className="landing-stat" ref={ref}>
      <span className="landing-stat-value">{n.toLocaleString(numLocale)}{suffix}</span>
      <span className="landing-stat-label">{label}</span>
    </div>
  );
}

const FEATURES = [
  { icon: MessageSquare, key: "chat" },
  { icon: Search, key: "reference" },
  { icon: GitCompare, key: "compare" },
  { icon: Calculator, key: "calculators" },
  { icon: Upload, key: "documents" },
];

const STEPS = [
  { n: "01", key: "step1" },
  { n: "02", key: "step2" },
  { n: "03", key: "step3" },
];

const DOMAIN_KEYS = ["travail", "fiscal", "societes", "donnees_personnelles", "penal", "jurisprudence", "divers"];

export default function LandingPage() {
  const { t } = useTranslation();
  const { lang } = useLanguage();
  const numLocale = dateLocale(lang);
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [demoQuery, setDemoQuery] = useState("");
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoResult, setDemoResult] = useState(null);
  const [demoError, setDemoError] = useState(null);

  useEffect(() => {
    searchService.stats().then((r) => setStats(r.data)).catch(() => {});
    watchService.recentTexts().then((r) => setRecent(r.data || [])).catch(() => {});
  }, []);
  useReveal([stats, recent]);

  const runDemo = async (q) => {
    const query = (q || demoQuery).trim();
    if (!query || demoLoading) return;
    if (q) setDemoQuery(q);
    setDemoLoading(true); setDemoError(null); setDemoResult(null);
    try {
      const res = await chatService.demo(query);
      setDemoResult(res.data);
    } catch (e) {
      setDemoError(extractErrorMessage(e, t("landing.demoServiceError")));
    } finally { setDemoLoading(false); }
  };

  const domainsWithData = stats ? Object.entries(stats.documents || {}).filter(([, n]) => n > 0) : [];
  const totalDomainCount = stats ? Object.keys(stats.documents || {}).length : 0;
  const demoExamples = t("landing.demoExamples", { returnObjects: true });

  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-logo">
          <div className="sidebar-logo-icon"><Scale size={18}/></div>
          <div>
            <span className="landing-brand">LexIA Maroc</span>
            <span className="landing-tagline">{t("landing.tagline")}</span>
          </div>
        </div>
        <div className="landing-header-actions">
          <LanguageSwitcher />
          <Link to="/login" className="landing-btn-ghost">{t("landing.login")}</Link>
          <Link to="/login" className="landing-btn-primary">{t("landing.signup")}</Link>
        </div>
      </header>

      {recent.length > 0 && (
        <div className="landing-ticker">
          <span className="landing-ticker-label">{t("landing.tickerLabel")}</span>
          <div className="landing-ticker-viewport">
            <div className="landing-ticker-track landing-ticker-scroll">
              {[...recent, ...recent].map((tItem, i) => (
                <span key={i} className="landing-ticker-item">
                  <span className="landing-ticker-dom">{t(`domainShort.${tItem.domain}`, tItem.domain)}</span>
                  {tItem.filename}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      <section className="landing-hero">
        <span className="landing-badge">{t("landing.badge")}</span>
        <h1>{t("landing.heroTitle")}<br/><span className="landing-gold">{t("landing.heroTitleGold")}</span></h1>
        <p className="landing-hero-sub">{t("landing.heroSub")}</p>
        <div className="landing-hero-cta">
          <Link to="/login" className="landing-btn-primary landing-btn-lg">{t("landing.ctaCreateAccount")} <ArrowRight size={16}/></Link>
        </div>

        <div className="demo-box">
          <div className="demo-box-label"><MessageSquare size={14}/> {t("landing.tryWithoutAccount")}</div>
          <div className="demo-input-row">
            <input
              className="demo-input"
              value={demoQuery}
              onChange={(e) => setDemoQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") runDemo(); }}
              placeholder={t("landing.demoPlaceholder")}
              maxLength={500}
              disabled={demoLoading}
            />
            <button className="demo-send" onClick={() => runDemo()} disabled={demoLoading || !demoQuery.trim()}>
              {demoLoading ? <Loader2 size={16} className="spin"/> : <Send size={16}/>}
            </button>
          </div>
          {!demoResult && !demoLoading && !demoError && (
            <>
              <LiveDemo/>
              <div className="demo-examples-label">{t("landing.orTryQuestions")}</div>
              <div className="demo-examples">
                {demoExamples.map((ex) => (
                  <button key={ex} className="demo-example" onClick={() => runDemo(ex)}>{ex}</button>
                ))}
              </div>
            </>
          )}
          {demoLoading && <div className="demo-loading"><Loader2 size={15} className="spin"/> {t("landing.searching")}</div>}
          {demoError && <div className="demo-error">{demoError}</div>}
          {demoResult && (
            <div className="demo-answer">
              <div className="demo-answer-text"><ReactMarkdown>{demoResult.answer}</ReactMarkdown></div>
              {demoResult.citations?.length > 0 && (
                <div className="demo-sources">
                  <span className="demo-sources-label"><ExternalLink size={12}/> {t("landing.sources")}</span>
                  {demoResult.citations.slice(0, 3).map((c, i) => (
                    <span key={i} className="demo-source-chip">{(c.filename || "document").replace(/\.(pdf|docx?|txt)$/i, "")}{c.page ? ` — p. ${c.page}` : ""}</span>
                  ))}
                </div>
              )}
              <div className="demo-footer">
                {typeof demoResult.remaining === "number" && <span className="demo-remaining">{t("landing.remainingDemo", { count: demoResult.remaining })}</span>}
                <Link to="/login" className="demo-cta-link">{t("landing.createAccountContinue")} <ArrowRight size={13}/></Link>
              </div>
            </div>
          )}
          <p className="demo-disclaimer">{t("landing.demoDisclaimer")}</p>
        </div>

        {stats && (
          <div className="landing-stats">
            <CountStat value={stats.total_documents} label={t("landing.statsDocuments")} numLocale={numLocale}/>
            <CountStat value={domainsWithData.length} label={t("landing.statsActiveDomains", { total: totalDomainCount })} numLocale={numLocale}/>
            <div className="landing-stat"><span className="landing-stat-value">3</span><span className="landing-stat-label">{t("landing.statsLanguages")}</span></div>
          </div>
        )}
      </section>

      <section className="landing-section reveal">
        <h2 className="landing-section-title">{t("landing.howItWorks")}</h2>
        <div className="landing-steps">
          {STEPS.map((s) => (
            <div key={s.n} className="landing-step">
              <span className="landing-step-num">{s.n}</span>
              <h3>{t(`landing.steps.${s.key}.title`)}</h3>
              <p>{t(`landing.steps.${s.key}.desc`)}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section landing-section-alt reveal">
        <h2 className="landing-section-title">{t("landing.featuresTitle")}</h2>
        <div className="landing-features">
          {FEATURES.map((f) => (
            <div key={f.key} className="landing-feature-card">
              <div className="landing-feature-icon"><f.icon size={20}/></div>
              <h3>{t(`landing.features.${f.key}.title`)}</h3>
              <p>{t(`landing.features.${f.key}.desc`)}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section reveal">
        <h2 className="landing-section-title">{t("landing.domainsCovered")}</h2>
        <p className="landing-section-sub">{t("landing.domainsSub")}</p>
        <div className="landing-domains">
          {DOMAIN_KEYS.map((key) => {
            const count = stats?.corpus_stats?.[key] || 0;
            return (
              <div key={key} className={`landing-domain-chip ${count > 0 ? "active" : ""}`}>
                {count > 0 && <CheckCircle2 size={13}/>}
                <span>{t(`domain.${key}`)}</span>
                {stats && <span className="landing-domain-count">{count > 0 ? t("landing.passagesCount", { count }) : t("landing.inProgress")}</span>}
              </div>
            );
          })}
        </div>
      </section>

      <footer className="landing-footer">
        <p>{t("landing.footerStage")}</p>
        <p className="landing-disclaimer">{t("landing.footerDisclaimer")}</p>
        <p className="landing-footer-links"><Link to="/cgu">{t("landing.cgu")}</Link> · <Link to="/confidentialite">{t("landing.privacy")}</Link></p>
      </footer>
    </div>
  );
}
