import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { createRoot } from 'react-dom/client';
import { NUMBERING, topOfMindApi } from './lib/api/topOfMindApi';
import { ChatView } from './components/chat/ChatView';
import { Composer } from './components/chat/Composer';
import { SourceFilter } from './components/chat/SourceFilter';
import { PromptsPanel } from './components/prompts/PromptsPanel';
import './styles.css';

const ACTIVE_AGENT_KEY = 'topOfMind.activeAgentId';
const OP_FAMILY_KEY = 'topOfMind.operationFamily';
const API_SHELF_KEY = 'topOfMind.apiShelf.v1';

// ---- fallback data ----
const fallbackSources = [
  { id: 'clipboard', name: 'Clipboard', status: 'online', source_code: NUMBERING.sources.clipboard },
  { id: 'ahk', name: 'AutoHotkey', status: 'online', source_code: NUMBERING.sources.ahk },
  { id: 'codex', name: 'Codex', status: 'online', source_code: NUMBERING.sources.codex },
  { id: 'kimi', name: 'Kimi', status: 'online', source_code: NUMBERING.sources.kimi },
  { id: 'claude', name: 'Claude', status: 'online', source_code: NUMBERING.sources.claude },
  { id: 'gemini', name: 'Gemini', status: 'online', source_code: NUMBERING.sources.gemini },
  { id: 'cursor', name: 'Cursor/Versor', status: 'online', source_code: NUMBERING.sources.cursor },
];
const starterFolders = [
  { id: 'local-inbox', name: 'Inbox', folder_code: NUMBERING.folders.inbox, children: [
    { id: 'local-active', name: 'Active', folder_code: NUMBERING.folders.active }
  ]}
];

// ---- helpers ----
const initials = (s) => (s?.name || s?.label || s?.id || s?.source_id || '?').split(/\s|-/).map((p) => p[0]).join('').slice(0, 3).toUpperCase();
const srcName = (s) => s?.name || s?.label || s?.source_id || s?.id || 'source';
const srcId = (s) => s?.id || s?.source_id || s?.name || s?.label;
const arr = (d, key) => Array.isArray(d) ? d : d?.[key] || [];

// ---- API Shelf (unchanged from original) ----
const defaultApiShelf = [
  { id: 'openai', name: 'OpenAI', group: 'AI Models', status: 'needs_key', env: 'OPENAI_API_KEY', owner: 'desktop', docs: 'https://platform.openai.com/docs', prompt: 'Use for Codex, agents, embeddings, and API-backed AI features.' },
  { id: 'gemini', name: 'Gemini', group: 'Research', status: 'browser', env: 'GEMINI_WEB_SESSION', owner: 'browser', docs: 'https://gemini.google.com', prompt: 'Use for Deep Research capture, export to Docs, and NotebookLM source preparation.' },
  { id: 'notebooklm', name: 'NotebookLM', group: 'Research', status: 'browser', env: 'NOTEBOOKLM_WEB_SESSION', owner: 'browser', docs: 'https://notebooklm.google.com', prompt: 'Add captured research, vault packs, and grant source packets as notebook sources.' },
  { id: 'github', name: 'GitHub', group: 'Code + Grants', status: 'configured', env: 'GH_TOKEN / gh auth', owner: 'desktop', docs: 'https://github.com', prompt: 'Push branches, create PR records, preserve research captures, and verify CI.' },
  { id: 'cloudflare', name: 'Cloudflare', group: 'Website', status: 'needs_review', env: 'CLOUDFLARE_API_TOKEN', owner: 'site', docs: 'https://dash.cloudflare.com', prompt: 'Use for Pages deploys, DNS, R2 media references, and faiththruphysics.com checks.' },
  { id: 'r2', name: 'R2 Media', group: 'Media', status: 'needs_review', env: 'RCLONE_CONFIG / R2 keys', owner: 'media', docs: 'https://developers.cloudflare.com/r2/', prompt: 'Upload audio, video, podcasts, and large media outside the website repo.' },
  { id: 'synology', name: 'Synology Hub', group: 'David-OS Nodes', status: 'planned', env: 'DAVID_OS_HUB_URL', owner: 'network', docs: 'http://synology.local:10000', prompt: 'Primary node heartbeat, file watcher coordination, help requests, and backups.' },
  { id: 'ahk', name: 'AutoHotkey Bridge', group: 'Desktop Control', status: 'planned', env: 'AHK_BRIDGE_URL', owner: 'desktop', docs: 'D:/GitHub/David-OS/ahk', prompt: 'Paste, capture, window targeting, overlays, and desktop command routing.' },
];
function loadApiShelf() {
  try { const saved = JSON.parse(localStorage.getItem(API_SHELF_KEY) || '[]'); if (Array.isArray(saved) && saved.length) return saved; } catch {}
  return defaultApiShelf;
}
function ApiShelfPanel({ setNotice }) {
  const [items, setItems] = useState(loadApiShelf);
  const [selectedId, setSelectedId] = useState(items[0]?.id || '');
  const [filter, setFilter] = useState('');
  const selected = items.find((item)=>item.id===selectedId) || items[0] || {};
  const groups = [...new Set(items.map((item)=>item.group || 'Other'))];
  const visibleItems = items.filter((item)=>[item.name, item.group, item.status, item.env].join(' ').toLowerCase().includes(filter.toLowerCase()));
  function save(next) { setItems(next); localStorage.setItem(API_SHELF_KEY, JSON.stringify(next)); }
  function patchSelected(patch) { save(items.map((item)=>item.id===selected.id ? { ...item, ...patch } : item)); }
  function addApi() { const id = `api-${Date.now()}`; save([...items, { id, name: 'New API', group: 'Unsorted', status: 'needs_key', env: '', owner: 'desktop', docs: '', prompt: '' }]); setSelectedId(id); }
  function copyPrompt() { const text = [`API: ${selected.name || ''}`, `Status: ${selected.status || ''}`, `Env/secret slot: ${selected.env || ''}`, `Owner: ${selected.owner || ''}`, '', selected.prompt || ''].join('\n'); navigator.clipboard?.writeText?.(text); setNotice(`Copied ${selected.name || 'API'} prompt card.`); }
  return <section className="api-shelf panel">
    <div className="api-head"><div><h3>API Shelf</h3><p>Track connectors, setup blanks, docs links, and prompt notes without storing raw API keys here.</p></div><button onClick={addApi}>Add API</button></div>
    <div className="api-layout">
      <aside className="api-list">
        <input value={filter} onChange={(e)=>setFilter(e.target.value)} placeholder="Filter APIs"/>
        {groups.map((group)=><div key={group}><h3>{group}</h3>{visibleItems.filter((item)=>item.group===group).map((item)=><button key={item.id} onClick={()=>setSelectedId(item.id)} className={`api-card ${selected.id===item.id?'selected':''}`}><b>{item.name}</b><span className={`api-status ${item.status}`}>{item.status}</span><small>{item.env || 'no env slot yet'}</small></button>)}</div>)}
      </aside>
      <div className="api-detail">
        <div className="form-grid">
          <label>Name<input value={selected.name || ''} onChange={(e)=>patchSelected({ name: e.target.value })}/></label>
          <label>Group<input value={selected.group || ''} onChange={(e)=>patchSelected({ group: e.target.value })}/></label>
          <label>Status<select value={selected.status || 'needs_key'} onChange={(e)=>patchSelected({ status: e.target.value })}><option value="configured">configured</option><option value="needs_key">needs key</option><option value="needs_review">needs review</option><option value="browser">browser session</option><option value="planned">planned</option><option value="offline">offline</option></select></label>
          <label>Owner<input value={selected.owner || ''} onChange={(e)=>patchSelected({ owner: e.target.value })}/></label>
          <label>Env or secret slot<input value={selected.env || ''} onChange={(e)=>patchSelected({ env: e.target.value })} placeholder="OPENAI_API_KEY"/></label>
          <label>Docs / console link<input value={selected.docs || ''} onChange={(e)=>patchSelected({ docs: e.target.value })}/></label>
        </div>
        <label>Prompt / setup note<textarea value={selected.prompt || ''} onChange={(e)=>patchSelected({ prompt: e.target.value })} placeholder="What should this API do inside David-OS?"/></label>
        <div className="inline"><button onClick={copyPrompt}>Copy prompt card</button>{selected.docs && <button onClick={()=>window.open(selected.docs, '_blank', 'noopener')}>Open docs</button>}<button onClick={()=>setNotice('Secrets should live in env files, OS keychain, GitHub secrets, or provider consoles. Keep this shelf as the map, not the vault.')}>Secret rule</button></div>
      </div>
    </div>
  </section>;
}

// ---- Settings (unchanged) ----
function ApiSettings({ online, setOnline, notice }) {
  const [url, setUrl] = useState(topOfMindApi.baseUrl);
  async function test() { topOfMindApi.setBaseUrl(url); try { await topOfMindApi.test(); setOnline(true); } catch { setOnline(false); } }
  return <section className="panel settings"><h3>API Settings</h3><input value={url} onChange={(e)=>setUrl(e.target.value)} placeholder="http://127.0.0.1:10000"/><button onClick={()=>{topOfMindApi.setBaseUrl(url); test();}}>Save + Test</button><span className={`status ${online?'ok':'bad'}`}>{online ? 'online' : 'offline'}</span>{notice && <p>{notice}</p>}</section>;
}

// ---- Sidebar (unchanged) ----
function Sidebar({ folders, selectedFolder, setSelectedFolder, createFolder, active, setActive }) {
  const sections = ['chats','apis','prompts','agents','models','tools/plugins','knowledge bank','settings'];
  const renderFolder = (f, depth = 0) => <div key={f.id || f.folder_id || f.folder_code}><button className="row" style={{'--depth': depth}} onClick={()=>setSelectedFolder(f)}>{depth ? '└' : '▾'} 📁 {f.name || f.title} <small>{f.folder_code}</small></button>{(f.children || []).map((c)=>renderFolder(c, depth + 1))}<button className="chat" style={{'--depth': depth + 1}}>💬 Current routing chat</button></div>;
  return <aside className="sidebar"><button className="new">＋ New Chat</button><input className="search" placeholder="Search Chats"/><h3>Folders</h3>{folders.map((f)=>renderFolder(f))}<button className="row" onClick={createFolder}>＋ Create folder via API</button>{sections.map((s)=><button key={s} onClick={()=>setActive(s)} className={`row ${active===s?'selected':''}`}>◇ {s}</button>)}</aside>;
}

// ---- Funnel (source control) ----
function Funnel({ sources, setSources, selectedMessage, patchMessage, collapsed, setCollapsed, activeAgentId, setActiveAgentId }) {
  const toggle = (id, key) => setSources((ss)=>ss.map((s)=> (s.id||s.name)===id ? {...s, [key]: !s[key], status: key==='paused' ? 'paused' : s.status} : s));
  const assign = (field, value) => selectedMessage && patchMessage(selectedMessage.id || selectedMessage.message_id, { [field]: value });
  return <aside className={`funnel ${collapsed?'collapsed':''}`}><button onClick={()=>setCollapsed(!collapsed)}>{collapsed?'▶':'◀'}</button>{!collapsed && <><h3>Funnel</h3>{sources.map((s)=>{ const id = srcId(s); const isActive = id === activeAgentId; return <div className={`source ${isActive?'active-source':''}`} key={id} onClick={()=>setActiveAgentId(id)} role="button" tabIndex="0" onKeyDown={(e)=>{if(e.key==='Enter'||e.key===' ') setActiveAgentId(id);}}><span className="avatar">{initials(s)}</span><b>{srcName(s)}</b><em>{isActive ? 'active' : (s.status||'online')}</em><button onClick={(e)=>{e.stopPropagation();toggle(id,'paused');}}>pause</button><button onClick={(e)=>{e.stopPropagation();toggle(id,'muted');}}>mute</button><label onClick={(e)=>e.stopPropagation()}><input type="checkbox" defaultChecked/> include</label><small>priority {s.priority || s.priority_code || 'normal'} · {s.configured === false ? 'not configured' : 'configured'}</small></div>})}<h3>Assign selected</h3><button onClick={()=>assign('wall_code', NUMBERING.walls.main)}>Main wall</button><button onClick={()=>assign('wall_code', NUMBERING.walls.code)}>Code wall</button><button onClick={()=>assign('folder_code', NUMBERING.folders.active)}>Active folder</button><div className="grid"><button onClick={()=>topOfMindApi.combine({})}>combine</button><button>split draft</button><button>broadcast draft</button><button onClick={()=>topOfMindApi.endAll()}>end all</button></div></>}</aside>;
}

// ---- Operator Surface (unchanged from original) ----
const operationFamilies = [
  { id: 'ahk', label: 'AHK', icon: '⌨', group: 'AutoHotkey' },
  { id: 'clipboard', label: 'Clipboard', icon: '⧉', group: 'Clipboard' },
  { id: 'files', label: 'Files', icon: '▣', group: 'File Operations' },
  { id: 'knowledge', label: 'Knowledge', icon: '◇', group: 'Knowledge Bank' },
  { id: 'vector', label: 'Vector', icon: '∑', group: 'Vectorization' },
  { id: 'commands', label: 'Commands', icon: '>', group: 'Command Line' },
  { id: 'agents', label: 'Agents', icon: '◎', group: 'Agents' },
  { id: 'memory', label: 'Memory', icon: '◈', group: 'Memory' },
  { id: 'hub', label: 'Hub', icon: '◆', group: 'API Calls' },
];

function OperatorSurface({ selectedSource, input, setNotice }) {
  const [family, setFamilyState] = useState(()=>localStorage.getItem(OP_FAMILY_KEY) || 'hub');
  const [folded, setFolded] = useState(false);
  const [capabilities, setCapabilities] = useState([]);
  const [ahkOnline, setAhkOnline] = useState(false);
  const [profile, setProfile] = useState('TopMind');
  const agent = { id: srcId(selectedSource), name: srcName(selectedSource), source_code: selectedSource?.source_code };
  const selectedFamily = operationFamilies.find((f)=>f.id===family) || operationFamilies[0];
  const setFamily = (id) => { setFamilyState(id); localStorage.setItem(OP_FAMILY_KEY, id); setFolded(false); };
  const status = (name, text) => setNotice(`${name}: ${text}`);
  const bridgeJob = (action, payload = {}) => topOfMindApi.createBridgeJob({ worker: 'ahk-main', action, target: agent, payload, source: 'operator-surface' });
  async function safeCall(name, fn, options = {}) {
    if (options.confirm && !window.confirm(options.confirm)) { status(name, 'cancelled'); return; }
    try { const result = await fn(); status(name, result?.status || result?.message || 'hub request accepted'); }
    catch (e) { status(name, `API route unavailable or failed (${e.message})`); }
  }
  useEffect(()=>{ topOfMindApi.getCapabilities().then((d)=>setCapabilities(arr(d,'capabilities'))).catch(()=>setCapabilities([])); },[]);
  const groupedCapabilities = capabilities.filter((cap)=>cap.enabled !== false && (cap.ui_group || '').toLowerCase() === selectedFamily.group.toLowerCase());
  const actionButton = (label, onClick, danger) => <button className={danger?'danger':''} onClick={onClick}>{label}</button>;
  const defaultActions = {
    ahk: [
      actionButton('Paste job', ()=>safeCall('AHK Paste', ()=>bridgeJob('paste_to_active', { text: input }))),
      actionButton('Send job', ()=>safeCall('AHK Send', ()=>bridgeJob('send_to_active', { text: input }))),
      actionButton('Toggle overlay', ()=>safeCall('AHK Overlay', ()=>bridgeJob('toggle_overlay', { profile }))),
    ],
    clipboard: [
      actionButton('Save clipboard', ()=>safeCall('Clipboard', ()=>topOfMindApi.saveClipboard({ action: 'clipboard_save', target: agent, text: input, dry_run: true }))),
      actionButton('Push clipboard', ()=>safeCall('Push', ()=>topOfMindApi.pushClipboard({ target: agent, message: input, dry_run: true }))),
    ],
    files: [
      actionButton('List folders', ()=>safeCall('Folders', ()=>topOfMindApi.getFolders())),
      actionButton('Dry-run file action', ()=>safeCall('File dry-run', ()=>topOfMindApi.fileActions({ action: 'dry_run', target: agent, dry_run: true }))),
      actionButton('Overwrite file', ()=>safeCall('Overwrite', ()=>topOfMindApi.fileActions({ action: 'overwrite_file', target: agent, dry_run: true }), { confirm: 'Overwrite file actions require confirmation. Continue dry-run?' }), true),
    ],
    knowledge: [actionButton('Search KB', ()=>safeCall('Knowledge', ()=>topOfMindApi.searchFileCache(input || '')))],
    vector: [
      actionButton('Embed pending', ()=>safeCall('Vector', ()=>topOfMindApi.embedPending())),
      actionButton('Search vectors', ()=>safeCall('Vector Search', ()=>topOfMindApi.searchMemory(input || '', 'vector'))),
      actionButton('Bulk import', ()=>safeCall('Bulk import', ()=>bridgeJob('bulk_import', { dry_run: true }), { confirm: 'Bulk import requires confirmation. Queue dry-run?' }), true),
    ],
    commands: [
      actionButton('Dry-run command', ()=>safeCall('Command', ()=>topOfMindApi.command({ action: 'dry_run', command: input, dry_run: true }), { confirm: 'Command line actions require confirmation. Continue dry-run?' }), true),
    ],
    agents: [
      actionButton('Agent send', ()=>safeCall('Agent Send', ()=>topOfMindApi.sendAgent({ action: 'agent_send', target: agent, message: input, route_only: true, dry_run: true }))),
      actionButton('Broadcast dry-run', ()=>safeCall('Broadcast', ()=>topOfMindApi.sendAgent({ action: 'broadcast_all', target: agent, message: input, route_only: true, dry_run: true }), { confirm: 'Broadcast to all agents requires confirmation. Continue dry-run?' }), true),
    ],
    memory: [
      actionButton('Save memory', ()=>safeCall('Memory', ()=>topOfMindApi.createMemoryItem({ text: input, source: agent, dry_run: true }))),
      actionButton('Search memory', ()=>safeCall('Memory Search', ()=>topOfMindApi.searchMemory(input || ''))),
    ],
    hub: [
      actionButton('Health', ()=>safeCall('Hub Health', ()=>topOfMindApi.hubHealth())),
      actionButton('Capabilities', ()=>safeCall('Capabilities', async()=>{ const d = await topOfMindApi.getCapabilities(); setCapabilities(arr(d,'capabilities')); return d; })),
      actionButton('End all', ()=>safeCall('End All', ()=>topOfMindApi.endAll({ action: 'end_all', target: agent }), { confirm: 'Stop/end all active jobs?' }), true),
    ],
  };
  return <aside className={`operator-surface ${folded?'folded':''}`} aria-label="Operator command surface">
    <nav className="shortcut-rail" aria-label="Operation shortcuts">
      <button className="fold" onClick={()=>setFolded(!folded)} aria-label={folded?'Expand operations':'Fold operations'} title={folded?'Expand operations':'Fold operations'}>{folded?'◀':'▶'}</button>
      <div className="rail-ahk" aria-label="Persistent AutoHotkey controls">
        <span className={`dot ${ahkOnline?'ok':'bad'}`} title={`AHK ${ahkOnline?'online':'offline'} · ${profile}`}></span>
        <button onClick={()=>safeCall('AHK Frame', ()=>bridgeJob('toggle_overlay', { profile }))} aria-label="Toggle AHK frame overlay" title="Frame / overlay">F</button>
        <button onClick={()=>safeCall('AHK Paste', ()=>bridgeJob('paste_to_active', { text: input }))} aria-label="AHK paste to active" title="Paste">P</button>
        <button onClick={()=>safeCall('AHK Send', ()=>bridgeJob('send_to_active', { text: input }))} aria-label="AHK send to active" title="Send">S</button>
        <button onClick={()=>safeCall('End All', ()=>topOfMindApi.endAll({ action: 'end_all', target: agent }))} aria-label="Stop or end all" title="Stop / end all">!</button>
        <button onClick={()=>safeCall('Hub', ()=>topOfMindApi.hubHealth())} aria-label="Hub health" title="Hub health">H</button>
        <button onClick={()=>safeCall('Bridge Test', async()=>{ const r = await bridgeJob('bridge_test', { profile }); setAhkOnline(true); return r; })} aria-label="Quick bridge test" title="Bridge test">T</button>
      </div>
      {operationFamilies.map((item)=><button key={item.id} className={family===item.id?'active':''} onClick={()=>setFamily(item.id)} aria-label={item.label} title={item.label}>{item.icon}</button>)}
    </nav>
    {!folded && <section className="ops-panel">
      <div className="ahk-layer" aria-label="Persistent AutoHotkey layer">
        <div><b>AHK</b><span className={`dot ${ahkOnline?'ok':'bad'}`}></span></div>
        <small>{ahkOnline?'online':'offline'} · {profile}</small>
        <div className="mini-grid">
          <button onClick={()=>safeCall('AHK Frame', ()=>bridgeJob('toggle_overlay', { profile }))}>Frame</button>
          <button onClick={()=>safeCall('AHK Paste', ()=>bridgeJob('paste_to_active', { text: input }))}>Paste</button>
          <button onClick={()=>safeCall('AHK Send', ()=>bridgeJob('send_to_active', { text: input }))}>Send</button>
          <button onClick={()=>safeCall('End All', ()=>topOfMindApi.endAll({ action: 'end_all', target: agent }))}>Stop</button>
          <button onClick={()=>safeCall('Hub', ()=>topOfMindApi.hubHealth())}>Hub</button>
          <button onClick={()=>safeCall('Bridge Test', async()=>{ const r = await bridgeJob('bridge_test', { profile }); setAhkOnline(true); return r; })}>Test</button>
        </div>
      </div>
      <div className="ops-head"><b>{selectedFamily.group}</b><small>target: {agent.name}</small></div>
      {groupedCapabilities.length ? <div className="cap-list">{groupedCapabilities.map((cap)=><button key={cap.id} disabled={cap.enabled===false} className={cap.requires_confirm || cap.risk_level === 'danger' ? 'danger' : ''} onClick={()=>safeCall(cap.label, ()=>topOfMindApi.createBridgeJob({ worker: 'ahk-main', action: cap.id, target: agent, payload: { dry_run: cap.supports_dry_run !== false }, source: 'capability' }), cap.requires_confirm ? { confirm: `${cap.label} requires confirmation. Continue?` } : {})}>{cap.label}<small>{cap.capability} · {cap.risk_level || 'safe'}</small></button>)}</div> : <div className="ops-grid">{defaultActions[family] || defaultActions.hub}<small className="placeholder">No /capabilities data for this group yet; showing safe hub placeholders.</small></div>}
    </section>}
  </aside>;
}

// ---- Search panels (unchanged) ----
function SearchPanel({ title, modeToggle, onSearch }) {
  const [q, setQ] = useState(''); const [mode, setMode] = useState('text'); const [results, setResults] = useState([]);
  async function run(){ try { setResults(arr(await onSearch(q, mode), 'items')); } catch { setResults([{ name: 'API offline', content: 'Search could not run.' }]); } }
  return <section className="panel"><h3>{title}</h3><div className="inline"><input value={q} onChange={(e)=>setQ(e.target.value)} placeholder="Search…"/>{modeToggle && <label><input type="checkbox" onChange={(e)=>setMode(e.target.checked?'vector':'text')}/> vector</label>}<button onClick={run}>Search</button></div>{results.slice(0,8).map((r,i)=><p key={i}>▣ {r.name || r.path || r.title || r.content || JSON.stringify(r)}</p>)}</section>;
}

// ============================================================
// MAIN APP
// ============================================================
function App() {
  const [sources, setSources] = useState(fallbackSources);
  const [folders, setFolders] = useState(starterFolders);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [active, setActive] = useState('chats');
  const [selectedFolder, setSelectedFolder] = useState(starterFolders[0]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [online, setOnline] = useState(false);
  const [notice, setNotice] = useState('');
  const [funnelCollapsed, setFunnelCollapsed] = useState(false);
  const [activeAgentId, setActiveAgentIdState] = useState(()=>localStorage.getItem(ACTIVE_AGENT_KEY) || 'kimi');
  const [chatFilter, setChatFilter] = useState(null);

  const setActiveAgentId = (id) => { setActiveAgentIdState(id); localStorage.setItem(ACTIVE_AGENT_KEY, id); };

  // Load messages on mount + polling
  useEffect(()=>{
    topOfMindApi.getSources().then(d=>{const s=arr(d,'sources'); if(s.length) setSources(s); setOnline(true);}).catch(e=>{setOnline(false); setNotice(e.message);});
    topOfMindApi.getFolders().then(d=>setFolders(arr(d,'folders'))).catch(()=>{});
    const loadMessages = () => topOfMindApi.getMessages(75).then(d=>{setMessages(arr(d,'messages')); setOnline(true);}).catch(()=>setOnline(false));
    loadMessages();
    const timer = setInterval(loadMessages, 4000);
    return () => clearInterval(timer);
  },[]);

  const selectedSource = sources.find((source)=>srcId(source)===activeAgentId) || sources[0] || fallbackSources[0];

  // Send message
  async function send() {
    if (!input.trim()) return;
    const payload = {
      source_id: srcId(selectedSource),
      source_label: srcName(selectedSource),
      body: input,
      role: 'user',
      wall: 'main',
      folder: selectedFolder.name || 'Main'
    };
    setInput('');
    try {
      const saved = await topOfMindApi.createMessage(payload);
      setMessages((m)=>[...m, saved]);
    } catch {
      setMessages((m)=>[...m, {...payload, id: `local-${Date.now()}`, created_at: new Date().toISOString()}]);
      setNotice('Draft shown locally; API post failed.');
    }
  }

  // Patch a message
  async function patchMessage(id, body) {
    setMessages(ms=>ms.map(m=>(m.id===id||m.message_id===id)?{...m,...body}:m));
    try { await topOfMindApi.updateMessage(id, body); } catch { setNotice('Local patch shown; API patch failed.'); }
  }

  // Create folder
  async function createFolder() {
    const name = prompt('Folder name?');
    if (!name) return;
    try { const f = await topOfMindApi.createFolder({ name, parent_id: selectedFolder.id || selectedFolder.folder_id }); setFolders(fs=>[...fs, f]); } catch { setNotice('Folder must be created by API; request failed.'); }
  }

  // Message counts by source
  const messageCounts = useMemo(() => {
    const bySource = {};
    messages.forEach((m) => {
      const s = m.source || m.source_id || m.source_label || 'unknown';
      bySource[s] = (bySource[s] || 0) + 1;
    });
    return { total: messages.length, bySource };
  }, [messages]);

  // Copy prompt to composer
  const copyPromptToComposer = useCallback((text) => {
    setInput((current) => (current ? current + '\n\n' + text : text));
  }, []);

  // Mic toggle
  const handleMicToggle = useCallback((enabled) => {
    setNotice(`Microphone ${enabled ? 'on' : 'off'}`);
  }, []);

  // Attach (placeholder)
  const handleAttach = useCallback(() => {
    setNotice('Attachments coming soon — needs upload endpoint.');
  }, []);

  // Derive active source name for composer placeholder
  const activeSourceName = srcName(selectedSource);

  return (
    <div className="app">
      {/* Left rail */}
      <nav className="rail">
        <b>ToM</b>
        {['chats','apis','prompts','memory','files','operator','settings'].map(x => (
          <button className={active===x?'on':''} onClick={()=>setActive(x)} key={x}>
            {x[0].toUpperCase()}
          </button>
        ))}
      </nav>

      {/* Sidebar */}
      <Sidebar
        folders={folders}
        selectedFolder={selectedFolder}
        setSelectedFolder={setSelectedFolder}
        createFolder={createFolder}
        active={active}
        setActive={setActive}
      />

      {/* Funnel */}
      <Funnel
        sources={sources}
        setSources={setSources}
        selectedMessage={selectedMessage}
        patchMessage={patchMessage}
        collapsed={funnelCollapsed}
        setCollapsed={setFunnelCollapsed}
        activeAgentId={activeAgentId}
        setActiveAgentId={setActiveAgentId}
      />

      {/* Main content */}
      <main>
        <header>
          <h1>Top of Mind Desk</h1>
          <span className={`status ${online?'ok':'bad'}`}>
            {online?'● live':'○ offline'} · {topOfMindApi.baseUrl}
          </span>
        </header>

        <section className="workspace">
          {/* Chats view */}
          {active === 'chats' && (
            <div className="chats-layout">
              {/* Source filter rail */}
              <SourceFilter
                sources={sources}
                activeFilter={chatFilter}
                onFilterChange={setChatFilter}
                messageCounts={messageCounts}
                online={online}
              />

              {/* Chat area */}
              <div className="chats-main">
                <ChatView
                  messages={messages}
                  onPatchMessage={patchMessage}
                  onSelectMessage={setSelectedMessage}
                  filterSource={chatFilter}
                />

                {/* Footer composer */}
                <footer className="chat-footer">
                  <div className="cmd">
                    <button onClick={()=>topOfMindApi.combine({ folder_code: selectedFolder.folder_code })}>Combine</button>
                    <button>Split</button>
                    <button>Broadcast</button>
                    <button onClick={()=>topOfMindApi.endAll()}>End all</button>
                    <span>source_code {selectedSource.source_code}</span>
                    <span>folder_code {selectedFolder.folder_code}</span>
                  </div>
                  <Composer
                    input={input}
                    setInput={setInput}
                    onSend={send}
                    onMicToggle={handleMicToggle}
                    onAttach={handleAttach}
                    busy={false}
                    activeSource={activeSourceName}
                  />
                </footer>
              </div>
            </div>
          )}

          {/* Prompts view */}
          {active === 'prompts' && (
            <PromptsPanel onCopyToComposer={copyPromptToComposer} />
          )}

          {/* Other views (unchanged) */}
          {active === 'apis' && <ApiShelfPanel setNotice={setNotice} />}
          {active === 'memory' && <SearchPanel title="Memory search" modeToggle onSearch={(q,m)=>topOfMindApi.searchMemory(q,m==='vector'?'vector':undefined)} />}
          {active === 'files' && <SearchPanel title="File cache search" onSearch={(q)=>topOfMindApi.searchFileCache(q)} />}
          {active === 'settings' && <ApiSettings online={online} setOnline={setOnline} notice={notice} />}
          {active === 'operator' && (
            <section className="panel">
              <h3>Operator drafts</h3>
              <textarea placeholder='{"action":"write_text","path":"notes.txt","text":"draft only"}'/>
              <textarea placeholder='{"action":"append_text","path":"notes.txt","text":"draft only"}'/>
              <button onClick={()=>setNotice('Draft only. Review before sending to /operator/file-actions or /operator/commands.')}>Do not run destructive action</button>
            </section>
          )}
        </section>
      </main>

      {/* Operator surface */}
      <OperatorSurface selectedSource={selectedSource} input={input} setNotice={setNotice} />

      {/* Notice toast */}
      {notice && (
        <div className="notice-toast" onClick={() => setNotice('')}>
          {notice}
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
