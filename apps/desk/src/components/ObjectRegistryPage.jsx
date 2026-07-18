import React, { useMemo, useState } from 'react';

const providers = {
  openai: { label: 'OpenAI', status: 'configured', icon: '◎' },
  anthropic: { label: 'Anthropic', status: 'configured', icon: 'AI' },
  google: { label: 'Google', status: 'configured', icon: '✦' },
  local: { label: 'Local', status: 'offline', icon: '⌂' },
  system: { label: 'System', status: 'active', icon: '⚙' },
};

export const registryData = {
  agents: {
    title: 'Agents',
    subtitle: 'Durable working identities with roles, models, tools, permissions, and conversation status.',
    cta: 'Create agent',
    groups: ['All agents', 'Active', 'Unread', 'Invited', 'Silent', 'Muted', 'Offline'],
    items: [
      { id: 'primary', name: 'GPT Primary', group: 'Active', provider: 'openai', model: 'GPT-5.4', status: 'speaking', unread: 0, description: 'Primary conductor that synthesizes visible answers and suppresses duplicate proposals.', tags: ['conductor', 'default'], permissions: ['silent advisors', 'selected context', 'review required'], tools: ['Web Browser', 'MCP Hub'] },
      { id: 'claude', name: 'Claude', group: 'Unread', provider: 'anthropic', model: 'Claude Sonnet 4.6', status: 'new message', unread: 1, description: 'Long-context reasoning partner for contradiction checks and theological/physics review.', tags: ['contradiction', 'research'], permissions: ['recent context', 'silent by default'], tools: ['Knowledge Search'] },
      { id: 'physicist', name: 'Physicist', group: 'Invited', provider: 'openai', model: 'GPT-5.4 Pro', status: 'working', unread: 0, description: 'Specialist agent for entropy, boundary-condition, and theoretical physics audits.', tags: ['physics', 'audit'], permissions: ['selected files only', 'no commands'], tools: ['MCP Hub'] },
      { id: 'archivist', name: 'Archivist', group: 'Silent', provider: 'google', model: 'Gemini 3.1 Pro', status: 'found 4 sources', unread: 4, description: 'Source collector that prepares citations and provenance packets without interrupting the main turn.', tags: ['sources', 'memory'], permissions: ['canonical context', 'silent advisor'], tools: ['File Cache', 'SiYuan'] },
      { id: 'adversary', name: 'Adversary', group: 'Muted', provider: 'anthropic', model: 'Claude Fable 5', status: 'muted', unread: 0, description: 'Red-team reviewer. Muted until explicitly invited into a named contribution or roundtable.', tags: ['red-team'], permissions: ['current message only'], tools: [] },
    ],
  },
  models: {
    title: 'Models',
    subtitle: 'Capability providers are separate from agents; one model can power many agent identities.',
    cta: 'Add custom model',
    groups: ['All models', 'OpenAI', 'Anthropic', 'Google', 'OpenRouter', 'Local', 'Disabled'],
    items: [
      { id: 'gpt-5-4', name: 'GPT-5.4', group: 'OpenAI', provider: 'openai', status: 'default', context: '1M', description: 'Frontier model for complex professional work and primary synthesis.', tags: ['plugins', 'vision', 'system role', 'streaming'], pricing: '$2.5 / $15', enabled: true },
      { id: 'claude-sonnet-46', name: 'Claude Sonnet 4.6', group: 'Anthropic', provider: 'anthropic', status: 'enabled', context: '1M', description: 'Long-context collaborator for careful reasoning and critique.', tags: ['system role', 'prompt caching'], pricing: '$5 / $25', enabled: true },
      { id: 'gemini-31-pro', name: 'Gemini 3.1 Pro', group: 'Google', provider: 'google', status: 'enabled', context: '1M', description: 'Research, multimodal, and document-oriented model lane.', tags: ['vision', 'long context'], pricing: 'configured', enabled: true },
      { id: 'ollama-local', name: 'Ollama Local', group: 'Local', provider: 'local', status: 'offline', context: '128K', description: 'Local inference endpoint for private drafting when available.', tags: ['local', 'private'], pricing: 'local', enabled: false },
    ],
  },
  plugins: {
    title: 'Plugins',
    subtitle: 'Per-message tools and plugin choices that should be selectable before sending.',
    cta: 'Add plugin',
    groups: ['All plugins', 'Model tools', 'Knowledge', 'Files', 'Search', 'Creative', 'Disabled'],
    items: [
      { id: 'web-browser', name: 'Web Browser', group: 'Model tools', provider: 'system', status: 'enabled', description: 'Read-only browser/search tool for current information.', tags: ['read-only', 'web'], permissions: ['network read'], enabled: true },
      { id: 'code-sandbox', name: 'Code Sandbox', group: 'Model tools', provider: 'system', status: 'enabled', description: 'Controlled code execution surface for analysis and tests.', tags: ['code', 'sandbox'], permissions: ['execute with approval'], enabled: true },
      { id: 'siyuan-mcp', name: 'SiYuan Knowledge', group: 'Knowledge', provider: 'system', status: 'configured', description: 'Local MCP Hub access to SiYuan notes and compact context packets.', tags: ['mcp', 'knowledge'], permissions: ['read notes'], enabled: true },
      { id: 'image-search', name: 'Image Search', group: 'Search', provider: 'system', status: 'disabled', description: 'Image lookup and visual reference collection.', tags: ['image', 'search'], permissions: ['network read'], enabled: false },
    ],
  },
  workflows: {
    title: 'Workflows',
    subtitle: 'Repeatable operating-system automations with triggers, review gates, and resumable logs.',
    cta: 'Create workflow',
    groups: ['All workflows', 'Manual', 'Clipboard', 'File changes', 'Scheduled', 'Review required'],
    items: [
      { id: 'context-packet', name: 'Build context packet', group: 'Manual', provider: 'system', status: 'ready', description: 'Collect files, clipboard records, messages, prompts, and state into a cited package.', tags: ['context', 'export'], trigger: 'manual launch', permissions: ['read selected sources'] },
      { id: 'clipboard-triage', name: 'Clipboard triage', group: 'Clipboard', provider: 'system', status: 'ready', description: 'Deduplicate, secret-check, tag, and optionally route clipboard captures.', tags: ['clipboard', 'review'], trigger: 'clipboard captured', permissions: ['read clipboard'] },
      { id: 'contradiction-scan', name: 'Contradiction scan', group: 'Review required', provider: 'system', status: 'planned', description: 'Ask silent specialists to detect contradictions and create arrival events.', tags: ['agents', 'review'], trigger: 'manual or scheduled', permissions: ['silent proposals only'] },
    ],
  },
};

function providerMeta(id) {
  return providers[id] || providers.system;
}

export function ObjectRegistryPage({ kind = 'agents', onAction, onCopyToComposer }) {
  const data = registryData[kind] || registryData.agents;
  const [group, setGroup] = useState(data.groups[0]);
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState(data.items[0]?.id);
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return data.items.filter((item) => {
      const inGroup = group === data.groups[0] || item.group === group || item.status === group.toLowerCase();
      const text = [item.name, item.description, item.group, item.status, item.model, ...(item.tags || [])].join(' ').toLowerCase();
      return inGroup && (!q || text.includes(q));
    });
  }, [data, group, query]);
  const selected = data.items.find((item) => item.id === selectedId) || visible[0] || data.items[0];

  const copySpec = async () => {
    const text = JSON.stringify(selected, null, 2);
    await navigator.clipboard?.writeText?.('```json\n' + text + '\n```');
    onAction?.(`Copied ${selected.name} spec.`);
  };

  const sendToComposer = () => {
    onCopyToComposer?.(`Use ${data.title.slice(0, -1)}: ${selected.name}\nStatus: ${selected.status}\nDescription: ${selected.description}`);
  };

  return <section className="registry-page">
    <aside className="registry-sidebar">
      <div className="registry-side-title">{data.title}</div>
      {data.groups.map((name) => {
        const count = name === data.groups[0] ? data.items.length : data.items.filter((item) => item.group === name || item.status === name.toLowerCase()).length;
        return <button key={name} className={group === name ? 'selected' : ''} onClick={() => setGroup(name)}><span>{name}</span><b>{count}</b></button>;
      })}
    </aside>
    <main className="registry-main">
      <header className="registry-header"><div><h1>{data.title}</h1><p>{data.subtitle}</p></div><button className="tm-primary" onClick={() => onAction?.(`${data.cta} will use the durable registry backend when available.`)}>＋ {data.cta}</button></header>
      <div className="registry-toolbar"><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`Search ${data.title.toLowerCase()}…`} /><button>⋮</button><button>↕ Status</button></div>
      <div className="registry-list">{visible.map((item) => { const provider = providerMeta(item.provider); return <article key={item.id} className={`registry-row ${selected?.id === item.id ? 'selected' : ''}`} onClick={() => setSelectedId(item.id)}><span className="registry-avatar">{provider.icon}</span><div><b>{item.name}</b><p>{item.description}</p><small>{item.model || item.trigger || provider.label} · {item.context || item.pricing || item.status}</small></div><span className={`registry-status ${item.status}`}>{item.status}</span>{typeof item.enabled === 'boolean' && <span className={`registry-toggle ${item.enabled ? 'on' : ''}`} />}{item.unread > 0 && <em>{item.unread}</em>}</article>; })}</div>
    </main>
    <aside className="registry-inspector">
      {selected && <><div className="registry-detail-head"><span className="registry-avatar large">{providerMeta(selected.provider).icon}</span><div><h2>{selected.name}</h2><p>{providerMeta(selected.provider).label} · {selected.status}</p></div></div><div className="registry-tabs"><button className="active">Overview</button><button>Permissions</button><button>Activity</button></div><dl><dt>Description</dt><dd>{selected.description}</dd><dt>Model / provider</dt><dd>{selected.model || providerMeta(selected.provider).label}</dd><dt>Tools / permissions</dt><dd>{[...(selected.tools || []), ...(selected.permissions || [])].join(', ') || 'No tools configured'}</dd><dt>Tags</dt><dd>{(selected.tags || []).map((tag) => <span key={tag} className="registry-tag">{tag}</span>)}</dd></dl><div className="registry-actions"><button className="tm-primary" onClick={sendToComposer}>Use now</button><button onClick={copySpec}>Copy spec</button><button onClick={() => onAction?.(`Opened inspector for ${selected.name}.`)}>Inspect</button></div><small>Objects are intentionally separated: models provide capability; agents define working identity; plugins/tools are selected per message.</small></>}
    </aside>
  </section>;
}
