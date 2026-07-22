import React, { useState, useRef, useEffect } from "react";
import { Send, Plus, Trash2, MessageSquare, Loader2, AlertCircle, CheckCircle2, AlertTriangle, XCircle, BookOpen, ExternalLink, ChevronDown, ChevronUp, ChevronRight, ThumbsUp, ThumbsDown, Mic, Volume2, Square, Download } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useChat } from "../../hooks/useChat";
import { useSpeechToText, useTextToSpeech } from "../../hooks/useVoice";
import { useAuth } from "../../contexts/AuthContext";
import { exportService } from "../../services/api";

const CONFIDENCE = {
  "élevé": { icon: CheckCircle2, color: "#16A34A", bg: "#D1FAE5", label: "Confiance élevée" },
  "moyen": { icon: AlertTriangle, color: "#D97706", bg: "#FEF3C7", label: "Confiance moyenne" },
  "faible": { icon: AlertCircle, color: "#DC2626", bg: "#FEE2E2", label: "Confiance faible" },
  "insuffisant": { icon: XCircle, color: "#6B7280", bg: "#F3F4F6", label: "Sources insuffisantes" },
};

const ROLE_BADGE = {
  etudiant: { label: "Réponse pédagogique", color: "#2563EB" },
  particulier: { label: "Réponse simplifiée", color: "#16A34A" },
  juriste: { label: "Réponse technique", color: "#7C3AED" },
  avocat: { label: "Analyse juridique", color: "#B45309" },
  entreprise: { label: "Impact opérationnel", color: "#0891B2" },
};

const DOMAINS = [
  { value: null, label: "Tous", emoji: "⚖️" },
  { value: "travail", label: "Travail", emoji: "👷" },
  { value: "fiscal", label: "Fiscal", emoji: "🏦" },
  { value: "societes", label: "Sociétés", emoji: "🏢" },
  { value: "donnees_personnelles", label: "Données", emoji: "🔒" },
  { value: "jurisprudence", label: "Jurisprudence", emoji: "📚" },
];

const DOMAIN_LABELS = { travail:"Droit du travail", fiscal:"Droit fiscal", societes:"Droit des sociétés", donnees_personnelles:"Protection des données", jurisprudence:"Jurisprudence", divers:"Divers" };

const DOC_TYPES = [
  { value: "", label: "Tous types" },
  { value: "loi", label: "Loi" },
  { value: "dahir", label: "Dahir" },
  { value: "decret", label: "Décret" },
  { value: "arrete", label: "Arrêté" },
  { value: "circulaire", label: "Circulaire" },
  { value: "jurisprudence", label: "Jurisprudence" },
  { value: "autre", label: "Autre" },
];

// Défense en profondeur : l'API filtre déjà les schémas non http(s), mais on
// ne fait jamais confiance à une seule couche pour un lien cliquable.
const isSafeUrl = (url) => typeof url === "string" && (url.startsWith("http://") || url.startsWith("https://"));

function SourcePanel({ citations, onClose }) {
  return (
    <aside className="source-panel">
      <div className="source-panel-header"><h3>Sources citées</h3><button className="source-close" onClick={onClose}><XCircle size={16}/></button></div>
      <div className="source-list">
        {citations.map((c) => (
          <div key={c.index} className="source-card">
            <div className="source-card-top">
              <span className="source-idx">[{c.index}]</span>
              <span className={`source-domain-badge`}>{DOMAIN_LABELS[c.domain] || c.domain}</span>
            </div>
            <div className="source-label">📄 {c.label || c.filename}{c.page ? ` — p. ${c.page}` : ""}</div>
            <blockquote className="source-excerpt">{c.excerpt}</blockquote>
            <div className="source-footer">
              <span className="source-score">Pertinence : {Math.round((c.score||0)*100)}%</span>
              {isSafeUrl(c.url) && <a href={c.url} target="_blank" rel="noreferrer" className="source-link"><ExternalLink size={11}/> Source</a>}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

function MessageBubble({ msg, onCitationClick, onSuggestionClick, onFeedback, onSpeak, speaking, ttsSupported }) {
  const [showSugg, setShowSugg] = useState(false);
  if (msg.role === "user") return (
    <div className="msg-row user"><div className="msg-bubble user"><p>{msg.content}</p></div></div>
  );
  const cfg = CONFIDENCE[msg.confidence_label] || CONFIDENCE["insuffisant"];
  const Icon = cfg.icon;
  const roleBadge = msg.adapted_for_role ? ROLE_BADGE[msg.adapted_for_role] : null;
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
      <div className="msg-bubble assistant loading-bubble"><Loader2 size={16} className="spin"/><span>Recherche en cours...</span></div>
    </div>
  );
  return (
    <div className="msg-row assistant">
      <div className="msg-bubble assistant">
        {roleBadge && <div className="role-adaptation-badge" style={{color:roleBadge.color}}><BookOpen size={11}/> {roleBadge.label}</div>}
        <div className="msg-content"><ReactMarkdown>{displayContent}</ReactMarkdown>{msg.streaming && <span className="stream-cursor">▋</span>}</div>
        {!msg.streaming && <div className="msg-meta">
          {msg.confidence_label && (
            <div className="confidence-badge" style={{background:cfg.bg,color:cfg.color}}>
              <Icon size={12}/> <span>{cfg.label}</span>
            </div>
          )}
          {msg.citations?.length > 0 && (
            <button className="citations-btn" onClick={() => onCitationClick(msg.citations)}>
              <ExternalLink size={12}/> {msg.citations.length} source(s)
            </button>
          )}
          {ttsSupported && displayContent && (
            <button className={`tts-btn ${speaking ? "active" : ""}`} onClick={() => onSpeak(displayContent, msg.id)} aria-label={speaking ? "Arrêter la lecture" : "Écouter la réponse"} title={speaking ? "Arrêter" : "Écouter"}>
              {speaking ? <Square size={12}/> : <Volume2 size={13}/>}
            </button>
          )}
          {canFeedback && (
            <div className="feedback-group" title="Cette réponse vous a-t-elle été utile ?">
              <button className={`feedback-btn ${msg.feedback === "up" ? "active up" : ""}`} onClick={() => onFeedback(msg.id, "up")} aria-label="Réponse utile"><ThumbsUp size={13}/></button>
              <button className={`feedback-btn ${msg.feedback === "down" ? "active down" : ""}`} onClick={() => onFeedback(msg.id, "down")} aria-label="Réponse non utile"><ThumbsDown size={13}/></button>
            </div>
          )}
        </div>}
        {msg.suggested_queries?.length > 0 && (
          <div className="suggestions-block">
            <button className="suggestions-toggle" onClick={() => setShowSugg((p)=>!p)}>
              {showSugg ? <ChevronUp size={13}/> : <ChevronDown size={13}/>} Questions de suivi
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
  const { user } = useAuth();
  const { messages, conversations, activeConvId, loading, error, sendMessage, sendFeedback, loadConversations, loadConversation, startNewConversation, deleteConversation, setError } = useChat();
  const [input, setInput] = useState("");
  const [domain, setDomain] = useState(null);
  const [docType, setDocType] = useState(null);
  const [lang, setLang] = useState("fr");
  const [activeCitations, setActiveCitations] = useState([]);
  const [historyQuery, setHistoryQuery] = useState("");
  const [historyResults, setHistoryResults] = useState([]);
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
    } catch { setError("Export impossible."); }
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
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  const handleSend = async (q = null) => {
    const query = q || input.trim();
    if (!query || loading) return;
    if (listening) stopDictation();
    setInput("");
    await sendMessage({ query, domain, docType, lang });
  };

  const handleKey = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } };

  return (
    <div className="chat-shell">
      <aside className="conv-sidebar">
        <div className="conv-sidebar-header">
          <button className="new-conv-btn" onClick={startNewConversation}><Plus size={15}/> Nouvelle conversation</button>
        </div>
        <div style={{padding:"8px 12px", borderBottom:"1px solid var(--border)"}}>
          <input className="chat-textarea" placeholder="Rechercher dans l'historique..." value={historyQuery} onChange={(e) => searchHistory(e.target.value)} style={{fontSize:13, padding:"7px 10px", minHeight:36}}/>
        </div>
        <div className="conv-list">
          {historyQuery && historyResults.length === 0 && <p className="conv-empty">Aucun résultat.</p>}
          {historyQuery && historyResults.map((m) => (
            <div key={m.id} className="conv-item" onClick={() => loadConversation(m.conversation_id)}>
              <MessageSquare size={13} className="conv-icon"/>
              <div className="conv-info">
                <span className="conv-title">{m.content.slice(0, 60)}...</span>
                <span className="conv-date">Conv. {m.conversation_id.slice(0, 8)}... • {new Date(m.created_at).toLocaleDateString("fr-MA")}</span>
              </div>
            </div>
          ))}
          {!historyQuery && conversations.length === 0 ? <p className="conv-empty">Aucune conversation.</p> :
            !historyQuery && conversations.map((c) => (
              <div key={c.id} className={`conv-item ${c.id === activeConvId ? "active" : ""}`} onClick={() => loadConversation(c.id)}>
                <MessageSquare size={13} className="conv-icon"/>
                <div className="conv-info">
                  <span className="conv-title">{c.title || "Sans titre"}</span>
                  <span className="conv-date">{new Date(c.updated_at).toLocaleDateString("fr-MA")}</span>
                </div>
                <div style={{display:"flex",gap:2}}>
                  <button className="conv-delete" onClick={(e) => { e.stopPropagation(); handleExport(c.id, "json"); }} title="Exporter JSON"><Download size={12}/></button>
                  <button className="conv-delete" onClick={(e) => { e.stopPropagation(); handleExport(c.id, "docx"); }} title="Exporter Word"><BookOpen size={12}/></button>
                  <button className="conv-delete" onClick={(e) => { e.stopPropagation(); deleteConversation(c.id); }}><Trash2 size={12}/></button>
                </div>
              </div>
            ))
          }
        </div>
      </aside>

      <div className="chat-main">
        <div className="chat-domain-bar">
          <div className="domain-selector">
            {DOMAINS.map((d) => (
              <button key={String(d.value)} onClick={() => setDomain(d.value)} className={`domain-chip ${domain === d.value ? "active" : ""}`}>
                <span>{d.emoji}</span><span>{d.label}</span>
              </button>
            ))}
          </div>
          <div className="filter-selects">
            <div className="lang-toggle" title="Langue de réponse">
              <button className={`lang-btn ${lang === "fr" ? "active" : ""}`} onClick={() => setLang("fr")}>FR</button>
              <button className={`lang-btn ${lang === "ar" ? "active" : ""}`} onClick={() => setLang("ar")}>ع</button>
            </div>
            <select value={docType || ""} onChange={(e) => setDocType(e.target.value || null)} className="filter-select" title="Filtrer par type de document">
              {DOC_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
        </div>

        <div className="messages-area" dir={lang === "ar" ? "rtl" : "ltr"}>
          {messages.length === 0 && (
            <div className="chat-welcome">
              <div className="welcome-icon">⚖️</div>
              <h2>Bonjour{user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""} !</h2>
              <p>Posez votre question sur le droit marocain. Les réponses sont sourcées et adaptées à votre profil.</p>
              <div className="welcome-examples">
                {["Quels sont les droits du salarié en cas de licenciement ?","Comment déclarer la TVA pour une SARL ?","Quelles sont les obligations liées à la loi 09-08 ?"].map((ex) => (
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
            <textarea ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKey} dir={lang === "ar" ? "rtl" : "ltr"} placeholder={lang === "ar" ? "اطرح سؤالك القانوني..." : "Posez votre question juridique..."} rows={1} className="chat-textarea" disabled={loading}/>
            {sttSupported && (
              <button onClick={() => (listening ? stopDictation() : startDictation())} disabled={loading} className={`chat-mic-btn ${listening ? "listening" : ""}`} title={listening ? "Arrêter la dictée" : "Dicter la question"} aria-label={listening ? "Arrêter la dictée" : "Dicter la question"}>
                <Mic size={17}/>
              </button>
            )}
            <button onClick={() => handleSend()} disabled={loading || !input.trim()} className="chat-send-btn">
              {loading ? <Loader2 size={17} className="spin"/> : <Send size={17}/>}
            </button>
          </div>
          <p className="chat-disclaimer">Les réponses sont informatives et basées sur les textes officiels indexés. Elles ne constituent pas un avis juridique professionnel.</p>
        </div>
      </div>

      {activeCitations.length > 0 && <SourcePanel citations={activeCitations} onClose={() => setActiveCitations([])}/>}
    </div>
  );
}
