import { useMemo, useRef, useEffect, useState } from 'react';
import { Pin, Archive, ArrowRightLeft, Clock, Trash2, Copy, Check } from 'lucide-react';
import { SourceAvatar, StatusBadge, getSourceMeta } from '../icons/AppIcons';

/*
  ChatView — the main conversation surface.
  Renders messages chronologically with source avatars, timestamps,
  and actions. Groups adjacent messages from the same source.
  Enhanced with better styling, copy-to-clipboard, and delete.
*/

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return '';
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  if (isToday) return 'Today';
  const yesterday = new Date(now); yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };
  return (
    <button onClick={handleCopy} title="Copy to clipboard">
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

function MessageGroup({ messages, source, onPatch, onSelect, onDelete }) {
  const meta = getSourceMeta(source);
  const first = messages[0];
  const status = first?.status || first?.source_status || 'online';
  const isUser = first?.role === 'user';

  return (
    <div className={`msg-group ${isUser ? 'msg-group-user' : ''}`}>
      <div className="msg-group-header">
        <div className="msg-group-avatar">
          <SourceAvatar source={source} status={status} />
          <span className="msg-group-name">{meta.label}</span>
          <StatusBadge status={status} />
        </div>
        <span className="msg-group-time">
          <Clock size={11} />
          {formatTime(first?.created_at || first?.timestamp)}
        </span>
      </div>
      <div className="msg-group-body">
        {messages.map((m) => {
          const id = m.id || m.message_id || m.created_at;
          const bodyText = m.body || m.content || m.text || m.message || JSON.stringify(m);
          return (
            <div
              key={id}
              className={`msg-bubble ${m.pinned ? 'msg-pinned' : ''} ${m.role === 'user' ? 'msg-user' : ''}`}
              onClick={() => onSelect?.(m)}
            >
              <p>{bodyText}</p>
              {m.pinned && <span className="msg-pin-indicator"><Pin size={10} /></span>}
              <div className="msg-bubble-actions">
                <CopyButton text={bodyText} />
                <button
                  title={m.pinned ? 'Unpin' : 'Pin'}
                  onClick={(e) => { e.stopPropagation(); onPatch(id, { pinned: !m.pinned }); }}
                >
                  <Pin size={12} /> {m.pinned ? 'Unpin' : 'Pin'}
                </button>
                <button
                  title="Archive"
                  onClick={(e) => { e.stopPropagation(); onPatch(id, { archived: true }); }}
                >
                  <Archive size={12} /> Archive
                </button>
                <button
                  title="Move wall"
                  onClick={(e) => { e.stopPropagation(); onPatch(id, { wall: ((m.wall || 1) % 3) + 1 }); }}
                >
                  <ArrowRightLeft size={12} /> Wall {((m.wall || 1) % 3) + 1}
                </button>
                {onDelete && (
                  <button
                    className="danger"
                    title="Delete"
                    onClick={(e) => { e.stopPropagation(); onDelete(id); }}
                  >
                    <Trash2 size={12} /> Delete
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DateDivider({ date }) {
  return (
    <div className="date-divider">
      <span>{date}</span>
    </div>
  );
}

export function ChatView({ messages, onPatchMessage, onSelectMessage, onDeleteMessage, filterSource }) {
  const bottomRef = useRef(null);

  const grouped = useMemo(() => {
    const filtered = filterSource
      ? messages.filter((m) => {
          const s = (m.source || m.source_id || m.source_label || '').toLowerCase();
          return s.includes(filterSource.toLowerCase());
        })
      : messages;

    const sorted = [...filtered].sort((a, b) => {
      const ta = new Date(a.created_at || a.timestamp || 0).getTime();
      const tb = new Date(b.created_at || b.timestamp || 0).getTime();
      return ta - tb;
    });

    const groups = [];
    let currentDate = null;
    let currentSource = null;
    let currentBatch = [];

    sorted.forEach((m) => {
      const d = formatDate(m.created_at || m.timestamp);
      const s = m.source || m.source_id || m.source_label || 'unknown';

      if (d !== currentDate) {
        if (currentBatch.length) {
          groups.push({ type: 'messages', source: currentSource, messages: currentBatch });
        }
        currentDate = d;
        currentSource = s;
        currentBatch = [m];
        groups.push({ type: 'date', date: d });
      } else if (s !== currentSource) {
        if (currentBatch.length) {
          groups.push({ type: 'messages', source: currentSource, messages: currentBatch });
        }
        currentSource = s;
        currentBatch = [m];
      } else {
        currentBatch.push(m);
      }
    });

    if (currentBatch.length) {
      groups.push({ type: 'messages', source: currentSource, messages: currentBatch });
    }

    return groups;
  }, [messages, filterSource]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [grouped.length]);

  if (!messages.length) {
    return (
      <div className="chat-empty">
        <div className="chat-welcome-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <h2>Welcome to Top of Mind</h2>
        <p>Your unified AI command desk. All your AI agents in one surface. Start typing below to send a message through the API.</p>
        <div className="chat-welcome-sources">
          <span>Kimi CLI</span>
          <span>Codex</span>
          <span>AHK</span>
          <span>Clipboard</span>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-view">
      {grouped.map((g, i) =>
        g.type === 'date' ? (
          <DateDivider key={`d-${i}`} date={g.date} />
        ) : (
          <MessageGroup
            key={`m-${i}`}
            messages={g.messages}
            source={g.source}
            onPatch={onPatchMessage}
            onSelect={onSelectMessage}
            onDelete={onDeleteMessage}
          />
        )
      )}
      <div ref={bottomRef} />
    </div>
  );
}
