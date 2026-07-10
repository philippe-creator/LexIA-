import { useState, useCallback } from "react";
import { chatService } from "../services/api";

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadConversations = useCallback(async () => {
    try {
      const res = await chatService.listConversations();
      setConversations(res.data);
    } catch {}
  }, []);

  const loadConversation = useCallback(async (convId) => {
    try {
      const res = await chatService.getConversation(convId);
      setActiveConvId(convId);
      setMessages(res.data.messages.map((m) => ({
        id: m.id, role: m.role, content: m.content,
        citations: m.citations || [], confidence_score: m.confidence_score,
        created_at: m.created_at,
      })));
    } catch { setError("Impossible de charger la conversation."); }
  }, []);

  const startNewConversation = useCallback(() => {
    setActiveConvId(null); setMessages([]); setError(null);
  }, []);

  const sendMessage = useCallback(async ({ query, domain, top_k = 5, adapt_to_profile = true }) => {
    if (!query.trim() || loading) return;
    const userMsg = { id: `tmp-${Date.now()}`, role: "user", content: query, citations: [], created_at: new Date().toISOString() };
    const assistantId = `stream-${Date.now()}`;
    const assistantMsg = { id: assistantId, role: "assistant", content: "", citations: [], streaming: true, created_at: new Date().toISOString() };
    setMessages((p) => [...p, userMsg, assistantMsg]);
    setLoading(true); setError(null);

    const patch = (id, fields) => setMessages((p) => p.map((m) => (m.id === id ? { ...m, ...fields } : m)));
    const dropPlaceholders = () => setMessages((p) => p.filter((m) => m.id !== assistantId && m.id !== userMsg.id));

    try {
      await chatService.stream(
        { query, conversation_id: activeConvId, domain: domain || null, top_k, adapt_to_profile },
        {
          onMeta: (m) => {
            if (!activeConvId) { setActiveConvId(m.conversation_id); loadConversations(); }
            patch(assistantId, {
              citations: m.citations || [], confidence_score: m.confidence_score,
              confidence_label: m.confidence_label, domains_searched: m.domains_searched,
              adapted_for_role: m.adapted_for_role,
            });
          },
          onToken: (t) => setMessages((p) => p.map((m) => (m.id === assistantId ? { ...m, content: m.content + t } : m))),
          onDone: (d) => patch(assistantId, {
            id: d.message_id || assistantId, streaming: false,
            suggested_queries: d.suggested_queries || [],
          }),
          onError: (detail) => { setError(detail || "Erreur lors de la recherche."); dropPlaceholders(); },
        }
      );
    } catch (e) {
      setError("Erreur lors de la recherche.");
      dropPlaceholders();
    } finally { setLoading(false); }
  }, [activeConvId, loading, loadConversations]);

  const deleteConversation = useCallback(async (convId) => {
    try {
      await chatService.deleteConversation(convId);
      setConversations((p) => p.filter((c) => c.id !== convId));
      if (activeConvId === convId) startNewConversation();
    } catch { setError("Impossible de supprimer."); }
  }, [activeConvId, startNewConversation]);

  return { messages, conversations, activeConvId, loading, error, sendMessage, loadConversations, loadConversation, startNewConversation, deleteConversation, setError };
}
