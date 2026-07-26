import React, { useState } from "react";
import { Hash, Search, ExternalLink, Loader2, FileText } from "lucide-react";
import { searchService } from "../services/api";
const DL = { travail:"Droit du travail", fiscal:"Droit fiscal", societes:"Droit des sociétés", donnees_personnelles:"Protection des données", jurisprudence:"Jurisprudence", divers:"Divers" };
const EXAMPLES = ["loi 09-08","article 62 code du travail","dahir 1-72-184","CGI 2026","loi 17-95","note circulaire TVA"];
const isSafeUrl = (url) => typeof url === "string" && (url.startsWith("http://") || url.startsWith("https://"));
export default function ReferenceSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const search = async (q=query) => {
    if(!q.trim()) return;
    setLoading(true); setError(null);
    try { const res=await searchService.reference({reference:q,top_k:5}); setResults(res.data); }
    catch { setError("Erreur lors de la recherche."); }
    finally { setLoading(false); }
  };
  return (
    <div className="reference-container">
      <div className="reference-header"><Hash size={20}/><h2>Recherche par référence</h2></div>
      <p className="reference-subtitle">Retrouvez un texte précis par son numéro de loi, d'article ou de dahir.</p>
      <div className="reference-search-bar">
        <input type="text" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key==="Enter"&&search()} placeholder='Ex: "loi 09-08"' className="reference-input"/>
        <button onClick={()=>search()} disabled={loading||!query.trim()} className="reference-btn">{loading?<Loader2 size={18} className="spin"/>:<Search size={18}/>}</button>
      </div>
      <div className="reference-examples">
        <span className="examples-label">Exemples :</span>
        {EXAMPLES.map(ex=><button key={ex} className="example-chip" onClick={()=>{setQuery(ex);search(ex);}}>{ex}</button>)}
      </div>
      {error && <div style={{color:"#DC2626",padding:"10px",background:"#FEF2F2",borderRadius:"7px",marginBottom:"12px"}}>{error}</div>}
      {results && (
        <div>
          {results.references_found?.length>0 && (
            <div className="detected-refs"><span>Références détectées :</span>{results.references_found.map(r=><span key={r} className="ref-tag">{r}</span>)}</div>
          )}
          {results.results?.length===0 ? (
            <div className="reference-empty">Aucun texte correspondant à cette référence dans les corpus indexés.<br/><small>Vérifiez le numéro, ou ce texte n'est peut-être pas encore couvert (ex. les circulaires ne sont pas indexées). Essayez une recherche par mots-clés dans l'assistant.</small></div>
          ) : (
            <div className="reference-list">
              {results.results?.map((r,i)=>(
                <div key={i} className="reference-card">
                  <div className="ref-card-header">
                    <span className="ref-badge">{(r.reference_type||"REF").toUpperCase()}</span>
                    <span className="source-domain-badge">{DL[r.domain]||r.domain}</span>
                    <span className="ref-score">Score : {(r.score||0).toFixed(2)}</span>
                  </div>
                  <div className="ref-source"><FileText size={12}/> {r.filename} via {(r.source||"").toUpperCase()}</div>
                  <blockquote className="ref-excerpt">{r.excerpt}</blockquote>
                  {isSafeUrl(r.url) && <a href={r.url} target="_blank" rel="noreferrer" className="ref-link"><ExternalLink size={11}/> Source officielle</a>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
