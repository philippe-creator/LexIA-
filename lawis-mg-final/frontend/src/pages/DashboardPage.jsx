import React, { useState, useEffect } from "react";
import { Database, Clock, RefreshCw, AlertCircle, TrendingUp, Users, BarChart3, Crown } from "lucide-react";
import { searchService, watchService, adminService, extractErrorMessage } from "../services/api";
import { useAuth } from "../contexts/AuthContext";
const DL = { travail:"Droit du travail", fiscal:"Droit fiscal", societes:"Droit des sociétés", donnees_personnelles:"Protection des données", penal:"Droit pénal", jurisprudence:"Jurisprudence", divers:"Divers" };

export default function DashboardPage() {
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
    } catch (err) { setUserActionError(extractErrorMessage(err, "Échec de la promotion.")); }
    finally { setUserActionLoading(null); }
  };
  const handleDemote = async (id) => {
    setUserActionError(""); setUserActionLoading(id);
    try {
      await adminService.demote(id);
      const r = await adminService.listUsers(); setUsers(r.data);
    } catch (err) { setUserActionError(extractErrorMessage(err, "Échec de la rétrogradation.")); }
    finally { setUserActionLoading(null); }
  };

  return (
    <div className="page-container">
      <div className="page-header"><h1>Tableau de bord</h1><p>État des corpus et de la veille réglementaire.</p></div>

      {overview && (
        <section className="dashboard-section">
          <h2><BarChart3 size={17}/> Activité</h2>
          <div className="stats-grid">
            <div className="stat-card"><div className="stat-label">Comptes</div><div className="stat-value">{overview.total_users}</div><div className="stat-unit">dont {overview.verified_users} vérifiés</div></div>
            <div className="stat-card"><div className="stat-label">Admins</div><div className="stat-value">{overview.admin_count}</div></div>
            <div className="stat-card"><div className="stat-label">Messages (7j)</div><div className="stat-value">{overview.messages_last_7d}</div></div>
            <div className="stat-card"><div className="stat-label">Messages (30j)</div><div className="stat-value">{overview.messages_last_30d}</div></div>
          </div>
          {overview.top_domains?.length > 0 && (
            <table className="data-table" style={{marginTop:12}}>
              <thead><tr><th>Domaine le plus demandé</th><th>Conversations</th></tr></thead>
              <tbody>{overview.top_domains.map(d => (
                <tr key={d.domain}><td>{DL[d.domain]||d.domain}</td><td>{d.count}</td></tr>
              ))}</tbody>
            </table>
          )}
        </section>
      )}

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

      {user?.is_owner && (
        <section className="dashboard-section">
          <h2><Users size={17}/> Gestion des comptes</h2>
          <p className="text-muted" style={{marginBottom:10}}>Réservé au propriétaire — promouvoir ou rétrograder des comptes admin.</p>
          {userActionError && <div className="dashboard-alert"><AlertCircle size={15}/> {userActionError}</div>}
          {users ? (
            <table className="data-table">
              <thead><tr><th>Compte</th><th>Email</th><th>Rôle</th><th></th></tr></thead>
              <tbody>{users.map(u => (
                <tr key={u.id}>
                  <td><strong>{u.username}</strong>{u.is_owner && <Crown size={13} style={{marginLeft:6,verticalAlign:"middle",color:"var(--gold-dark)"}} title="Propriétaire"/>}</td>
                  <td>{u.email}</td>
                  <td><span className={`status-badge ${u.role==="admin"?"changed":"stable"}`}>{u.role}</span></td>
                  <td>
                    {u.is_owner ? null : u.role === "admin" ? (
                      <button className="text-btn" disabled={userActionLoading===u.id} onClick={() => handleDemote(u.id)}>Rétrograder</button>
                    ) : (
                      <button className="text-btn" disabled={userActionLoading===u.id} onClick={() => handlePromote(u.id)}>Promouvoir admin</button>
                    )}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          ) : <p className="text-muted">Chargement...</p>}
        </section>
      )}
    </div>
  );
}
