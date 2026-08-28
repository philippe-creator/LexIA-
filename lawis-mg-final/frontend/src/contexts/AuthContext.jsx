import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { authService, setAccessToken, refreshAccessToken } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Pas de jeton en localStorage à relire : on tente un rafraîchissement
    // silencieux via le cookie httpOnly pour restaurer la session au chargement.
    // refreshAccessToken() est mutualisé : en dev, StrictMode monte cet effet
    // deux fois, mais un seul /auth/refresh part réellement — sinon la rotation
    // du jeton côté API révoquerait celui du premier appel et déconnecterait.
    refreshAccessToken()
      .then(() => authService.me())
      .then((res) => setUser(res.data))
      .catch(() => setAccessToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await authService.login({ email, password });
    setAccessToken(res.data.access_token);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const register = useCallback(async (data) => {
    // Ne connecte plus automatiquement : le compte doit d'abord être confirmé
    // par email (voir api/routes/auth.py /auth/register) — l'appelant reçoit
    // le message de confirmation à afficher, pas un utilisateur connecté.
    const res = await authService.register(data);
    return res.data;
  }, []);

  const loginWithGoogle = useCallback(async (idToken) => {
    const res = await authService.google(idToken);
    setAccessToken(res.data.access_token);
    setUser(res.data.user);
    return res.data.user;
  }, []);

  const logout = useCallback(async () => {
    try { await authService.logout(); } catch {}
    setAccessToken(null);
    setUser(null);
  }, []);

  const updateUser = useCallback((data) => setUser((p) => ({ ...p, ...data })), []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, loginWithGoogle, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
