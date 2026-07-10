import React, { useState, useEffect, useRef } from "react";
import { Upload, Trash2, FileText, CheckCircle, AlertCircle, Clock, Loader2 } from "lucide-react";
import { documentService } from "../services/api";
const STATUS = { pending:{icon:Clock,color:"#D97706",label:"En attente"}, processing:{icon:Loader2,color:"#2563EB",label:"Traitement..."}, indexed:{icon:CheckCircle,color:"#16A34A",label:"Indexé"}, error:{icon:AlertCircle,color:"#DC2626",label:"Erreur"} };
const DOMAINS = ["divers","travail","fiscal","societes","donnees_personnelles","jurisprudence"];
export default function DocumentsPage() {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [domain, setDomain] = useState("divers");
  const fileRef = useRef();
  useEffect(() => { documentService.list().then(r=>setDocs(r.data)).catch(()=>{}); }, []);
  const handleUpload = async (e) => {
    const file=e.target.files[0]; if(!file) return;
    setUploading(true); setError(null);
    const fd=new FormData(); fd.append("file",file); fd.append("domain",domain);
    try { await documentService.upload(fd); const r=await documentService.list(); setDocs(r.data); }
    catch(err) { setError(err.response?.data?.detail||"Erreur upload."); }
    finally { setUploading(false); }
  };
  const handleDelete = async (id) => {
    if(!window.confirm("Supprimer ?")) return;
    await documentService.delete(id); setDocs(p=>p.filter(d=>d.id!==id));
  };
  return (
    <div className="page-container">
      <div className="page-header"><h1>Mes documents</h1><p>Uploadez vos PDFs pour les interroger via le chatbot.</p></div>
      <div className="upload-zone">
        <div className="upload-zone-inner">
          <Upload size={30} className="upload-icon"/>
          <h3>Importer un document</h3>
          <p>PDF, Word, TXT — max 50MB</p>
          <div className="upload-controls">
            <select value={domain} onChange={e=>setDomain(e.target.value)} className="form-input upload-domain">
              {DOMAINS.map(d=><option key={d} value={d}>{d}</option>)}
            </select>
            <button className="btn-primary" onClick={()=>fileRef.current?.click()} disabled={uploading}>
              {uploading?<><Loader2 size={14} className="spin"/> Upload...</>:"Choisir un fichier"}
            </button>
            <input ref={fileRef} type="file" accept=".pdf,.doc,.docx,.txt,.html" onChange={handleUpload} style={{display:"none"}}/>
          </div>
          {error && <div className="upload-error"><AlertCircle size={13}/> {error}</div>}
        </div>
      </div>
      <div className="docs-list">
        {docs.length===0 ? <div className="docs-empty"><FileText size={30}/><p>Aucun document importé.</p></div> :
          docs.map(doc=>{
            const cfg=STATUS[doc.status]||STATUS.pending; const Icon=cfg.icon;
            return (
              <div key={doc.id} className="doc-card">
                <div className="doc-icon"><FileText size={19}/></div>
                <div className="doc-info">
                  <span className="doc-name">{doc.filename}</span>
                  <span className="doc-meta">{doc.domain} • {Math.round(doc.file_size/1024)}KB • {doc.chunk_count} chunks</span>
                </div>
                <div className="doc-status" style={{color:cfg.color}}><Icon size={13} className={doc.status==="processing"?"spin":""}/> {cfg.label}</div>
                <button className="doc-delete" onClick={()=>handleDelete(doc.id)}><Trash2 size={13}/></button>
              </div>
            );
          })
        }
      </div>
    </div>
  );
}
