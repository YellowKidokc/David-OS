import React, { useState, useCallback } from 'react';
import {
  Bot,
  Sparkles,
  BrainCircuit,
  CircleDot,
  Clipboard,
  Keyboard,
  Zap,
  MessageSquare,
  Plus,
  Settings,
  Search,
  Star,
} from 'lucide-react';

/*
  AgentsPanel — the "Your AI agents" dashboard.
  Modeled after TypingMind's home screen.
  Shows all personas as cards; click one to start/jump to a chat.
*/

const BUILT_IN_AGENTS = [
  {
    id: 'kimi',
    name: 'Kimi',
    role: 'Coordinator',
    description: 'Default coordinator. Short operational answers. Routes messages and manages the crew.',
    icon: Bot,
    color: '#22d3ee',
    bg: 'linear-gradient(135deg, #083344 0%, #0c4a5c 100%)',
    borderColor: '#164e63',
    status: 'online',
    tags: ['coordinator', 'hub'],
    model: 'Kimi Desktop',
  },
  {
    id: 'claude',
    name: 'Claude',
    role: 'Deep Reasoning',
    description: 'Deep reasoning, canon, editorial, theorems. Best for complex analysis and writing.',
    icon: Sparkles,
    color: '#fb923c',
    bg: 'linear-gradient(135deg, #431407 0%, #5c240e 100%)',
    borderColor: '#9a3412',
    status: 'online',
    tags: ['reasoning', 'writing'],
    model: 'Claude Opus 4.6',
  },
  {
    id: 'codex',
    name: 'Codex',
    role: 'Builder',
    description: 'Code, files, APIs, tests, shell commands. The implementer and debugger.',
    icon: CircleDot,
    color: '#60a5fa',
    bg: 'linear-gradient(135deg, #172554 0%, #1e3a8a 100%)',
    borderColor: '#1e40af',
    status: 'online',
    tags: ['code', 'devops'],
    model: 'Codex CLI',
  },
  {
    id: 'gemini',
    name: 'Gemini',
    role: 'Verifier',
    description: 'Broad verification, integration checks, research synthesis.',
    icon: BrainCircuit,
    color: '#60a5fa',
    bg: 'linear-gradient(135deg, #172554 0%, #1e3a8a 100%)',
    borderColor: '#1e40af',
    status: 'online',
    tags: ['verify', 'research'],
    model: 'Gemini 3.1 Pro',
  },
  {
    id: 'gpt',
    name: 'GPT',
    role: 'Generalist',
    description: 'General reasoning, planning, summaries. Jack of all trades.',
    icon: BrainCircuit,
    color: '#4ade80',
    bg: 'linear-gradient(135deg, #052e16 0%, #14532d 100%)',
    borderColor: '#166534',
    status: 'online',
    tags: ['planning', 'summary'],
    model: 'GPT-5.3 Chat',
  },
  {
    id: 'opus',
    name: 'Opus',
    role: 'Theorist',
    description: 'Deep reasoning, canon, editorial, theorems. The philosopher.',
    icon: Sparkles,
    color: '#c084fc',
    bg: 'linear-gradient(135deg, #3b0764 0%, #581c87 100%)',
    borderColor: '#6b21a8',
    status: 'online',
    tags: ['theory', 'canon'],
    model: 'Claude Opus 4.7',
  },
  {
    id: 'sonnet',
    name: 'Sonnet',
    role: 'Balancer',
    description: 'Balanced implementation, writing polish. The editor.',
    icon: Zap,
    color: '#f472b6',
    bg: 'linear-gradient(135deg, #500724 0%, #831843 100%)',
    borderColor: '#9d174d',
    status: 'online',
    tags: ['edit', 'balance'],
    model: 'Claude Sonnet 4',
  },
  {
    id: 'fabel',
    name: 'Fabel',
    role: 'Architect',
    description: 'Site pipelines, content structure, workflow. The systems thinker.',
    icon: BrainCircuit,
    color: '#d6ad4a',
    bg: 'linear-gradient(135deg, #3f2e0a 0%, #713f12 100%)',
    borderColor: '#854d0e',
    status: 'online',
    tags: ['architecture', 'pipelines'],
    model: 'Fabel Opus',
  },
  {
    id: 'anti-gravity',
    name: 'Anti-Gravity',
    role: 'UI/UX',
    description: 'UI, layout, browser behavior, packaging. The visual designer.',
    icon: Zap,
    color: '#94a3b8',
    bg: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
    borderColor: '#475569',
    status: 'online',
    tags: ['ui', 'design'],
    model: 'AG Designer',
  },
  {
    id: 'hakui',
    name: 'Hakui',
    role: 'Quick Check',
    description: 'Fast lightweight answers, quick checks. The speed runner.',
    icon: Bot,
    color: '#a3e635',
    bg: 'linear-gradient(135deg, #1a2e05 0%, #365314 100%)',
    borderColor: '#3f6212',
    status: 'online',
    tags: ['fast', 'check'],
    model: 'Hakui Lite',
  },
  {
    id: 'clipboard',
    name: 'Clipboard',
    role: 'Capture',
    description: 'Clipboard capture and push. The passive listener.',
    icon: Clipboard,
    color: '#94a3b8',
    bg: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
    borderColor: '#475569',
    status: 'online',
    tags: ['capture', 'input'],
    model: 'System',
  },
  {
    id: 'autohotkey',
    name: 'AHK',
    role: 'Bridge',
    description: 'AutoHotKey bridge. Desktop control and overlay management.',
    icon: Keyboard,
    color: '#c084fc',
    bg: 'linear-gradient(135deg, #3b0764 0%, #581c87 100%)',
    borderColor: '#6b21a8',
    status: 'online',
    tags: ['desktop', 'bridge'],
    model: 'AHK Bridge',
  },
];

function AgentCard({ agent, onChat, isFavorite, onToggleFavorite, messageCount }) {
  const Icon = agent.icon || Bot;
  const [hovered, setHovered] = useState(false);

  return (
    <div
      className="agent-card"
      style={{
        '--agent-bg': agent.bg,
        '--agent-border': agent.borderColor,
        '--agent-color': agent.color,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="agent-card-header">
        <div className="agent-avatar">
          <Icon size={22} />
        </div>
        <div className="agent-meta">
          <div className="agent-name-row">
            <b>{agent.name}</b>
            <span className={`agent-status ${agent.status}`} />
          </div>
          <span className="agent-role">{agent.role}</span>
        </div>
        <button
          className={`agent-favorite ${isFavorite ? 'favorited' : ''}`}
          onClick={(e) => { e.stopPropagation(); onToggleFavorite(agent.id); }}
          title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
        >
          <Star size={14} fill={isFavorite ? 'currentColor' : 'none'} />
        </button>
      </div>
      <p className="agent-description">{agent.description}</p>
      <div className="agent-tags">
        {agent.tags.map((tag) => (
          <span key={tag}>#{tag}</span>
        ))}
        <span className="agent-model">{agent.model}</span>
      </div>
      <div className="agent-card-footer">
        <button className="agent-chat-btn" onClick={() => onChat(agent)}>
          <MessageSquare size={14} />
          Chat{messageCount > 0 ? ` (${messageCount})` : ''}
        </button>
      </div>
    </div>
  );
}

export function AgentsPanel({ sources = [], messageCounts = {}, onSelectAgent, activeAgentId }) {
  const [search, setSearch] = useState('');
  const [favorites, setFavorites] = useState(() => {
    try { return JSON.parse(localStorage.getItem('topOfMind.favoriteAgents') || '[]'); }
    catch { return ['kimi', 'claude', 'codex']; }
  });
  const [showAddModal, setShowAddModal] = useState(false);

  const allAgents = BUILT_IN_AGENTS.map((agent) => {
    const source = sources.find(
      (s) => s.id === agent.id || s.name?.toLowerCase() === agent.id
    );
    return { ...agent, ...source, source_id: agent.id };
  });

  const filtered = allAgents.filter((a) => {
    const q = search.toLowerCase();
    return (
      a.name.toLowerCase().includes(q) ||
      a.role.toLowerCase().includes(q) ||
      a.description.toLowerCase().includes(q) ||
      a.tags.some((t) => t.includes(q))
    );
  });

  const favoriteAgents = filtered.filter((a) => favorites.includes(a.id));
  const otherAgents = filtered.filter((a) => !favorites.includes(a.id));

  const toggleFavorite = (id) => {
    const next = favorites.includes(id)
      ? favorites.filter((f) => f !== id)
      : [...favorites, id];
    setFavorites(next);
    localStorage.setItem('topOfMind.favoriteAgents', JSON.stringify(next));
  };

  return (
    <section className="agents-panel">
      <div className="agents-panel-header">
        <div>
          <h1>Your AI Agents</h1>
          <p>All your AI personas in one place. Click any agent to start chatting.</p>
        </div>
        <div className="agents-panel-actions">
          <div className="agents-search">
            <Search size={14} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search agents, roles, tags..."
            />
          </div>
          <button className="agents-add-btn" onClick={() => setShowAddModal(true)}>
            <Plus size={14} /> Add Agent
          </button>
        </div>
      </div>

      {favoriteAgents.length > 0 && (
        <div className="agents-section">
          <h3>Favorites</h3>
          <div className="agents-grid">
            {favoriteAgents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onChat={onSelectAgent}
                isFavorite={true}
                onToggleFavorite={toggleFavorite}
                messageCount={messageCounts.bySource?.[agent.id] || 0}
              />
            ))}
          </div>
        </div>
      )}

      <div className="agents-section">
        <h3>All Agents <span className="agents-count">{filtered.length}</span></h3>
        <div className="agents-grid">
          {otherAgents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onChat={onSelectAgent}
              isFavorite={false}
              onToggleFavorite={toggleFavorite}
              messageCount={messageCounts.bySource?.[agent.id] || 0}
            />
          ))}
        </div>
      </div>

      {filtered.length === 0 && (
        <div className="agents-empty">
          <Bot size={48} strokeWidth={1.2} />
          <h3>No agents found</h3>
          <p>Try a different search term or add a custom agent.</p>
        </div>
      )}

      {showAddModal && (
        <div className="modal-backdrop" onClick={() => setShowAddModal(false)}>
          <div className="agent-modal" onClick={(e) => e.stopPropagation()}>
            <h2>Add Custom Agent</h2>
            <p>Custom agents are stored locally and can be routed via the hub.</p>
            <div className="agent-form-fields">
              <label>
                Name
                <input placeholder="e.g., My Researcher" />
              </label>
              <label>
                Role
                <input placeholder="e.g., Research assistant" />
              </label>
              <label>
                Description
                <textarea rows={3} placeholder="What does this agent do?" />
              </label>
              <label>
                Tags (comma separated)
                <input placeholder="research, writing, code" />
              </label>
            </div>
            <div className="agent-modal-actions">
              <button onClick={() => setShowAddModal(false)}>Cancel</button>
              <button className="tm-primary" onClick={() => setShowAddModal(false)}>
                Create Agent
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
