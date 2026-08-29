import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Hash, Search, ExternalLink, Loader2, FileText } from "lucide-react";
import { searchService } from "../services/api";
const EXAMPLES = ["loi 09-08","article 62 code du travail","dahir 1-72-184","CGI 2026","loi 17-95","note circulaire TVA"];
const isSafeUrl = (url) => typeof url === "string" && (url.startsWith("http://") || url.startsWith("https://"));
export default function ReferenceSearch() {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const search = async (q=query) => {
    if(!q.trim()) return;
    setLoading(true); setError(null);
    try { const res=await searchService.reference({reference:q,top_k:5}); setResults(res.data); }
    catch { setError(t("reference.searchError")); }
    finally { setLoading(false); }
  };
  return (
    <div className="reference-container">
      <div className="reference-header"><Hash size={20}/><h2>{t("reference.title")}</h2></div>
      <p className="reference-subtitle">{t("reference.subtitle")}</p>
      <div className="reference-search-bar">
        <input type="text" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key==="Enter"&&search()} placeholder={t("reference.placeholder")} className="reference-input"/>
        <button onClick={()=>search()} disabled={loading||!query.trim()} className="reference-btn">{loading?<Loader2 size={18} className="spin"/>:<Search size={18}/>}</button>
      </div>
      <div className="reference-examples">
        <span className="examples-label">{t("reference.examples")}</span>
        {EXAMPLES.map(ex=><button key={ex} className="example-chip" onClick={()=>{setQuery(ex);search(ex);}}>{ex}</button>)}
      </div>
      {error && <div style={{color:"#DC2626",padding:"10px",background:"#FEF2F2",borderRadius:"7px",marginBottom:"12px"}}>{error}</div>}
      {results && (
        <div>
          {results.references_found?.length>0 && (
            <div className="detected-refs"><span>{t("reference.detectedRefs")}</span>{results.references_found.map(r=><span key={r} className="ref-tag">{r}</span>)}</div>
          )}
          {results.results?.length===0 ? (
            <div className="reference-empty">{t("reference.noResults")}<br/><small>{t("reference.noResultsHint")}</small></div>
          ) : (
            <div className="reference-list">
              {results.results?.map((r,i)=>(
                <div key={i} className="reference-card">
                  <div className="ref-card-header">
                    <span className="ref-badge">{(r.reference_type||"REF").toUpperCase()}</span>
                    <span className="source-domain-badge">{t(`domain.${r.domain}`, r.domain)}</span>
                    <span className="ref-score">{t("reference.score")} {(r.score||0).toFixed(2)}</span>
                  </div>
                  <div className="ref-source"><FileText size={12}/> {r.filename} via {(r.source||"").toUpperCase()}</div>
                  <blockquote className="ref-excerpt">{r.text}</blockquote>
                  {isSafeUrl(r.url) && <a href={r.url} target="_blank" rel="noreferrer" className="ref-link"><ExternalLink size={11}/> {t("reference.officialSource")}</a>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
