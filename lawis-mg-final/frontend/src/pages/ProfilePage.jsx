import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../contexts/AuthContext";
import { authService, extractErrorMessage } from "../services/api";
const LEVELS = ["debutant", "intermediaire", "expert"];
export default function ProfilePage() {
  const { t } = useTranslation();
  const { user, updateUser } = useAuth();
  const [form, setForm] = useState({ full_name:user?.full_name||"", profession:user?.profession||"", legal_level:user?.legal_level||"intermediaire", sector:user?.sector||"" });
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);
  const handleSubmit = async (e) => {
    e.preventDefault(); setLoading(true);
    try { const r=await authService.updateProfile(form); updateUser(r.data); setMsg({type:"success",text:t("profile.updateSuccess")}); }
    catch(err) { setMsg({type:"error",text:extractErrorMessage(err, t("profile.updateError"))}); }
    finally { setLoading(false); }
  };
  return (
    <div className="page-container">
      <div className="page-header"><h1>{t("profile.title")}</h1><p>{t("profile.subtitle")}</p></div>
      <div className="profile-card">
        <div className="profile-avatar-section">
          <div className="profile-avatar-large">{user?.full_name?.[0]||user?.username?.[0]||"U"}</div>
          <div><h2>{user?.full_name||user?.username}</h2><p className="text-muted">{user?.email}</p></div>
        </div>
        {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}
        <form onSubmit={handleSubmit} className="profile-form">
          <div className="form-row">
            <div className="form-group"><label>{t("profile.fullName")}</label><input className="form-input" value={form.full_name} onChange={e=>setForm(p=>({...p,full_name:e.target.value}))}/></div>
            <div className="form-group"><label>{t("profile.profession")}</label><input className="form-input" value={form.profession} onChange={e=>setForm(p=>({...p,profession:e.target.value}))} placeholder={t("profile.professionPlaceholder")}/></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>{t("profile.sector")}</label><input className="form-input" value={form.sector} onChange={e=>setForm(p=>({...p,sector:e.target.value}))} placeholder={t("profile.sectorPlaceholder")}/></div>
            <div className="form-group"><label>{t("profile.legalLevel")}</label>
              <select className="form-input" value={form.legal_level} onChange={e=>setForm(p=>({...p,legal_level:e.target.value}))}>
                {LEVELS.map(l=><option key={l} value={l}>{t(`profile.levels.${l}`)}</option>)}
              </select>
            </div>
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>{loading?t("profile.saving"):t("profile.save")}</button>
        </form>
      </div>
    </div>
  );
}
