import { useState } from "react";
import { Bell } from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  useUnreadNotificationCount,
} from "../../hooks/useNotifications";
import { Button } from "../ui/Button";
import "./NotificationBell.css";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const count = useUnreadNotificationCount();
  const list = useNotifications(false);
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();
  const navigate = useNavigate();
  const unread = count.data?.unread ?? 0;

  return (
    <div className="notif-bell">
      <button
        type="button"
        className="notif-bell__btn"
        aria-label="Notifications"
        onClick={() => setOpen((v) => !v)}
      >
        <Bell size={18} strokeWidth={1.75} aria-hidden />
        {unread > 0 ? <span className="notif-bell__badge font-data">{unread > 9 ? "9+" : unread}</span> : null}
      </button>
      {open ? (
        <div className="notif-bell__panel" role="dialog" aria-label="Notifications">
          <div className="notif-bell__panel-head">
            <strong>Notifications</strong>
            <Button
              variant="secondary"
              disabled={markAll.isPending || unread === 0}
              onClick={() => markAll.mutate()}
            >
              Mark all read
            </Button>
          </div>
          <ul className="notif-bell__list">
            {(list.data?.items ?? []).length === 0 ? (
              <li className="notif-bell__empty">No notifications yet.</li>
            ) : (
              (list.data?.items ?? []).map((n) => (
                <li
                  key={n.id}
                  className={`notif-bell__item${n.readAt ? "" : " notif-bell__item--unread"}`}
                >
                  <button
                    type="button"
                    className="notif-bell__item-btn"
                    onClick={async () => {
                      if (!n.readAt) await markRead.mutateAsync(n.id);
                      if (n.kind.startsWith("kpi_")) {
                        setOpen(false);
                        navigate("/kpi/dashboard");
                      }
                    }}
                  >
                    <span className="notif-bell__title">{n.title}</span>
                    <span className="notif-bell__body">{n.body}</span>
                    <span className="notif-bell__time font-data">
                      {new Date(n.createdAt).toLocaleString()}
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
