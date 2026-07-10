import React, { useState, useRef, useEffect } from "react";
import { Send, Plus, Trash2, MessageSquare, Loader2, AlertCircle, CheckCircle2, AlertTriangle, XCircle, BookOpen, ExternalLink, ChevronDown, ChevronUp, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useChat } from "../../hooks/useChat";
import { useAuth } from "../../contexts/AuthContext";

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
            <div className="source-label">📄 {c.label || c.filename}</div>
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

function MessageBubble({ msg, onCitationClick, onSuggestionClick }) {
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
              <Icon size={12}/> <span>{cfg.label} ({Math.round((msg.confidence_score||0)*100)}%)</span>
            </div>
          )}
          {msg.citations?.length > 0 && (
            <button className="citations-btn" onClick={() => onCitationClick(msg.citations)}>
              <ExternalLink size={12}/> {msg.citations.length} source(s)
            </button>
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
  const { messages, conversations, activeConvId, loading, error, sendMessage, loadConversations, loadConversation, startNewConversation, deleteConversation, setError } = useChat();
  const [input, setInput] = useState("");
  const [domain, setDomain] = useState(null);
  const [activeCitations, setActiveCitations] = useState([]);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { loadConversations(); }, [loadConversations]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  const handleSend = async (q = null) => {
    const query = q || input.trim();
    if (!query || loading) return;
    setInput("");
    await sendMessage({ query, domain });
  };

  const handleKey = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } };

  return (
    <div className="chat-shell">
      <aside className="conv-sidebar">
        <div className="conv-sidebar-header">
          <button className="new-conv-btn" onClick={startNewConversation}><Plus size={15}/> Nouvelle conversation</button>
        </div>
        <div className="conv-list">
          {conversations.length === 0 ? <p className="conv-empty">Aucune conversation.</p> :
            conversations.map((c) => (
              <div key={c.id} className={`conv-item ${c.id === activeConvId ? "active" : ""}`} onClick={() => loadConversation(c.id)}>
                <MessageSquare size={13} className="conv-icon"/>
                <div className="conv-info">
                  <span className="conv-title">{c.title || "Sans titre"}</span>
                  <span className="conv-date">{new Date(c.updated_at).toLocaleDateString("fr-MA")}</span>
                </div>
                <button className="conv-delete" onClick={(e) => { e.stopPropagation(); deleteConversation(c.id); }}><Trash2 size={12}/></button>
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
        </div>

        <div className="messages-area">
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
            <MessageBubble key={msg.id} msg={msg} onCitationClick={setActiveCitations} onSuggestionClick={(q) => { setInput(q); inputRef.current?.focus(); }} />
          ))}
          {error && (
            <div className="chat-error"><AlertCircle size={15}/> {error}<button onClick={() => setError(null)}>✕</button></div>
          )}
          <div ref={bottomRef}/>
        </div>

        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <textarea ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKey} placeholder="Posez votre question juridique..." rows={1} className="chat-textarea" disabled={loading}/>
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
