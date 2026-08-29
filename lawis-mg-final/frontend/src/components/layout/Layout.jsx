import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Scale, MessageSquare, BarChart2, GitCompare, Hash, Upload, Calculator, FileText, LogOut, ChevronLeft, ChevronRight, Bell, Menu, X } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useLanguage } from "../../contexts/LanguageContext";
import NotificationBell from "./NotificationBell";
import LanguageSwitcher from "../LanguageSwitcher";

const NAV = [
  { to: "/", icon: MessageSquare, labelKey: "nav.chat", end: true },
  { to: "/reference", icon: Hash, labelKey: "nav.reference" },
  { to: "/compare", icon: GitCompare, labelKey: "nav.compare" },
  { to: "/calculators", icon: Calculator, labelKey: "nav.calculators" },
  { to: "/legal-documents", icon: FileText, labelKey: "nav.legalDocuments" },
  { to: "/documents", icon: Upload, labelKey: "nav.documents" },
  { to: "/dashboard", icon: BarChart2, labelKey: "nav.dashboard", adminOnly: true },
];

const ROLE_KEYS = { admin: "role.admin", juriste: "role.juriste", avocat: "role.avocat", entreprise: "role.entreprise", etudiant: "role.etudiant", particulier: "role.particulier" };

export default function Layout({ children }) {
  const { t } = useTranslation();
  const { lang } = useLanguage();
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
      <button className="mobile-topbar-toggle" onClick={() => setMobileOpen(true)} aria-label={t("nav.openMenu")}>
        <Menu size={20} />
      </button>
      {mobileOpen && <div className="mobile-sidebar-backdrop" onClick={closeMobile} />}
      <aside className="main-sidebar">
        <div className="main-sidebar-logo">
          <div className="sidebar-logo-icon"><Scale size={20} /></div>
          {!collapsed && <div className="sidebar-logo-text"><span className="sidebar-brand">{t("app.brand")}</span><span className="sidebar-tagline">{t("app.tagline")}</span></div>}
          <div style={{display:"flex",alignItems:"center",gap:4}}>
            <NotificationBell />
            <button className="sidebar-collapse-btn" onClick={() => setCollapsed((p) => !p)}>
              {collapsed !== (lang === "ar") ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
            </button>
            <button className="mobile-sidebar-close" onClick={closeMobile} aria-label={t("nav.closeMenu")}><X size={18} /></button>
          </div>
        </div>
        <nav className="main-sidebar-nav">
          {NAV.filter((item) => !item.adminOnly || user?.role === "admin").map(({ to, icon: Icon, labelKey, end }) => (
            <NavLink key={to} to={to} end={end} title={collapsed ? t(labelKey) : undefined} onClick={closeMobile}
              className={({ isActive }) => `sidebar-nav-item ${isActive ? "active" : ""}`}>
              <Icon size={17} className="nav-icon" />
              {!collapsed && <span>{t(labelKey)}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          {!collapsed && <LanguageSwitcher variant="dark" className="sidebar-lang-toggle" />}
          <NavLink to="/profile" onClick={closeMobile} className={({ isActive }) => `sidebar-nav-item user-item ${isActive ? "active" : ""}`}>
            <div className="user-avatar">{user?.full_name?.[0] || user?.username?.[0] || "U"}</div>
            {!collapsed && <div className="user-info"><span className="user-name">{user?.full_name || user?.username}</span><span className="user-role">{t(ROLE_KEYS[user?.role]) || user?.role}</span></div>}
          </NavLink>
          <button className="sidebar-nav-item logout-btn" onClick={async () => { await logout(); navigate("/login"); }} title={collapsed ? t("nav.logout") : undefined}>
            <LogOut size={17} className="nav-icon" />
            {!collapsed && <span>{t("nav.logout")}</span>}
          </button>
        </div>
      </aside>
      <main className="main-content-area">{children}</main>
    </div>
  );
}
