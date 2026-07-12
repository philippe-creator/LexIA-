import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Scale, MessageSquare, BarChart2, GitCompare, Hash, Upload, Calculator, LogOut, ChevronLeft, ChevronRight } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";

const NAV = [
  { to: "/", icon: MessageSquare, label: "Assistant juridique", end: true },
  { to: "/reference", icon: Hash, label: "Recherche par référence" },
  { to: "/compare", icon: GitCompare, label: "Comparer des versions" },
  { to: "/calculators", icon: Calculator, label: "Calculateurs" },
  { to: "/documents", icon: Upload, label: "Mes documents" },
  { to: "/dashboard", icon: BarChart2, label: "Tableau de bord" },
];

const ROLE_LABELS = { admin:"Administrateur", juriste:"Juriste", avocat:"Avocat", entreprise:"Entreprise", etudiant:"Étudiant", particulier:"Particulier" };

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`layout ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className="main-sidebar">
        <div className="main-sidebar-logo">
          <div className="sidebar-logo-icon"><Scale size={20} /></div>
          {!collapsed && <div className="sidebar-logo-text"><span className="sidebar-brand">LexIA Maroc</span><span className="sidebar-tagline">Veille juridique IA</span></div>}
          <button className="sidebar-collapse-btn" onClick={() => setCollapsed((p) => !p)}>
            {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
          </button>
        </div>
        <nav className="main-sidebar-nav">
          {NAV.map(({ to, icon: Icon, label, end }) => (
            <NavLink key={to} to={to} end={end} title={collapsed ? label : undefined}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? "active" : ""}`}>
              <Icon size={17} className="nav-icon" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <NavLink to="/profile" className={({ isActive }) => `sidebar-nav-item user-item ${isActive ? "active" : ""}`}>
            <div className="user-avatar">{user?.full_name?.[0] || user?.username?.[0] || "U"}</div>
            {!collapsed && <div className="user-info"><span className="user-name">{user?.full_name || user?.username}</span><span className="user-role">{ROLE_LABELS[user?.role] || user?.role}</span></div>}
          </NavLink>
          <button className="sidebar-nav-item logout-btn" onClick={async () => { await logout(); navigate("/login"); }} title={collapsed ? "Déconnexion" : undefined}>
            <LogOut size={17} className="nav-icon" />
            {!collapsed && <span>Déconnexion</span>}
          </button>
        </div>
      </aside>
      <main className="main-content-area">{children}</main>
    </div>
  );
}
