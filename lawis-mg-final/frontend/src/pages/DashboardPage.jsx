import React, { useState, useEffect } from "react";
import { Database, Clock, RefreshCw, AlertCircle, TrendingUp } from "lucide-react";
import { searchService, watchService } from "../services/api";
const DL = { travail:"Droit du travail", fiscal:"Droit fiscal", societes:"Droit des sociétés", donnees_personnelles:"Protection des données", jurisprudence:"Jurisprudence", divers:"Divers" };
export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [watch, setWatch] = useState(null);
  const [triggering, setTriggering] = useState(false);
  useEffect(() => {
    searchService.stats().then(r=>setStats(r.data)).catch(()=>{});
    watchService.status().then(r=>setWatch(r.data)).catch(()=>{});
  }, []);
  const trigger = async () => {
    setTriggering(true);
    try { await watchService.trigger(); const r=await watchService.status(); setWatch(r.data); }
    catch {} finally { setTriggering(false); }
  };
  return (
    <div className="page-container">
      <div className="page-header"><h1>Tableau de bord</h1><p>État des corpus et de la veille réglementaire.</p></div>
      <section className="dashboard-section">
        <h2><Database size={17}/> Corpus indexés</h2>
        {stats ? (
          <>
            <div className="stats-grid">
              {Object.entries(stats.stats).map(([d,n]) => (
                <div key={d} className="stat-card"><div className="stat-label">{DL[d]||d}</div><div className="stat-value">{n.toLocaleString()}</div><div className="stat-unit">chunks</div></div>
              ))}
              <div className="stat-card highlight"><div className="stat-label">Total</div><div className="stat-value">{stats.total_chunks.toLocaleString()}</div><div className="stat-unit">chunks</div></div>
            </div>
            {stats.total_chunks===0 && <div className="dashboard-alert"><AlertCircle size={15}/> Corpus vide. Lancez : <code>docker-compose exec api python ingestion/watcher.py</code></div>}
          </>
        ) : <p className="text-muted">Chargement...</p>}
      </section>
      <section className="dashboard-section">
        <div className="section-header-row">
          <h2><Clock size={17}/> Veille réglementaire</h2>
          <button className="btn-secondary" onClick={trigger} disabled={triggering}><RefreshCw size={13} className={triggering?"spin":""}/> {triggering?"En cours...":"Lancer un cycle"}</button>
        </div>
        {watch ? (
          <>
            <p className="text-muted">Dernière vérification : {watch.last_run ? new Date(watch.last_run).toLocaleString("fr-MA") : "Jamais"}</p>
            {watch.new_documents_count>0 && <div className="dashboard-alert success"><TrendingUp size={14}/> {watch.new_documents_count} nouveau(x) document(s).</div>}
            <table className="data-table">
              <thead><tr><th>Source</th><th>Documents</th><th>Dernière vérif.</th><th>Statut</th></tr></thead>
              <tbody>{watch.sources.map(s=>(
                <tr key={s.name}>
                  <td><strong>{s.name?.toUpperCase()}</strong></td>
                  <td>{s.doc_count||"—"}</td>
                  <td>{s.last_check ? new Date(s.last_check).toLocaleString("fr-MA") : "—"}</td>
                  <td><span className={`status-badge ${s.changed?"changed":"stable"}`}>{s.changed?"Mis à jour":"Stable"}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </>
        ) : <p className="text-muted">Chargement...</p>}
      </section>
    </div>
  );
}
