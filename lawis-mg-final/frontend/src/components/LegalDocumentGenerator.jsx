import React, { useState, useEffect } from "react";
import { FileText, Download, FileType, Eye, AlertCircle } from "lucide-react";
import { legalDocumentService } from "../services/api";

// Rend un bloc de la trame renvoyée par l'API dans l'aperçu à l'écran.
function PreviewBlock({ block }) {
  const { style, text } = block;
  if (style === "spacer") return <div style={{ height: 10 }} />;
  if (style === "title") return <h3 className="legaldoc-preview-title">{text}</h3>;
  if (style === "subtitle") return <p className="legaldoc-preview-subtitle">{text}</p>;
  if (style === "heading") return <p className="legaldoc-preview-heading">{text}</p>;
  if (style === "note") return <p className="legaldoc-preview-note">{text}</p>;
  const align = style === "body_center" ? "center" : style === "body_right" ? "right" : "justify";
  return <p className="legaldoc-preview-body" style={{ textAlign: align }}>{text}</p>;
}

function Field({ field, value, onChange }) {
  const common = {
    className: "select-input",
    value: value || "",
    onChange: (e) => onChange(field.name, e.target.value),
    placeholder: field.placeholder || "",
  };
  return (
    <div className="selector-group">
      <label>{field.label}{field.required && <span className="legaldoc-req"> *</span>}</label>
      {field.type === "textarea" ? (
        <textarea rows={3} {...common} />
      ) : field.type === "select" ? (
        <select {...common}>
          {field.options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"} {...common} />
      )}
    </div>
  );
}

export default function LegalDocumentGenerator() {
  const [types, setTypes] = useState([]);
  const [activeKey, setActiveKey] = useState(null);
  const [formData, setFormData] = useState({});
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(null);

  useEffect(() => {
    legalDocumentService.types()
      .then((res) => {
        setTypes(res.data.types);
        if (res.data.types.length) selectType(res.data.types[0]);
      })
      .catch(() => setError("Impossible de charger les modèles de documents."));
  }, []); // eslint-disable-line

  const activeType = types.find((t) => t.key === activeKey);

  const selectType = (t) => {
    setActiveKey(t.key);
    // Les champs select affichent leur 1re option par défaut : on l'inscrit dans
    // l'état pour qu'elle soit envoyée même si l'utilisateur n'y touche pas.
    const initial = {};
    t.fields.forEach((f) => {
      if (f.type === "select" && f.options?.length) initial[f.name] = f.options[0];
    });
    setFormData(initial);
    setPreview(null);
    setError(null);
  };

  const handleChange = (name, value) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    setPreview(null); // toute modification invalide l'aperçu précédent
  };

  const doPreview = async () => {
    setError(null); setLoading(true);
    try {
      const res = await legalDocumentService.preview(activeKey, formData);
      setPreview(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Erreur lors de la génération.");
    } finally { setLoading(false); }
  };

  const doDownload = async (format) => {
    setError(null); setDownloading(format);
    try {
      const res = await legalDocumentService.download(activeKey, formData, format);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${activeKey}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      // Le corps d'erreur est un blob JSON quand la requête échoue.
      let detail = "Erreur lors du téléchargement.";
      try { detail = JSON.parse(await e.response?.data?.text())?.detail || detail; } catch { /* noop */ }
      setError(detail);
    } finally { setDownloading(null); }
  };

  return (
    <div className="compare-container">
      <div className="compare-header"><FileText size={20} /><h2>Générateur de documents juridiques</h2></div>
      <p className="compare-subtitle">
        Trames conformes au Code du travail marocain (loi 65-99). Remplissez les champs, prévisualisez, puis exportez en Word ou PDF — à faire relire par un professionnel avant usage.
      </p>

      <div className="calc-tabs">
        {types.map((t) => (
          <button key={t.key} className={`domain-chip ${activeKey === t.key ? "active" : ""}`} onClick={() => selectType(t)}>
            <FileText size={14} /><span>{t.label}</span>
          </button>
        ))}
      </div>

      {activeType && (
        <div className="legaldoc-layout">
          <div className="legaldoc-form">
            <div className="legaldoc-ref"><AlertCircle size={13} /> {activeType.legal_reference}</div>
            <div className="calc-fields legaldoc-fields">
              {activeType.fields.map((f) => (
                <Field key={f.name} field={f} value={formData[f.name]} onChange={handleChange} />
              ))}
            </div>
            <div className="legaldoc-actions">
              <button className="compare-btn" onClick={doPreview} disabled={loading}>
                <Eye size={15} /> {loading ? "Génération..." : "Aperçu"}
              </button>
              <button className="legaldoc-dl-btn" onClick={() => doDownload("docx")} disabled={!!downloading}>
                <Download size={15} /> {downloading === "docx" ? "..." : "Word (.docx)"}
              </button>
              <button className="legaldoc-dl-btn" onClick={() => doDownload("pdf")} disabled={!!downloading}>
                <FileType size={15} /> {downloading === "pdf" ? "..." : "PDF"}
              </button>
            </div>
            {error && <div className="calc-error">{error}</div>}
          </div>

          <div className="legaldoc-preview">
            {preview ? (
              <div className="legaldoc-preview-sheet">
                {preview.blocks.map((b, i) => <PreviewBlock key={i} block={b} />)}
              </div>
            ) : (
              <div className="legaldoc-preview-empty">
                <FileText size={32} />
                <p>Remplissez le formulaire puis cliquez sur « Aperçu » pour visualiser le document.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
