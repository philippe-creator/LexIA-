import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import "./i18n";
import { LanguageProvider } from "./contexts/LanguageContext";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import CookieBanner from "./components/CookieBanner";
import { trackPageview } from "./services/analytics";
import Layout from "./components/layout/Layout";
import LandingPage from "./pages/LandingPage";
import AuthPage from "./pages/AuthPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import PrivacyPage from "./pages/PrivacyPage";
import TermsPage from "./pages/TermsPage";
import ChatPage from "./pages/ChatPage";
import ReferencePage from "./pages/ReferencePage";
import ComparePage from "./pages/ComparePage";
import CalculatorsPage from "./pages/CalculatorsPage";
import LegalDocumentsPage from "./pages/LegalDocumentsPage";

import DashboardPage from "./pages/DashboardPage";
import DocumentsPage from "./pages/DocumentsPage";
import ProfilePage from "./pages/ProfilePage";
import "./App.css";

function ProtectedRoute({ children, requireRole }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="app-loader"><div className="spinner"/></div>;
  if (!user) return <Navigate to="/login" replace/>;
  if (requireRole && user.role !== requireRole) return <Navigate to="/" replace/>;
  return <Layout>{children}</Layout>;
}
function PublicRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="app-loader"><div className="spinner"/></div>;
  if (user) return <Navigate to="/" replace/>;
  return children;
}
function HomeRoute() {
  const { user, loading } = useAuth();
  if (loading) return <div className="app-loader"><div className="spinner"/></div>;
  if (user) return <Layout><ChatPage/></Layout>;
  return <LandingPage/>;
}
function AnalyticsTracker() {
  const location = useLocation();
  useEffect(() => { trackPageview(location.pathname); }, [location]);
  return null;
}
function AppRoutes() {
  return (
    <>
    <AnalyticsTracker/>
    <Routes>
      <Route path="/login" element={<PublicRoute><AuthPage/></PublicRoute>}/>
      <Route path="/reset-password" element={<PublicRoute><ResetPasswordPage/></PublicRoute>}/>
      <Route path="/verify-email" element={<VerifyEmailPage/>}/>
      <Route path="/confidentialite" element={<PrivacyPage/>}/>
      <Route path="/cgu" element={<TermsPage/>}/>
      <Route path="/" element={<HomeRoute/>}/>
      <Route path="/reference" element={<ProtectedRoute><ReferencePage/></ProtectedRoute>}/>
      <Route path="/compare" element={<ProtectedRoute><ComparePage/></ProtectedRoute>}/>
      <Route path="/calculators" element={<ProtectedRoute><CalculatorsPage/></ProtectedRoute>}/>
      <Route path="/legal-documents" element={<ProtectedRoute><LegalDocumentsPage/></ProtectedRoute>}/>

      <Route path="/documents" element={<ProtectedRoute><DocumentsPage/></ProtectedRoute>}/>
      <Route path="/dashboard" element={<ProtectedRoute requireRole="admin"><DashboardPage/></ProtectedRoute>}/>
      <Route path="/profile" element={<ProtectedRoute><ProfilePage/></ProtectedRoute>}/>
      <Route path="*" element={<Navigate to="/" replace/>}/>
    </Routes>
    </>
  );
}
export default function App() {
  return <BrowserRouter><LanguageProvider><AuthProvider><CookieBanner/><AppRoutes/></AuthProvider></LanguageProvider></BrowserRouter>;
}
