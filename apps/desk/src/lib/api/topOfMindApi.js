const DEFAULT_API_BASE = 'http://127.0.0.1:10000';
const STORAGE_KEY = 'topOfMind.apiBaseUrl';

export const NUMBERING = {
  sources: { clipboard: 22001, ahk: 22002, codex: 20040, kimi: 20030, claude: 20010, gemini: 20020, cursor: 20050, operator: 20060, topOfMind: 20070 },
  types: { normalChat: 30001, response: 30002, clipboardCapture: 32001 },
  priorities: { normal: 40003, high: 40007 },
  walls: { main: 50001, code: 50006 },
  folders: { inbox: 60001, active: 60002 },
};

export function getApiBaseUrl() {
  return localStorage.getItem(STORAGE_KEY) || import.meta.env.VITE_TOP_OF_MIND_API || DEFAULT_API_BASE;
}

export function setApiBaseUrl(url) {
  const clean = (url || '').trim().replace(/\/$/, '');
  if (clean) localStorage.setItem(STORAGE_KEY, clean);
  return clean || DEFAULT_API_BASE;
}

async function request(path, options = {}) {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  if (response.status === 204) return null;
  return response.json();
}

const qs = (params) => new URLSearchParams(params).toString();

export const topOfMindApi = {
  get baseUrl() { return getApiBaseUrl(); },
  setBaseUrl: setApiBaseUrl,
  test: () => request('/top-of-mind/sources'),
  getCapabilities: () => request('/capabilities'),
  getSources: () => request('/top-of-mind/sources'),
  createSource: (source) => request('/top-of-mind/sources', { method: 'POST', body: JSON.stringify(source) }),
  getMessages: (limit = 75) => request(`/top-of-mind/messages?${qs({ limit })}`),
  createMessage: (message) => request('/top-of-mind/messages', { method: 'POST', body: JSON.stringify(message) }),
  saveClipboard: (payload) => request('/clipboard/save', { method: 'POST', body: JSON.stringify(payload) }),
  sendAgent: (payload) => request('/agents/send', { method: 'POST', body: JSON.stringify(payload) }),
  pushClipboard: (payload) => request('/agents/send', { method: 'POST', body: JSON.stringify({ ...payload, action: 'push_clipboard', route_only: true }) }),
  createBridgeJob: (payload) => request('/bridge/jobs', { method: 'POST', body: JSON.stringify(payload) }),
  bridgeHeartbeat: (payload) => request('/bridge/heartbeat', { method: 'POST', body: JSON.stringify(payload) }),
  getBridgeJobs: (worker = 'ahk-main') => request(`/bridge/jobs?${qs({ worker })}`),
  bridgeEvent: (payload) => request('/bridge/events', { method: 'POST', body: JSON.stringify(payload) }),
  updateMessage: (id, patch) => request(`/top-of-mind/messages/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  combine: (payload = {}) => request('/top-of-mind/combine', { method: 'POST', body: JSON.stringify(payload) }),
  endAll: (payload = {}) => request('/top-of-mind/controls/end-all', { method: 'POST', body: JSON.stringify(payload) }),
  hubHealth: () => request('/jobs/stats'),
  getFolders: () => request('/folders'),
  createFolder: (folder) => request('/folders', { method: 'POST', body: JSON.stringify(folder) }),
  createMemoryItem: (item) => request('/memory/items', { method: 'POST', body: JSON.stringify(item) }),
  getMemoryItems: () => request('/memory/items'),
  searchMemory: (q, mode) => request(`/memory/search?${qs({ q, ...(mode ? { mode } : {}) })}`),
  embedPending: () => request('/memory/embed-pending', { method: 'POST', body: JSON.stringify({}) }),
  cacheFile: (file) => request('/files/cache', { method: 'POST', body: JSON.stringify(file) }),
  getFileCache: () => request('/files/cache'),
  searchFileCache: (q) => request(`/files/cache/search?${qs({ q })}`),
  getFileByPath: (path) => request(`/files/cache/by-path?${qs({ path })}`),
  fileActions: (payload) => request('/operator/file-actions', { method: 'POST', body: JSON.stringify(payload) }),
  command: (payload) => request('/operator/commands', { method: 'POST', body: JSON.stringify(payload) }),
};
