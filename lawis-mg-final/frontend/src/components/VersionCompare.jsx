import React, { useState, useEffect } from "react";
import { GitCompare, RefreshCw, Plus, Minus } from "lucide-react";
import { compareService } from "../services/api";
const DOMAINS = [{value:"travail",label:"Droit du travail"},{value:"fiscal",label:"Droit fiscal"},{value:"societes",label:"Droit des sociétés"},{value:"donnees_personnelles",label:"Protection des données"},{value:"jurisprudence",label:"Jurisprudence"}];
export default function VersionCompare() {
  const [domain, setDomain] = useState("travail");
  const [versions, setVersions] = useState([]);
  const [v1, setV1] = useState("");
  const [v2, setV2] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  useEffect(() => {
    compareService.versions(domain).then(r=>{setVersions(r.data||[]);setV1("");setV2("");setResult(null);}).catch(()=>setVersions([]));
  }, [domain]);
  const label = (s) => `${s.filename} — ${new Date(s.created_at).toLocaleDateString("fr-MA")}`;
  const compare = async () => {
    if(!v1||!v2||v1===v2) return;
    setLoading(true); setError(null);
    try { const res=await compareService.compare({snapshot_id_1:v1,snapshot_id_2:v2}); setResult(res.data); }
    catch(e) { setError(e.response?.data?.detail||"Erreur."); }
    finally { setLoading(false); }
  };
  return (
    <div className="compare-container">
      <div className="compare-header"><GitCompare size={20}/><h2>Comparaison de versions</h2></div>
      <p className="compare-subtitle">Détectez les changements entre deux versions d'un texte juridique déjà indexé.</p>
      <div className="compare-selectors">
        <div className="selector-group"><label>Domaine</label>
          <select value={domain} onChange={e=>setDomain(e.target.value)} className="select-input">{DOMAINS.map(d=><option key={d.value} value={d.value}>{d.label}</option>)}</select>
        </div>
        <div className="selector-group"><label>Version A</label>
          <select value={v1} onChange={e=>setV1(e.target.value)} className="select-input"><option value="">-- Choisir --</option>{versions.map(v=><option key={v.id} value={v.id}>{label(v)}</option>)}</select>
        </div>
        <div className="selector-group"><label>Version B</label>
          <select value={v2} onChange={e=>setV2(e.target.value)} className="select-input"><option value="">-- Choisir --</option>{versions.map(v=><option key={v.id} value={v.id}>{label(v)}</option>)}</select>
        </div>
        <button onClick={compare} disabled={!v1||!v2||v1===v2||loading} className="compare-btn">{loading?<RefreshCw size={16} className="spin"/>:<GitCompare size={16}/>} Comparer</button>
      </div>
      {versions.length===0 && <div className="compare-empty">Aucune version indexée pour ce domaine pour l'instant. Une version est enregistrée à chaque ingestion d'un texte.</div>}
      {error && <div style={{color:"#DC2626",padding:"10px",background:"#FEF2F2",borderRadius:"7px",marginBottom:"12px"}}>{error}</div>}
      {result && (
        <div className="compare-results">
          <div className="compare-summary">
            <span style={{fontSize:"14px",fontWeight:500}}>{result.summary}</span>
            <div className="summary-stats"><span className="stat added">+{result.total_added}</span><span className="stat removed">-{result.total_removed}</span><span className="stat changed">~{result.total_changed}</span></div>
          </div>
          <div className="diff-view">
            <div className="diff-header"><span className="diff-file v1">{result.filename_v1}</span><span className="diff-arrow">→</span><span className="diff-file v2">{result.filename_v2}</span></div>
            {result.diff_blocks.length===0 ? <div className="diff-empty">Aucune différence.</div> :
              result.diff_blocks.map((b,i)=>(
                <div key={i} className={`diff-block diff-${b.type}`}>
                  {(b.type==="removed"||b.type==="changed")&&b.lines_v1.map((l,j)=>(<div key={j} className="diff-line removed"><Minus size={12} className="diff-icon"/><span className="line-num">{(b.line_number_v1||0)+j}</span><span className="line-text">{l}</span></div>))}
                  {(b.type==="added"||b.type==="changed")&&b.lines_v2.map((l,j)=>(<div key={j} className="diff-line added"><Plus size={12} className="diff-icon"/><span className="line-num">{(b.line_number_v2||0)+j}</span><span className="line-text">{l}</span></div>))}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
