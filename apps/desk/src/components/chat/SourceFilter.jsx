import { useState } from 'react';
import {
  MessageSquare,
  Filter,
  Bot,
  Sparkles,
  BrainCircuit,
  CircleDot,
  Clipboard,
  Keyboard,
  X,
} from 'lucide-react';

/*
  SourceFilter — the "hidden folders" for each AI/persona.
  Click a source to filter the chat to just that lane.
  This is the client-side view of the multi-conversation concept David described:
  each AI has its own lane, but messages can be mixed in threads.
*/

const BUILT_IN_SOURCES = [
  { id: 'kimi', name: 'Kimi', icon: Bot, color: '#22d3ee' },
  { id: 'claude', name: 'Claude', icon: Sparkles, color: '#fb923c' },
  { id: 'codex', name: 'Codex', icon: CircleDot, color: '#60a5fa' },
  { id: 'gemini', name: 'Gemini', icon: BrainCircuit, color: '#60a5fa' },
  { id: 'gpt', name: 'GPT', icon: BrainCircuit, color: '#4ade80' },
  { id: 'cursor', name: 'Cursor', icon: CircleDot, color: '#c084fc' },
  { id: 'clipboard', name: 'Clipboard', icon: Clipboard, color: '#94a3b8' },
  { id: 'autohotkey', name: 'AHK', icon: Keyboard, color: '#c084fc' },
];

export function SourceFilter({
  sources,
  activeFilter,
  onFilterChange,
  messageCounts,
  online,
}) {
  const [collapsed, setCollapsed] = useState(false);

  const allSources = sources?.length
    ? sources.map((s) => {
        const builtIn = BUILT_IN_SOURCES.find(
          (b) => s.id?.toLowerCase().includes(b.id) || s.name?.toLowerCase().includes(b.id)
        );
        return { ...s, icon: builtIn?.icon || Bot, color: builtIn?.color || '#94a3b8' };
      })
    : BUILT_IN_SOURCES;

  return (
    <div className={`source-filter ${collapsed ? 'collapsed' : ''}`}>
      <button
        className="source-filter-toggle"
        onClick={() => setCollapsed(!collapsed)}
        title={collapsed ? 'Expand lanes' : 'Collapse lanes'}
      >
        {collapsed ? <Bot size={16} /> : <Filter size={14} />}
        {!collapsed && <span>AI Lanes</span>}
      </button>

      {!collapsed && (
        <>
          {/* All messages */}
          <button
            className={`source-lane ${!activeFilter ? 'active' : ''}`}
            onClick={() => onFilterChange(null)}
          >
            <MessageSquare size={14} />
            <span>All</span>
            <span className="lane-count">{messageCounts?.total || 0}</span>
            {online && <span className="lane-dot online" />}
          </button>

          {/* Per-source lanes */}
          <div className="source-lanes">
            {allSources.map((s) => {
              const Icon = s.icon || Bot;
              const count = messageCounts?.bySource?.[s.id] || 0;
              const isActive = activeFilter === s.id;
              return (
                <button
                  key={s.id}
                  className={`source-lane ${isActive ? 'active' : ''}`}
                  onClick={() => onFilterChange(isActive ? null : s.id)}
                  style={{ '--lane-color': s.color || '#94a3b8' }}
                >
                  <Icon size={14} />
                  <span>{s.name || s.id}</span>
                  {count > 0 && <span className="lane-count">{count}</span>}
                  <span
                    className={`lane-dot ${s.status === 'online' || s.status === 'ready' ? 'online' : ''}`}
                  />
                </button>
              );
            })}
          </div>

          {activeFilter && (
            <button
              className="source-filter-clear"
              onClick={() => onFilterChange(null)}
            >
              <X size={12} /> Clear filter
            </button>
          )}
        </>
      )}
    </div>
  );
}
