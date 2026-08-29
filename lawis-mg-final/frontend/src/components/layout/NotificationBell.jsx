import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Bell, X, Check, CheckCheck, Inbox } from "lucide-react";
import { notificationService } from "../../services/api";
import { useLanguage } from "../../contexts/LanguageContext";
import { dateLocale } from "../../i18n/dateLocale";

export default function NotificationBell({ onNavigate }) {
  const { t } = useTranslation();
  const { lang } = useLanguage();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);

  const load = async () => {
    try {
      const r = await notificationService.list();
      setNotifications(r.data.items || []);
      setUnreadCount(r.data.total || 0);
    } catch {}
  };
  useEffect(() => { load(); }, []);
  useEffect(() => { if (open) load(); }, [open]);

  const markRead = async (id) => {
    await notificationService.markRead(id);
    setNotifications((p) => p.map((n) => (n.id === id ? { ...n, read: true } : n)));
    setUnreadCount((c) => Math.max(0, c - 1));
  };
  const markAllRead = async () => {
    await notificationService.markAllRead();
    setNotifications((p) => p.map((n) => ({ ...n, read: true })));
    setUnreadCount(0);
  };

  return (
    <div className="notification-bell">
      <button className="icon-btn" onClick={() => setOpen(!open)} aria-label={t("notifications.ariaLabel")}>
        <Bell size={18} />
        {unreadCount > 0 && <span className="badge">{unreadCount > 99 ? "99+" : unreadCount}</span>}
      </button>
      {open && (
        <div className="notification-dropdown">
          <div className="notification-header">
            <strong>{t("notifications.title")}</strong>
            {unreadCount > 0 && (
              <button className="text-btn" onClick={markAllRead}>
                <CheckCheck size={14} /> {t("notifications.markAllRead")}
              </button>
            )}
          </div>
          <div className="notification-list">
            {notifications.length === 0 && (
              <div className="empty-state"><Inbox size={24}/><p>{t("notifications.empty")}</p></div>
            )}
            {notifications.map((n) => (
              <div key={n.id} className={`notification-item ${n.read ? "read" : "unread"}`}>
                <div className="notification-content">
                  <div className="notification-title">{n.title}</div>
                  <div className="notification-message">{n.message}</div>
                  <div className="notification-time">{new Date(n.created_at).toLocaleString(dateLocale(lang))}</div>
                </div>
                {!n.read && (
                  <button className="icon-btn-sm" onClick={() => markRead(n.id)} title={t("notifications.markRead")}>
                    <Check size={14}/>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
