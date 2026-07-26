import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Layout from "./components/layout/Layout";
import LandingPage from "./pages/LandingPage";
import AuthPage from "./pages/AuthPage";
import ChatPage from "./pages/ChatPage";
import ReferencePage from "./pages/ReferencePage";
import ComparePage from "./pages/ComparePage";
import CalculatorsPage from "./pages/CalculatorsPage";
import LegalDocumentsPage from "./pages/LegalDocumentsPage";
import PricingPage from "./pages/PricingPage";
import DashboardPage from "./pages/DashboardPage";
import DocumentsPage from "./pages/DocumentsPage";
import ProfilePage from "./pages/ProfilePage";
import "./App.css";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="app-loader"><div className="spinner"/></div>;
  if (!user) return <Navigate to="/login" replace/>;
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
function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><AuthPage/></PublicRoute>}/>
      <Route path="/" element={<HomeRoute/>}/>
      <Route path="/reference" element={<ProtectedRoute><ReferencePage/></ProtectedRoute>}/>
      <Route path="/compare" element={<ProtectedRoute><ComparePage/></ProtectedRoute>}/>
      <Route path="/calculators" element={<ProtectedRoute><CalculatorsPage/></ProtectedRoute>}/>
      <Route path="/legal-documents" element={<ProtectedRoute><LegalDocumentsPage/></ProtectedRoute>}/>
      <Route path="/pricing" element={<ProtectedRoute><PricingPage/></ProtectedRoute>}/>
      <Route path="/documents" element={<ProtectedRoute><DocumentsPage/></ProtectedRoute>}/>
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage/></ProtectedRoute>}/>
      <Route path="/profile" element={<ProtectedRoute><ProfilePage/></ProtectedRoute>}/>
      <Route path="*" element={<Navigate to="/" replace/>}/>
    </Routes>
  );
}
export default function App() {
  return <BrowserRouter><AuthProvider><AppRoutes/></AuthProvider></BrowserRouter>;
}
