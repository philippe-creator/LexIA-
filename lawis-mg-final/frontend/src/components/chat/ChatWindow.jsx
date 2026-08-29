import React, { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Send, Plus, Trash2, MessageSquare, Loader2, AlertCircle, CheckCircle2, AlertTriangle, XCircle, BookOpen, ExternalLink, ChevronDown, ChevronUp, ChevronRight, ThumbsUp, ThumbsDown, Mic, Volume2, Square, Download, FileText, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useChat } from "../../hooks/useChat";
import { useSpeechToText, useTextToSpeech } from "../../hooks/useVoice";
import { useAuth } from "../../contexts/AuthContext";
import { useLanguage } from "../../contexts/LanguageContext";
import { exportService, chatService, documentService } from "../../services/api";
import { dateLocale } from "../../i18n/dateLocale";

const CONFIDENCE = {
  "élevé": { icon: CheckCircle2, color: "#16A34A", bg: "#D1FAE5", labelKey: "confidence.high" },
  "moyen": { icon: AlertTriangle, color: "#D97706", bg: "#FEF3C7", labelKey: "confidence.medium" },
  "faible": { icon: AlertCircle, color: "#DC2626", bg: "#FEE2E2", labelKey: "confidence.low" },
  "insuffisant": { icon: XCircle, color: "#6B7280", bg: "#F3F4F6", labelKey: "confidence.insufficient" },
};

const DOMAINS = [
  { value: null, emoji: "⚖️", key: "all" },
  { value: "travail", emoji: "👷", key: "travail" },
  { value: "fiscal", emoji: "🏦", key: "fiscal" },
  { value: "societes", emoji: "🏢", key: "societes" },
  { value: "donnees_personnelles", emoji: "🔒", key: "donnees_personnelles" },
  { value: "penal", emoji: "⚔️", key: "penal" },
  { value: "jurisprudence", emoji: "📚", key: "jurisprudence" },
];

const DOC_TYPES = [
  { value: "", key: "all" },
  { value: "loi", key: "loi" },
  { value: "dahir", key: "dahir" },
  { value: "decret", key: "decret" },
  { value: "arrete", key: "arrete" },
  { value: "circulaire", key: "circulaire" },
  { value: "jurisprudence", key: "jurisprudence" },
  { value: "autre", key: "autre" },
];

// Défense en profondeur : l'API filtre déjà les schémas non http(s), mais on
// ne fait jamais confiance à une seule couche pour un lien cliquable.
const isSafeUrl = (url) => typeof url === "string" && (url.startsWith("http://") || url.startsWith("https://"));

function SourcePanel({ citations, onClose }) {
  const { t } = useTranslation();
  return (
    <aside className="source-panel">
      <div className="source-panel-header"><h3>{t("chat.sourcesTitle")}</h3><button className="source-close" onClick={onClose}><XCircle size={16}/></button></div>
      <div className="source-list">
        {citations.map((c) => (
          <div key={c.index} className="source-card">
            <div className="source-card-top">
              <span className="source-idx">[{c.index}]</span>
              <span className={`source-domain-badge`}>{t(`domain.${c.domain}`, c.domain)}</span>
            </div>
            <div className="source-label">📄 {c.label || c.filename}{c.page ? ` — p. ${c.page}` : ""}</div>
            <blockquote className="source-excerpt">{c.excerpt}</blockquote>
            <div className="source-footer">
              <span className="source-score">{t("chat.relevance")} {Math.round((c.score||0)*100)}%</span>
              {isSafeUrl(c.url) && <a href={c.url} target="_blank" rel="noreferrer" className="source-link"><ExternalLink size={11}/> {t("chat.source")}</a>}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

function MessageBubble({ msg, onCitationClick, onSuggestionClick, onFeedback, onSpeak, speaking, ttsSupported }) {
  const { t } = useTranslation();
  const [showSugg, setShowSugg] = useState(false);
  if (msg.role === "user") return (
    <div className="msg-row user"><div className="msg-bubble user"><p>{msg.content}</p></div></div>
  );
  const cfg = CONFIDENCE[msg.confidence_label] || CONFIDENCE["insuffisant"];
  const Icon = cfg.icon;
  const roleBadgeColor = { etudiant:"#2563EB", particulier:"#16A34A", juriste:"#7C3AED", avocat:"#B45309", entreprise:"#0891B2" }[msg.adapted_for_role];
  // Le marqueur « QUESTIONS SUGGÉRÉES: ... » transite dans le flux de tokens ;
  // on ne l'affiche pas (les questions sont rendues en chips plus bas).
  const displayContent = (msg.content || "").split(/\**\s*QUESTIONS SUGGÉRÉES/i)[0].replace(/[\s*#>-]+$/, "");
  const isTyping = msg.streaming && !displayContent;
  // Le feedback n'a de sens que sur un message assistant réellement persisté :
  // les id temporaires (placeholder de streaming / message optimiste) n'existent
  // pas encore côté serveur, donc pas de POST /feedback possible.
  const canFeedback = !msg.streaming && msg.id && !String(msg.id).startsWith("stream-") && !String(msg.id).startsWith("tmp-");
  if (isTyping) return (
    <div className="msg-row assistant">
      <div className="msg-bubble assistant loading-bubble"><Loader2 size={16} className="spin"/><span>{t("chat.searching")}</span></div>
    </div>
  );
  return (
    <div className="msg-row assistant">
      <div className="msg-bubble assistant">
        {roleBadgeColor && <div className="role-adaptation-badge" style={{color:roleBadgeColor}}><BookOpen size={11}/> {t(`chat.roleBadge.${msg.adapted_for_role}`)}</div>}
        <div className="msg-content"><ReactMarkdown>{displayContent}</ReactMarkdown>{msg.streaming && <span className="stream-cursor">▋</span>}</div>
        {!msg.streaming && <div className="msg-meta">
          {msg.confidence_label && (
            <div className="confidence-badge" style={{background:cfg.bg,color:cfg.color}}>
              <Icon size={12}/> <span>{t(cfg.labelKey)}</span>
            </div>
          )}
          {msg.citations?.length > 0 && (
            <button className="citations-btn" onClick={() => onCitationClick(msg.citations)}>
              <ExternalLink size={12}/> {msg.citations.length} source(s)
            </button>
          )}
          {ttsSupported && displayContent && (
            <button className={`tts-btn ${speaking ? "active" : ""}`} onClick={() => onSpeak(displayContent, msg.id)} aria-label={speaking ? t("chat.stopReading") : t("chat.listenAnswer")} title={speaking ? t("chat.stop") : t("chat.listen")}>
              {speaking ? <Square size={12}/> : <Volume2 size={13}/>}
            </button>
          )}
          {canFeedback && (
            <div className="feedback-group" title={t("chat.feedbackTitle")}>
              <button className={`feedback-btn ${msg.feedback === "up" ? "active up" : ""}`} onClick={() => onFeedback(msg.id, "up")} aria-label={t("chat.usefulAnswer")}><ThumbsUp size={13}/></button>
              <button className={`feedback-btn ${msg.feedback === "down" ? "active down" : ""}`} onClick={() => onFeedback(msg.id, "down")} aria-label={t("chat.uselessAnswer")}><ThumbsDown size={13}/></button>
            </div>
          )}
        </div>}
        {msg.suggested_queries?.length > 0 && (
          <div className="suggestions-block">
            <button className="suggestions-toggle" onClick={() => setShowSugg((p)=>!p)}>
              {showSugg ? <ChevronUp size={13}/> : <ChevronDown size={13}/>} {t("chat.followUpQuestions")}
            </button>
            {showSugg && (
              <div className="suggestions-list">
                {msg.suggested_queries.map((q, i) => (
                  <button key={i} className="suggestion-chip" onClick={() => onSuggestionClick(q)}>
                    <ChevronRight size={12}/> {q}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatWindow() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { messages, conversations, activeConvId, loading, error, sendMessage, sendFeedback, loadConversations, loadConversation, startNewConversation, deleteConversation, setError } = useChat();
  const [input, setInput] = useState("");
  const [domain, setDomain] = useState(null);
  const [docType, setDocType] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [myDocuments, setMyDocuments] = useState([]);
  const { lang } = useLanguage(); // langue de réponse = langue globale de l'interface, plus de réglage séparé
  const [activeCitations, setActiveCitations] = useState([]);
  const [historyQuery, setHistoryQuery] = useState("");
  const [historyResults, setHistoryResults] = useState([]);
  // Historique des conversations : tiroir masqué par défaut sur mobile (sinon
  // ses 240px fixes ne laissent presque plus de place au chat lui-même).
  const [convSidebarOpen, setConvSidebarOpen] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  const handleExport = async (convId, format) => {
    try {
      const r = await exportService[format](convId);
      let blob;
      if (format === "json") {
        const text = await r.data.text();
        blob = new Blob([text], { type: "application/json" });
      } else {
        blob = new Blob([r.data], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `conversation_${convId}.${format}`; a.click();
      URL.revokeObjectURL(url);
    } catch { setError(t("chat.exportFailed")); }
  };

  const searchHistory = async (q) => {
    setHistoryQuery(q);
    if (!q.trim()) { setHistoryResults([]); return; }
    try {
      const r = await chatService.searchHistory(q);
      setHistoryResults(r.data);
    } catch { setHistoryResults([]); }
  };

  // Voix : dictée (la transcription s'ajoute au champ) et lecture à voix haute.
  const { supported: sttSupported, listening, start: startDictation, stop: stopDictation } =
    useSpeechToText(lang, (text) => setInput((prev) => (prev ? prev + " " + text : text)));
  const { supported: ttsSupported, speakingId, speak, cancel: cancelSpeech } = useTextToSpeech();
  const handleSpeak = (text, id) => { if (speakingId === id) cancelSpeech(); else speak(text, lang, id); };

  useEffect(() => { loadConversations(); }, [loadConversations]);
  useEffect(() => {
    documentService.list().then((r) => setMyDocuments((r.data || []).filter((d) => d.status === "indexed"))).catch(() => {});
  }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  const handleSend = async (q = null) => {
    const query = q || input.trim();
    if (!query || loading) return;
    if (listening) stopDictation();
    setInput("");
    await sendMessage({ query, domain, docType, documentId, lang });
  };

  const handleKey = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } };

  return (
    <div className="chat-shell">
      {convSidebarOpen && <div className="mobile-sidebar-backdrop chat-backdrop" onClick={() => setConvSidebarOpen(false)} />}
      <aside className={`conv-sidebar ${convSidebarOpen ? "open" : ""}`}>
        <div className="conv-sidebar-header">
          <button className="new-conv-btn" onClick={() => { startNewConversation(); setConvSidebarOpen(false); }}><Plus size={15}/> {t("chat.newConversation")}</button>
        </div>
        <div style={{padding:"8px 12px", borderBottom:"1px solid var(--border)"}}>
          <input className="chat-textarea" placeholder={t("chat.searchHistoryPlaceholder")} value={historyQuery} onChange={(e) => searchHistory(e.target.value)} style={{fontSize:13, padding:"7px 10px", minHeight:36}}/>
        </div>
        <div className="conv-list">
          {historyQuery && historyResults.length === 0 && <p className="conv-empty">{t("chat.noResults")}</p>}
          {historyQuery && historyResults.map((m) => (
            <div key={m.id} className="conv-item" onClick={() => { loadConversation(m.conversation_id); setConvSidebarOpen(false); }}>
              <MessageSquare size={13} className="conv-icon"/>
              <div className="conv-info">
                <span className="conv-title">{m.content.slice(0, 60)}...</span>
                <span className="conv-date">{t("chat.convPrefix")} {m.conversation_id.slice(0, 8)}... • {new Date(m.created_at).toLocaleDateString(dateLocale(lang))}</span>
              </div>
            </div>
          ))}
          {!historyQuery && conversations.length === 0 ? <p className="conv-empty">{t("chat.noConversations")}</p> :
            !historyQuery && conversations.map((c) => (
              <div key={c.id} className={`conv-item ${c.id === activeConvId ? "active" : ""}`} onClick={() => { loadConversation(c.id); setConvSidebarOpen(false); }}>
                <MessageSquare size={13} className="conv-icon"/>
                <div className="conv-info">
                  <span className="conv-title">{c.title || t("chat.untitled")}</span>
                  <span className="conv-date">{new Date(c.updated_at).toLocaleDateString(dateLocale(lang))}</span>
                </div>
                <div style={{display:"flex",gap:2}}>
                  <button className="conv-delete" onClick={(e) => { e.stopPropagation(); handleExport(c.id, "json"); }} title={t("chat.exportJson")}><Download size={12}/></button>
                  <button className="conv-delete" onClick={(e) => { e.stopPropagation(); handleExport(c.id, "docx"); }} title={t("chat.exportWord")}><BookOpen size={12}/></button>
                  <button className="conv-delete" onClick={(e) => { e.stopPropagation(); deleteConversation(c.id); }}><Trash2 size={12}/></button>
                </div>
              </div>
            ))
          }
        </div>
      </aside>

      <div className="chat-main">
        <div className="chat-domain-bar">
          <button className="conv-sidebar-toggle" onClick={() => setConvSidebarOpen(true)} aria-label={t("chat.historyDrawer")}><MessageSquare size={18}/></button>
          <div className="domain-selector">
            {DOMAINS.map((d) => (
              <button key={String(d.value)} onClick={() => setDomain(d.value)} className={`domain-chip ${domain === d.value ? "active" : ""}`}>
                <span>{d.emoji}</span><span>{t(`domainShort.${d.key}`)}</span>
              </button>
            ))}
          </div>
          <div className="filter-selects">
            <select value={docType || ""} onChange={(e) => setDocType(e.target.value || null)} className="filter-select" title={t("chat.filterDocType")}>
              {DOC_TYPES.map((dt) => <option key={dt.value} value={dt.value}>{t(`docType.${dt.key}`)}</option>)}
            </select>
            {myDocuments.length > 0 && (
              <select value={documentId || ""} onChange={(e) => setDocumentId(e.target.value || null)} className="filter-select" title={t("chat.chatWithDocument")}>
                <option value="">{t("chat.allTexts")}</option>
                {myDocuments.map((d) => <option key={d.id} value={d.id}>📄 {d.filename}</option>)}
              </select>
            )}
          </div>
        </div>

        {documentId && (
          <div className="doc-scope-banner">
            <FileText size={13}/> {t("chat.scopedTo")} {myDocuments.find((d) => d.id === documentId)?.filename} »
            <button onClick={() => setDocumentId(null)} title={t("chat.backToAllTexts")}><X size={13}/></button>
          </div>
        )}

        <div className="messages-area" dir={lang === "ar" ? "rtl" : "ltr"}>
          {messages.length === 0 && (
            <div className="chat-welcome">
              <div className="welcome-icon">⚖️</div>
              <h2>{t("chat.welcomeTitle")}{user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""} !</h2>
              <p>{t("chat.welcomeSubtitle")}</p>
              <div className="welcome-examples">
                {t("chat.exampleQuestions", { returnObjects: true }).map((ex) => (
                  <button key={ex} className="example-question" onClick={() => handleSend(ex)}>{ex}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} onCitationClick={setActiveCitations} onSuggestionClick={(q) => { setInput(q); inputRef.current?.focus(); }} onFeedback={sendFeedback} onSpeak={handleSpeak} speaking={speakingId === msg.id} ttsSupported={ttsSupported} />
          ))}
          {error && (
            <div className="chat-error"><AlertCircle size={15}/> {error}<button onClick={() => setError(null)}>✕</button></div>
          )}
          <div ref={bottomRef}/>
        </div>

        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <textarea ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKey} dir={lang === "ar" ? "rtl" : "ltr"} placeholder={t(lang === "ar" ? "chat.placeholderAr" : "chat.placeholder")} rows={1} className="chat-textarea" disabled={loading}/>
            {sttSupported && (
              <button onClick={() => (listening ? stopDictation() : startDictation())} disabled={loading} className={`chat-mic-btn ${listening ? "listening" : ""}`} title={listening ? t("chat.stopDictation") : t("chat.startDictation")} aria-label={listening ? t("chat.stopDictation") : t("chat.startDictation")}>
                <Mic size={17}/>
              </button>
            )}
            <button onClick={() => handleSend()} disabled={loading || !input.trim()} className="chat-send-btn">
              {loading ? <Loader2 size={17} className="spin"/> : <Send size={17}/>}
            </button>
          </div>
          <p className="chat-disclaimer">{t("chat.disclaimer")}</p>
        </div>
      </div>

      {activeCitations.length > 0 && <SourcePanel citations={activeCitations} onClose={() => setActiveCitations([])}/>}
    </div>
  );
}
