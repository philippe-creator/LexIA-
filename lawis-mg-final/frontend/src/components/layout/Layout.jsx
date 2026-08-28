import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Scale, MessageSquare, BarChart2, GitCompare, Hash, Upload, Calculator, FileText, LogOut, ChevronLeft, ChevronRight, Bell, Menu, X } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import NotificationBell from "./NotificationBell";

const NAV = [
  { to: "/", icon: MessageSquare, label: "Assistant juridique", end: true },
  { to: "/reference", icon: Hash, label: "Recherche par référence" },
  { to: "/compare", icon: GitCompare, label: "Comparer des versions" },
  { to: "/calculators", icon: Calculator, label: "Calculateurs" },
  { to: "/legal-documents", icon: FileText, label: "Générer un document" },
  { to: "/documents", icon: Upload, label: "Mes documents" },
  { to: "/dashboard", icon: BarChart2, label: "Tableau de bord", adminOnly: true },
];

const ROLE_LABELS = { admin:"Administrateur", juriste:"Juriste", avocat:"Avocat", entreprise:"Entreprise", etudiant:"Étudiant", particulier:"Particulier" };

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  // Menu séparé pour mobile : le rail latéral fixe n'a pas sa place sur un
  // petit écran (il mangerait la majorité de la largeur) — sur mobile il
  // devient un tiroir masqué par défaut, ouvert par le bouton hamburger.
  const [mobileOpen, setMobileOpen] = useState(false);
  const closeMobile = () => setMobileOpen(false);

  return (
    <div className={`layout ${collapsed ? "sidebar-collapsed" : ""} ${mobileOpen ? "mobile-menu-open" : ""}`}>
      <button className="mobile-topbar-toggle" onClick={() => setMobileOpen(true)} aria-label="Ouvrir le menu">
        <Menu size={20} />
      </button>
      {mobileOpen && <div className="mobile-sidebar-backdrop" onClick={closeMobile} />}
      <aside className="main-sidebar">
        <div className="main-sidebar-logo">
          <div className="sidebar-logo-icon"><Scale size={20} /></div>
          {!collapsed && <div className="sidebar-logo-text"><span className="sidebar-brand">LexIA Maroc</span><span className="sidebar-tagline">Veille juridique IA</span></div>}
          <div style={{display:"flex",alignItems:"center",gap:4}}>
            <NotificationBell />
            <button className="sidebar-collapse-btn" onClick={() => setCollapsed((p) => !p)}>
              {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
            </button>
            <button className="mobile-sidebar-close" onClick={closeMobile} aria-label="Fermer le menu"><X size={18} /></button>
          </div>
        </div>
        <nav className="main-sidebar-nav">
          {NAV.filter((item) => !item.adminOnly || user?.role === "admin").map(({ to, icon: Icon, label, end }) => (
            <NavLink key={to} to={to} end={end} title={collapsed ? label : undefined} onClick={closeMobile}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? "active" : ""}`}>
              <Icon size={17} className="nav-icon" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <NavLink to="/profile" onClick={closeMobile} className={({ isActive }) => `sidebar-nav-item user-item ${isActive ? "active" : ""}`}>
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
