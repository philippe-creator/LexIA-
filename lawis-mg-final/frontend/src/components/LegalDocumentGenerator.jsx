import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { FileText, Download, FileType, Eye, AlertCircle } from "lucide-react";
import { legalDocumentService, extractErrorMessage } from "../services/api";
import { useLanguage } from "../contexts/LanguageContext";

// Rend un bloc de la trame renvoyée par l'API dans l'aperçu à l'écran.
function PreviewBlock({ block, rtl }) {
  const { style, text } = block;
  if (style === "spacer") return <div style={{ height: 10 }} />;
  if (style === "title") return <h3 className="legaldoc-preview-title">{text}</h3>;
  if (style === "subtitle") return <p className="legaldoc-preview-subtitle">{text}</p>;
  if (style === "heading") return <p className="legaldoc-preview-heading">{text}</p>;
  if (style === "note") return <p className="legaldoc-preview-note">{text}</p>;
  let align = style === "body_center" ? "center" : style === "body_right" ? "right" : "justify";
  if (rtl && align === "justify") align = "right";
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
          {field.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      ) : (
        <input type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"} {...common} />
      )}
    </div>
  );
}

const DOC_LANGS = ["fr", "en", "ar"];

export default function LegalDocumentGenerator() {
  const { t } = useTranslation();
  const { lang } = useLanguage();
  const [docLang, setDocLang] = useState(lang);
  const [types, setTypes] = useState([]);
  const [activeKey, setActiveKey] = useState(null);
  const [formData, setFormData] = useState({});
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(null);

  // La langue du document suit la langue globale par défaut, mais reste
  // modifiable indépendamment : la langue d'un contrat est un choix
  // juridique, pas seulement une préférence d'affichage.
  useEffect(() => { setDocLang(lang); }, [lang]);

  useEffect(() => {
    legalDocumentService.types(docLang)
      .then((res) => {
        setTypes(res.data.types);
        setPreview(null);
        // Les libellés changent de langue mais les noms de champs et les
        // valeurs internes des options ("cadre", "oui"...) restent stables :
        // on ne réinitialise pas la saisie déjà en cours de l'utilisateur.
        const current = res.data.types.find((tp) => tp.key === activeKey) || res.data.types[0];
        if (current && !activeKey) selectType(current);
        else if (current) setActiveKey(current.key);
      })
      .catch(() => setError(t("legalDoc.loadError")));
  }, [docLang]); // eslint-disable-line

  const activeType = types.find((tp) => tp.key === activeKey);

  const selectType = (tp) => {
    setActiveKey(tp.key);
    // Les champs select affichent leur 1re option par défaut : on l'inscrit dans
    // l'état pour qu'elle soit envoyée même si l'utilisateur n'y touche pas.
    const initial = {};
    tp.fields.forEach((f) => {
      if (f.type === "select" && f.options?.length) initial[f.name] = f.options[0].value;
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
      const res = await legalDocumentService.preview(activeKey, formData, docLang);
      setPreview(res.data);
    } catch (e) {
      setError(extractErrorMessage(e, t("legalDoc.generateError")));
    } finally { setLoading(false); }
  };

  const doDownload = async (format) => {
    setError(null); setDownloading(format);
    try {
      const res = await legalDocumentService.download(activeKey, formData, format, docLang);
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
      let detail = t("legalDoc.downloadError");
      try { detail = JSON.parse(await e.response?.data?.text())?.detail || detail; } catch { /* noop */ }
      setError(detail);
    } finally { setDownloading(null); }
  };

  const rtl = docLang === "ar";

  return (
    <div className="compare-container">
      <div className="compare-header"><FileText size={20} /><h2>{t("legalDoc.title")}</h2></div>
      <p className="compare-subtitle">{t("legalDoc.subtitle")}</p>

      <div className="calc-tabs">
        {types.map((tp) => (
          <button key={tp.key} className={`domain-chip ${activeKey === tp.key ? "active" : ""}`} onClick={() => selectType(tp)}>
            <FileText size={14} /><span>{tp.label}</span>
          </button>
        ))}
      </div>

      {activeType && (
        <div className="legaldoc-layout">
          <div className="legaldoc-form">
            <div className="selector-group">
              <label>{t("legalDoc.documentLanguage")}</label>
              <select className="select-input" value={docLang} onChange={(e) => setDocLang(e.target.value)}>
                {DOC_LANGS.map((l) => <option key={l} value={l}>{t(`language.${l}`)}</option>)}
              </select>
            </div>
            <div className="legaldoc-ref"><AlertCircle size={13} /> {activeType.legal_reference}</div>
            <div className="calc-fields legaldoc-fields">
              {activeType.fields.map((f) => (
                <Field key={f.name} field={f} value={formData[f.name]} onChange={handleChange} />
              ))}
            </div>
            <div className="legaldoc-actions">
              <button className="compare-btn" onClick={doPreview} disabled={loading}>
                <Eye size={15} /> {loading ? t("legalDoc.generating") : t("legalDoc.preview")}
              </button>
              <button className="legaldoc-dl-btn" onClick={() => doDownload("docx")} disabled={!!downloading}>
                <Download size={15} /> {downloading === "docx" ? t("legalDoc.downloading") : "Word (.docx)"}
              </button>
              <button className="legaldoc-dl-btn" onClick={() => doDownload("pdf")} disabled={!!downloading}>
                <FileType size={15} /> {downloading === "pdf" ? t("legalDoc.downloading") : "PDF"}
              </button>
            </div>
            {error && <div className="calc-error">{error}</div>}
          </div>

          <div className="legaldoc-preview">
            {preview ? (
              <div className="legaldoc-preview-sheet" dir={rtl ? "rtl" : "ltr"}>
                {preview.blocks.map((b, i) => <PreviewBlock key={i} block={b} rtl={rtl} />)}
              </div>
            ) : (
              <div className="legaldoc-preview-empty">
                <FileText size={32} />
                <p>{t("legalDoc.emptyPreview")}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
