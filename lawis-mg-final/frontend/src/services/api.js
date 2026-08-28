import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

// FastAPI renvoie `detail` comme une simple chaîne pour la plupart des erreurs
// (HTTPException), mais comme un TABLEAU d'objets {type,loc,msg,input,ctx}
// pour les erreurs de validation Pydantic (422) — rendre cette forme
// directement dans du JSX plante React ("Objects are not valid as a React
// child"). Ce helper normalise les deux cas en une chaîne lisible.
export function extractErrorMessage(err, fallback = "Une erreur s'est produite.") {
  const detail = err?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail.map((d) => d?.msg).filter(Boolean);
    return msgs.length ? msgs.join(" ") : fallback;
  }
  return fallback;
}

// Le jeton d'accès ne vit qu'en mémoire (jamais dans localStorage) : un XSS
// ne peut plus l'exfiltrer via localStorage.getItem(). Le refresh token, lui,
// vit dans un cookie httpOnly posé par l'API — invisible à ce module aussi.
let accessToken = null;
export const setAccessToken = (token) => { accessToken = token; };
export const getAccessToken = () => accessToken;

// L'API fait tourner le refresh token (l'ancien est révoqué à chaque appel).
// Deux /auth/refresh concurrents avec le même cookie sont donc fatals : le
// premier réussit et révoque le jeton, le second reçoit 401 et déconnecte
// l'utilisateur. Cela arrive dès que plusieurs requêtes reçoivent 401 en même
// temps — et systématiquement en dev, React.StrictMode montant les effets deux
// fois. On mutualise donc UNE seule requête de refresh entre tous les appelants
// concurrents ("single-flight") : un seul appel réseau, un seul jeton consommé.
let refreshPromise = null;
export const refreshAccessToken = () => {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${BASE_URL}/auth/refresh`, {}, { withCredentials: true })
      .then((res) => { setAccessToken(res.data.access_token); return res.data.access_token; })
      .finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
};

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
  withCredentials: true, // envoie/reçoit le cookie refresh_token httpOnly
});

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry && original.url !== "/auth/refresh") {
      original._retry = true;
      try {
        const token = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      } catch {
        setAccessToken(null);
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;

export const authService = {
  login: (d) => api.post("/auth/login", d),
  register: (d) => api.post("/auth/register", d),
  logout: () => api.post("/auth/logout"),
  refresh: () => api.post("/auth/refresh"),
  me: () => api.get("/auth/me"),
  updateProfile: (d) => api.patch("/auth/me", d),
  changePassword: (d) => api.post("/auth/change-password", d),
  forgotPassword: (email) => api.post("/auth/forgot-password", { email }),
  resetPassword: (token, new_password) => api.post("/auth/reset-password", { token, new_password }),
  google: (id_token) => api.post("/auth/google", { id_token }),
  verifyEmail: (token) => api.post("/auth/verify-email", { token }),
  resendVerification: (email) => api.post("/auth/resend-verification", { email }),
};

export const chatService = {
  send: (d) => api.post("/chat/", d),
  demo: (query) => api.post("/chat/demo", { query }),
  listConversations: (limit = 20, offset = 0) => api.get(`/chat/conversations?limit=${limit}&offset=${offset}`),
  getConversation: (id, limit = 50, offset = 0) => api.get(`/chat/conversations/${id}?limit=${limit}&offset=${offset}`),
  deleteConversation: (id) => api.delete(`/chat/conversations/${id}`),
  sendFeedback: (messageId, feedback) => api.post(`/chat/messages/${messageId}/feedback`, { feedback }),
  searchHistory: (q, limit = 20) => api.get(`/chat/search-history?q=${encodeURIComponent(q)}&limit=${limit}`),

  // Streaming SSE via fetch (axios ne gère pas les flux ReadableStream).
  // handlers : { onMeta, onToken, onDone, onError }
  stream: async (payload, handlers = {}) => {
    const doFetch = (token) =>
      fetch(`${BASE_URL}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        credentials: "include",
        body: JSON.stringify(payload),
      });

    let res = await doFetch(getAccessToken());
    if (res.status === 401) {
      // Une tentative de refresh, comme l'intercepteur axios (mutualisée).
      try {
        res = await doFetch(await refreshAccessToken());
      } catch {
        setAccessToken(null);
        window.location.href = "/login";
        return;
      }
    }
    if (!res.ok || !res.body) {
      let detail = "Erreur lors de la recherche.";
      try { detail = (await res.json()).detail || detail; } catch { /* corps non-JSON */ }
      handlers.onError?.(detail);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || ""; // conserver un éventuel événement incomplet
      for (const evt of events) {
        const dataLine = evt.split("\n").find((l) => l.startsWith("data:"));
        if (!dataLine) continue;
        let obj;
        try { obj = JSON.parse(dataLine.slice(5).trim()); } catch { continue; }
        if (obj.type === "meta") handlers.onMeta?.(obj);
        else if (obj.type === "token") handlers.onToken?.(obj.content);
        else if (obj.type === "done") handlers.onDone?.(obj);
        else if (obj.type === "error") handlers.onError?.(obj.detail);
      }
    }
  },
};

export const searchService = {
  search: (d) => api.post("/search/", d),
  stats: () => api.get("/search/stats"),
  reference: (d) => api.post("/reference/", d),
};

export const watchService = {
  status: () => api.get("/watch/status"),
  trigger: () => api.post("/watch/trigger"),
  recentTexts: () => api.get("/search/recent-texts"),
};

export const compareService = {
  versions: (domain) => api.get(`/compare/versions/${domain}`),
  compare: (d) => api.post("/compare/", d),
};

export const adminService = {
  overview: () => api.get("/admin/overview"),
  listUsers: () => api.get("/admin/users"),
  promote: (userId) => api.post(`/admin/users/${userId}/promote`),
  demote: (userId) => api.post(`/admin/users/${userId}/demote`),
};

export const calculatorService = {
  severancePay: (d) => api.post("/calculators/severance-pay", d),
  noticePeriod: (d) => api.post("/calculators/notice-period", d),
  netSalary: (d) => api.post("/calculators/net-salary", d),
};

export const exportService = {
  json: (convId) => api.get(`/export/conversations/${convId}/json`, { responseType: "blob" }),
  docx: (convId) => api.get(`/export/conversations/${convId}/docx`, { responseType: "blob" }),
};



export const notificationService = {
  list: (params = {}) => api.get("/notifications/", { params }),
  unreadCount: () => api.get("/notifications/unread-count"),
  markRead: (id) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post("/notifications/read-all"),
};

export const legalDocumentService = {
  types: () => api.get("/legal-documents/types"),
  preview: (docType, data) => api.post(`/legal-documents/${docType}/preview`, { data }),
  download: (docType, data, format) =>
    api.post(`/legal-documents/${docType}/download?format=${format}`, { data }, { responseType: "blob" }),
};

export const documentService = {
  list: () => api.get("/documents/"),
  // L'instance `api` a Content-Type: application/json par défaut. Avec un
  // FormData, axios sérialise alors le corps en JSON (formToJSON) au lieu de
  // l'envoyer tel quel — le fichier est perdu. `Content-Type: undefined`
  // retire ce défaut pour laisser le navigateur fixer lui-même le boundary
  // multipart/form-data correct.
  // Un PDF scanné (OCR) peut prendre plusieurs minutes à traiter — bien au-delà
  // du timeout global de 60s de l'instance `api`, qui abandonnait la requête
  // (l'utilisateur voyait "Erreur upload." alors que le serveur finissait par
  // indexer le document avec succès en arrière-plan).
  upload: (fd) => api.post("/documents/upload", fd, { headers: { "Content-Type": undefined }, timeout: 600000 }),
  audit: (id) => api.post(`/documents/${id}/audit`, {}, { timeout: 90000 }),
  delete: (id) => api.delete(`/documents/${id}`),
};
