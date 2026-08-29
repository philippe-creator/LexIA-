import { useState, useRef, useCallback, useEffect } from "react";

// Codes de langue pour l'API Web Speech (reconnaissance + synthèse).
const SPEECH_LANG = { fr: "fr-FR", en: "en-US", ar: "ar-SA" };

const SpeechRecognition =
  typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

/**
 * Dictée vocale (speech-to-text) via l'API Web Speech du navigateur.
 * `onResult(text)` est appelé avec la transcription finale.
 * Aucun appel réseau : tout se fait dans le navigateur (Chrome/Edge).
 */
export function useSpeechToText(lang, onResult) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);
  const onResultRef = useRef(onResult);
  onResultRef.current = onResult;

  const supported = !!SpeechRecognition;

  const stop = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* déjà arrêté */ }
    }
    setListening(false);
  }, []);

  const start = useCallback(() => {
    if (!supported || listening) return;
    const rec = new SpeechRecognition();
    rec.lang = SPEECH_LANG[lang] || SPEECH_LANG.fr;
    rec.interimResults = false;
    rec.continuous = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e) => {
      const text = e.results?.[0]?.[0]?.transcript || "";
      if (text) onResultRef.current?.(text);
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recognitionRef.current = rec;
    try { rec.start(); setListening(true); } catch { setListening(false); }
  }, [supported, listening, lang]);

  // Nettoyage si le composant est démonté pendant l'écoute.
  useEffect(() => () => { try { recognitionRef.current?.abort(); } catch {} }, []);

  return { supported, listening, start, stop };
}

/**
 * Lecture à voix haute (text-to-speech) via speechSynthesis.
 * `speak(text, lang)` lit le texte ; `cancel()` arrête. Un seul énoncé à la fois.
 */
export function useTextToSpeech() {
  const [speakingId, setSpeakingId] = useState(null);
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;

  const cancel = useCallback(() => {
    if (supported) window.speechSynthesis.cancel();
    setSpeakingId(null);
  }, [supported]);

  const speak = useCallback((text, lang, id) => {
    if (!supported || !text) return;
    window.speechSynthesis.cancel(); // stoppe toute lecture en cours
    const u = new SpeechSynthesisUtterance(text);
    u.lang = SPEECH_LANG[lang] || SPEECH_LANG.fr;
    u.rate = 1;
    u.onend = () => setSpeakingId(null);
    u.onerror = () => setSpeakingId(null);
    setSpeakingId(id ?? "current");
    window.speechSynthesis.speak(u);
  }, [supported]);

  // Coupe la synthèse si le composant disparaît.
  useEffect(() => () => { if (supported) window.speechSynthesis.cancel(); }, [supported]);

  return { supported, speakingId, speak, cancel };
}
