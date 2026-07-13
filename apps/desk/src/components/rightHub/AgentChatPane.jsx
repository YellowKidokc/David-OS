import { useState, useRef, useEffect } from 'react';
import {
  Send,
  X,
  Merge,
  ChevronDown,
  Bot,
  Sparkles,
  Maximize2,
  Minimize2,
  MessageSquare,
} from 'lucide-react';
import { SourceAvatar, getSourceMeta } from '../icons/AppIcons';

function formatTimeShort(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function AgentChatPane({
  paneIndex,
  source,
  sources,
  messages,
  allMessages,
  onSend,
  onPatch,
  onAssignAgent,
  onRemove,
  onMerge,
  canRemove,
  isSingle,
}) {
  const [input, setInput] = useState('');
  const [showAgentPicker, setShowAgentPicker] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const messagesEndRef = useRef(null);
  const meta = getSourceMeta(source?.id || source?.name || 'unknown');

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSend({
      body: input,
      source_id: source?.id,
      source_label: source?.name || source?.id,
    });
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  // Group messages by date
  const grouped = [];
  let currentBatch = [];
  let lastDate = null;

  [...messages].sort((a, b) => {
    const ta = new Date(a.created_at || a.timestamp || 0).getTime();
    const tb = new Date(b.created_at || b.timestamp || 0).getTime();
    return ta - tb;
  }).forEach((m) => {
    const d = new Date(m.created_at || m.timestamp || 0).toDateString();
    if (d !== lastDate && currentBatch.length) {
      grouped.push({ type: 'batch', messages: currentBatch });
      currentBatch = [];
    }
    lastDate = d;
    currentBatch.push(m);
  });
  if (currentBatch.length) grouped.push({ type: 'batch', messages: currentBatch });

  return (
    <div className={`agent-chat-pane ${isExpanded ? 'expanded' : ''}`}>
      {/* Pane header */}
      <div className="pane-header">
        <div className="pane-header-left">
          <SourceAvatar source={source?.id} status={source?.status || 'online'} compact />
          <div className="pane-header-info">
            <span className="pane-name">{meta.label}</span>
            <span className={`pane-status ${source?.status || 'online'}`}>
              {source?.status || 'online'}
            </span>
          </div>

          {/* Agent switcher */}
          <div className="agent-picker">
            <button
              className="agent-picker-btn"
              onClick={() => setShowAgentPicker(!showAgentPicker)}
              title="Switch AI"
            >
              <ChevronDown size={12} />
            </button>
            {showAgentPicker && (
              <div className="agent-picker-dropdown">
                {sources.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => { onAssignAgent(s.id); setShowAgentPicker(false); }}
                    className={s.id === source?.id ? 'active' : ''}
                  >
                    <SourceAvatar source={s.id} status={s.status || 'online'} compact />
                    <span>{s.name || s.id}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="pane-header-actions">
          {!isSingle && (
            <button onClick={onMerge} title="Merge conversation">
              <Merge size={13} />
            </button>
          )}
          {canRemove && (
            <button onClick={onRemove} title="Close pane">
              <X size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Messages area */}
      <div className="pane-messages">
        {messages.length === 0 ? (
          <div className="pane-empty">
            <MessageSquare size={28} strokeWidth={1.2} />
            <p>No messages with {meta.label}</p>
          </div>
        ) : (
          grouped.map((g, gi) =>
            g.messages.map((m, mi) => {
              const isUser = m.role === 'user';
              const id = m.id || m.message_id || m.created_at;
              return (
                <div
                  key={`${gi}-${mi}-${id}`}
                  className={`pane-msg ${isUser ? 'msg-user' : ''}`}
                >
                  <div className="pane-msg-meta">
                    <span className="pane-msg-source">
                      {isUser ? 'You' : meta.label}
                    </span>
                    <span className="pane-msg-time">
                      {formatTimeShort(m.created_at || m.timestamp)}
                    </span>
                  </div>
                  <div className="pane-msg-body">
                    <p>{m.body || m.content || m.text || m.message || ''}</p>
                  </div>
                </div>
              );
            })
          )
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Composer */}
      <div className="pane-composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Message ${meta.label}...`}
          rows={1}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim()}
          className="pane-send-btn"
          title="Send (Ctrl+Enter)"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
