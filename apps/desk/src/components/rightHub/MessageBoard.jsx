import { useState } from 'react';
import {
  Bell,
  Info,
  AlertTriangle,
  CheckCircle2,
  Clock,
  X,
  Filter,
  RotateCcw,
} from 'lucide-react';

const BOARD_ITEMS = [
  {
    id: 'mb-1',
    type: 'info',
    title: 'No memory handoffs today',
    message: 'All AI agents are running with their own context windows. No cross-agent memory transfers scheduled.',
    time: '2 min ago',
    read: false,
  },
  {
    id: 'mb-2',
    type: 'success',
    title: 'Codex completed file scan',
    message: 'Cross-folder scan finished. 3 near-duplicates found in D:/GitHub and D:/Work.',
    time: '15 min ago',
    read: false,
  },
  {
    id: 'mb-3',
    type: 'warning',
    title: 'Claude session expiring',
    message: 'Session token expires in 30 minutes. Re-authentication required.',
    time: '1 hr ago',
    read: true,
  },
  {
    id: 'mb-4',
    type: 'info',
    title: 'Mattermost bridge online',
    message: 'Message routing to Synology Chat is active. All channels connected.',
    time: '2 hr ago',
    read: true,
  },
  {
    id: 'mb-5',
    type: 'success',
    title: 'Auto-check completed',
    message: 'Scheduled prompt check ran at 14:00. No action required from any agent.',
    time: '3 hr ago',
    read: true,
  },
];

const TYPE_META = {
  info: { icon: Info, color: '#6bd5ff', bg: '#0f1f2e' },
  success: { icon: CheckCircle2, color: '#42d785', bg: '#0f2a1a' },
  warning: { icon: AlertTriangle, color: '#ffc857', bg: '#351f10' },
  error: { icon: AlertTriangle, color: '#ff6464', bg: '#351111' },
};

export function MessageBoard() {
  const [items, setItems] = useState(BOARD_ITEMS);
  const [filter, setFilter] = useState('all');
  const [expandedItem, setExpandedItem] = useState(null);

  const unreadCount = items.filter((i) => !i.read).length;

  const filtered = items.filter((i) => {
    if (filter === 'all') return true;
    if (filter === 'unread') return !i.read;
    return i.type === filter;
  });

  const markRead = (id) => {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, read: true } : i)));
  };

  const dismiss = (id) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  };

  const markAllRead = () => {
    setItems((prev) => prev.map((i) => ({ ...i, read: true })));
  };

  return (
    <div className="message-board">
      {/* Header */}
      <div className="board-header">
        <div className="board-title">
          <Bell size={15} />
          <span>Message Board</span>
          {unreadCount > 0 && <span className="board-badge">{unreadCount}</span>}
        </div>
        <button className="board-mark-all" onClick={markAllRead}>
          <CheckCircle2 size={12} /> Mark all read
        </button>
      </div>

      {/* Filters */}
      <div className="board-filters">
        {[
          { id: 'all', label: 'All' },
          { id: 'unread', label: 'Unread' },
          { id: 'info', label: 'Info' },
          { id: 'success', label: 'OK' },
          { id: 'warning', label: 'Warn' },
        ].map((f) => (
          <button
            key={f.id}
            className={filter === f.id ? 'active' : ''}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Items */}
      <div className="board-items">
        {filtered.length === 0 ? (
          <div className="board-empty">
            <Info size={24} />
            <p>No messages</p>
          </div>
        ) : (
          filtered.map((item) => {
            const meta = TYPE_META[item.type] || TYPE_META.info;
            const Icon = meta.icon;
            const isExpanded = expandedItem === item.id;

            return (
              <div
                key={item.id}
                className={`board-item ${!item.read ? 'unread' : ''}`}
                onClick={() => {
                  markRead(item.id);
                  setExpandedItem(isExpanded ? null : item.id);
                }}
              >
                <div className="board-item-main">
                  <span
                    className="board-item-icon"
                    style={{ color: meta.color, background: meta.bg }}
                  >
                    <Icon size={13} />
                  </span>
                  <div className="board-item-content">
                    <div className="board-item-title">
                      <span>{item.title}</span>
                      {!item.read && <span className="unread-dot" />}
                    </div>
                    <div className="board-item-time">
                      <Clock size={10} />
                      {item.time}
                    </div>
                  </div>
                  <button
                    className="board-item-dismiss"
                    onClick={(e) => { e.stopPropagation(); dismiss(item.id); }}
                    title="Dismiss"
                  >
                    <X size={12} />
                  </button>
                </div>
                {isExpanded && (
                  <div className="board-item-expand">
                    <p>{item.message}</p>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
