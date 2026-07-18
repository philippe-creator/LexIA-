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
        confidence_label: m.confidence_label, feedback: m.feedback || null,
        created_at: m.created_at,
      })));
    } catch { setError("Impossible de charger la conversation."); }
  }, []);

  const startNewConversation = useCallback(() => {
    setActiveConvId(null); setMessages([]); setError(null);
  }, []);

  const sendMessage = useCallback(async ({ query, domain, docType, year, lang = "fr", top_k = 5, adapt_to_profile = true }) => {
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
        { query, conversation_id: activeConvId, domain: domain || null, doc_type: docType || null, year: year || null, lang, top_k, adapt_to_profile },
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

  const sendFeedback = useCallback(async (messageId, feedback) => {
    // Bascule optimiste : recliquer sur le même pouce annule (null). On calcule
    // `next` AVANT setMessages (pas dans l'updater) : un updater doit être pur,
    // et React StrictMode le double-invoque — y calculer une valeur à envoyer au
    // serveur donnait un résultat corrompu au 2e passage.
    const current = messages.find((m) => m.id === messageId)?.feedback ?? null;
    const next = current === feedback ? null : feedback;
    setMessages((p) => p.map((m) => (m.id === messageId ? { ...m, feedback: next } : m)));
    try {
      await chatService.sendFeedback(messageId, next);
    } catch {
      // En cas d'échec réseau, on recharge la conversation pour resynchroniser l'état.
      if (activeConvId) loadConversation(activeConvId);
    }
  }, [messages, activeConvId, loadConversation]);

  const deleteConversation = useCallback(async (convId) => {
    try {
      await chatService.deleteConversation(convId);
      setConversations((p) => p.filter((c) => c.id !== convId));
      if (activeConvId === convId) startNewConversation();
    } catch { setError("Impossible de supprimer."); }
  }, [activeConvId, startNewConversation]);

  return { messages, conversations, activeConvId, loading, error, sendMessage, sendFeedback, loadConversations, loadConversation, startNewConversation, deleteConversation, setError };
}
