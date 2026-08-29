import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Database, Clock, RefreshCw, AlertCircle, TrendingUp, Users, BarChart3, Crown, Gauge } from "lucide-react";
import { searchService, watchService, adminService, extractErrorMessage } from "../services/api";
import { useAuth } from "../contexts/AuthContext";
import { useLanguage } from "../contexts/LanguageContext";
import { dateLocale } from "../i18n/dateLocale";
const CONFIDENCE_ORDER = ["élevé", "moyen", "faible", "insuffisant"];
const CONFIDENCE_META = {
  "élevé": { color: "#16A34A", labelKey: "confidence.high" },
  "moyen": { color: "#D97706", labelKey: "confidence.medium" },
  "faible": { color: "#DC2626", labelKey: "confidence.low" },
  "insuffisant": { color: "#6B7280", labelKey: "confidence.insufficient" },
};

export default function DashboardPage() {
  const { t } = useTranslation();
  const { lang } = useLanguage();
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [watch, setWatch] = useState(null);
  const [triggering, setTriggering] = useState(false);
  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState(null);
  const [userActionError, setUserActionError] = useState("");
  const [userActionLoading, setUserActionLoading] = useState(null);

  useEffect(() => {
    searchService.stats().then(r=>setStats(r.data)).catch(()=>{});
    watchService.status().then(r=>setWatch(r.data)).catch(()=>{});
    adminService.overview().then(r=>setOverview(r.data)).catch(()=>{});
    if (user?.is_owner) adminService.listUsers().then(r=>setUsers(r.data)).catch(()=>{});
  }, [user]);

  const trigger = async () => {
    setTriggering(true);
    try { await watchService.trigger(); const r=await watchService.status(); setWatch(r.data); }
    catch {} finally { setTriggering(false); }
  };

  const handlePromote = async (id) => {
    setUserActionError(""); setUserActionLoading(id);
    try {
      await adminService.promote(id);
      const r = await adminService.listUsers(); setUsers(r.data);
    } catch (err) { setUserActionError(extractErrorMessage(err, t("dashboard.promote"))); }
    finally { setUserActionLoading(null); }
  };
  const handleDemote = async (id) => {
    setUserActionError(""); setUserActionLoading(id);
    try {
      await adminService.demote(id);
      const r = await adminService.listUsers(); setUsers(r.data);
    } catch (err) { setUserActionError(extractErrorMessage(err, t("dashboard.demote"))); }
    finally { setUserActionLoading(null); }
  };

  return (
    <div className="page-container">
      <div className="page-header"><h1>{t("dashboard.title")}</h1><p>{t("dashboard.subtitle")}</p></div>

      {overview && (
        <section className="dashboard-section">
          <h2><BarChart3 size={17}/> {t("dashboard.activity")}</h2>
          <div className="stats-grid">
            <div className="stat-card"><div className="stat-label">{t("dashboard.accounts")}</div><div className="stat-value">{overview.total_users}</div><div className="stat-unit">{t("dashboard.verifiedSuffix", { count: overview.verified_users })}</div></div>
            <div className="stat-card"><div className="stat-label">{t("dashboard.admins")}</div><div className="stat-value">{overview.admin_count}</div></div>
            <div className="stat-card"><div className="stat-label">{t("dashboard.messages7d")}</div><div className="stat-value">{overview.messages_last_7d}</div></div>
            <div className="stat-card"><div className="stat-label">{t("dashboard.messages30d")}</div><div className="stat-value">{overview.messages_last_30d}</div></div>
          </div>
          {overview.top_domains?.length > 0 && (
            <table className="data-table" style={{marginTop:12}}>
              <thead><tr><th>{t("dashboard.topDomain")}</th><th>{t("dashboard.conversations")}</th></tr></thead>
              <tbody>{overview.top_domains.map(d => (
                <tr key={d.domain}><td>{t(`domain.${d.domain}`, d.domain)}</td><td>{d.count}</td></tr>
              ))}</tbody>
            </table>
          )}
        </section>
      )}

      {overview && (
        <section className="dashboard-section">
          <h2><Gauge size={17}/> {t("dashboard.responseQuality")}</h2>
          {overview.total_answered > 0 ? (
            <>
              <div className="stats-grid">
                <div className="stat-card"><div className="stat-label">{t("dashboard.avgConfidence")}</div><div className="stat-value">{Math.round(overview.avg_confidence_score*100)}%</div></div>
                <div className="stat-card"><div className="stat-label">{t("dashboard.insufficientResponses")}</div><div className="stat-value">{overview.insufficient_rate_pct}%</div><div className="stat-unit">{t("dashboard.noSourceFound")}</div></div>
              </div>
              <div className="confidence-bar" style={{marginTop:14}}>
                {CONFIDENCE_ORDER.map(label => {
                  const count = overview.confidence_distribution[label] || 0;
                  const pct = (count / overview.total_answered) * 100;
                  return pct > 0 ? <div key={label} style={{width:`${pct}%`, background: CONFIDENCE_META[label].color}} title={`${t(CONFIDENCE_META[label].labelKey)} : ${count}`}/> : null;
                })}
              </div>
              <div className="confidence-legend">
                {CONFIDENCE_ORDER.map(label => (
                  <span key={label}><i style={{background: CONFIDENCE_META[label].color}}/>{t(CONFIDENCE_META[label].labelKey)} ({overview.confidence_distribution[label] || 0})</span>
                ))}
              </div>
            </>
          ) : <p className="text-muted">{t("dashboard.noAnswersYet")}</p>}
        </section>
      )}

      <section className="dashboard-section">
        <h2><Database size={17}/> {t("dashboard.corpusIndexed")}</h2>
        {stats ? (
          <>
            <div className="stats-grid">
              {Object.entries(stats.documents).map(([d,n]) => (
                <div key={d} className="stat-card"><div className="stat-label">{t(`domain.${d}`, d)}</div><div className="stat-value">{n.toLocaleString()}</div><div className="stat-unit">{t("dashboard.documentsChunks", { docs: n.toLocaleString(), chunks: (stats.stats[d]||0).toLocaleString() })}</div></div>
              ))}
              <div className="stat-card highlight"><div className="stat-label">{t("dashboard.total")}</div><div className="stat-value">{stats.total_documents.toLocaleString()}</div><div className="stat-unit">{t("dashboard.documentsChunks", { docs: stats.total_documents.toLocaleString(), chunks: stats.total_chunks.toLocaleString() })}</div></div>
            </div>
            {stats.total_documents===0 && <div className="dashboard-alert"><AlertCircle size={15}/> {t("dashboard.emptyCorpus")} <code>docker-compose exec api python ingestion/watcher.py</code></div>}
          </>
        ) : <p className="text-muted">{t("dashboard.loading")}</p>}
      </section>

      <section className="dashboard-section">
        <div className="section-header-row">
          <h2><Clock size={17}/> {t("dashboard.watch")}</h2>
          <button className="btn-secondary" onClick={trigger} disabled={triggering}><RefreshCw size={13} className={triggering?"spin":""}/> {triggering?t("dashboard.running"):t("dashboard.runCycle")}</button>
        </div>
        {watch ? (
          <>
            <p className="text-muted">{t("dashboard.lastCheck")} {watch.last_run ? new Date(watch.last_run).toLocaleString(dateLocale(lang)) : t("dashboard.never")}</p>
            {watch.new_documents_count>0 && <div className="dashboard-alert success"><TrendingUp size={14}/> {t("dashboard.newDocuments", { count: watch.new_documents_count })}</div>}
            <table className="data-table">
              <thead><tr><th>{t("dashboard.source")}</th><th>{t("dashboard.documents")}</th><th>{t("dashboard.lastVerif")}</th><th>{t("dashboard.status")}</th></tr></thead>
              <tbody>{watch.sources.map(s=>(
                <tr key={s.name}>
                  <td><strong>{s.name?.toUpperCase()}</strong></td>
                  <td>{s.doc_count||"—"}</td>
                  <td>{s.last_check ? new Date(s.last_check).toLocaleString(dateLocale(lang)) : "—"}</td>
                  <td><span className={`status-badge ${s.changed?"changed":"stable"}`}>{s.changed?t("dashboard.updated"):t("dashboard.stable")}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </>
        ) : <p className="text-muted">{t("dashboard.loading")}</p>}
      </section>

      {user?.is_owner && (
        <section className="dashboard-section">
          <h2><Users size={17}/> {t("dashboard.accountManagement")}</h2>
          <p className="text-muted" style={{marginBottom:10}}>{t("dashboard.ownerOnly")}</p>
          {userActionError && <div className="dashboard-alert"><AlertCircle size={15}/> {userActionError}</div>}
          {users ? (
            <table className="data-table">
              <thead><tr><th>{t("dashboard.account")}</th><th>{t("dashboard.email")}</th><th>{t("dashboard.role")}</th><th></th></tr></thead>
              <tbody>{users.map(u => (
                <tr key={u.id}>
                  <td><strong>{u.username}</strong>{u.is_owner && <Crown size={13} style={{marginLeft:6,verticalAlign:"middle",color:"var(--gold-dark)"}} title={t("dashboard.owner")}/>}</td>
                  <td>{u.email}</td>
                  <td><span className={`status-badge ${u.role==="admin"?"changed":"stable"}`}>{u.role}</span></td>
                  <td>
                    {u.is_owner ? null : u.role === "admin" ? (
                      <button className="text-btn" disabled={userActionLoading===u.id} onClick={() => handleDemote(u.id)}>{t("dashboard.demote")}</button>
                    ) : (
                      <button className="text-btn" disabled={userActionLoading===u.id} onClick={() => handlePromote(u.id)}>{t("dashboard.promote")}</button>
                    )}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          ) : <p className="text-muted">{t("dashboard.loading")}</p>}
        </section>
      )}
    </div>
  );
}
